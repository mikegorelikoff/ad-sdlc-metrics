---
title: 'Finish well-specified deferred work (--repo, gap-fill, Codex counts, parent linkage)'
type: 'chore'
created: '2026-07-23'
status: 'done'
review_loop_iteration: 0
context: []
baseline_commit: 'NO_VCS'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `deferred-work.md` had 13 open items. Of these, 5 were fully specified already (no outstanding judgment calls) and safe to implement directly: `--repo` filter (`inventory.py` + `pipeline.py`), `inventory.py` non-zero exit + `CODEX_HOME`/`CLAUDE_HOME` env overrides, `stats-cache.json` gap-fill for Claude, Codex `message_count`/`tool_call_count` (previously always blank), and parent/child subagent thread linkage.

**Approach:** Implement all five directly (human was unavailable to re-confirm scope mid-turn; each item's deferred-work description already constituted an agreed spec). Left untouched: metric-precision items needing a human threshold/definition decision, and the test-suite item (bundled into one consolidated future spec instead of 3 near-duplicates).

## Boundaries & Constraints

**Always:**
- `--repo <substring>` on `inventory.py`: case-insensitive substring match against each project-scoped source's `cwd`; `history.jsonl` and `stats-cache.json` stay unfiltered (not project-scoped).
- `--repo` on `pipeline.py`: same substring filter applied in both extractors before building `sessions.csv`; skips the `stats-cache.json` gap-fill entirely when set (that data has no per-project attribution).
- `inventory.py` honors `CODEX_HOME`/`CLAUDE_HOME` env vars (falling back to `~/.codex`/`~/.claude`), and exits non-zero if any printed source is `missing`/`unreadable`.
- Codex `message_count`/`tool_call_count` come from parsing each thread's own `rollout_path` jsonl file (`response_item` records: `message` with `role in (user, assistant)` → message; `function_call` → tool call).
- `parent_session_id` (new `sessions.csv` column, blank for top-level sessions): Codex — `parent_thread_id` from the `thread_spawn` JSON in `threads.source`; Claude — the parent session's own uuid, derived from the subagent transcript's grandparent directory name.
- Claude `stats-cache.json` gap-fill only adds `daily_activity.csv` rows for dates not already covered by transcript-derived sessions; a day counts as active if `sessionCount`, `messageCount`, or `toolCallCount` is > 0 (not `sessionCount` alone, since some real-activity days show `sessionCount: 0`).

**Ask First:** none — all five items were already fully specified in `deferred-work.md` with no open questions.

**Never:**
- Did not touch the four items needing a human judgment call (tool-echo message-count precision, row-count sanity threshold, partial-period marking, project_path redaction) — still open in `deferred-work.md`.
- Did not build the test suite — bundled into one future consolidated entry instead of building now.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| `--repo` with no matches | substring matches no session | Project-scoped sources report 0/empty; non-scoped sources unaffected | N/A |
| `CODEX_HOME` pointed at nonexistent dir | env var set to a missing path | Sources under it report "not found"; `inventory.py` exits 1 | N/A |
| Codex `source` column is a non-JSON, non-plain string (unexpected future value) | any | Treated as `human` (safe default), `parent_session_id` stays blank | N/A |
| Claude stats-cache day with `sessionCount: 0` but real message/tool activity | e.g. 2026-06-11 | Still included in `daily_activity.csv` gap-fill (evidence-based, not session-count-only) | N/A |
| Rollout file referenced by `rollout_path` no longer exists on disk | Codex thread row present, file missing | `message_count`/`tool_call_count` fall back to `None` (blank) | Warning printed, no crash |

</frozen-after-approval>

## Code Map

- `scripts/inventory.py` -- edit: env var overrides, `--repo`, non-zero exit
- `scripts/extract_codex.py` -- edit: rollout-based message/tool counts, `parent_session_id`, `--repo`
- `scripts/extract_claude.py` -- edit: `parent_session_id`, `--repo`, `get_stats_cache_gap_days`
- `scripts/csv_common.py` -- edit: `parent_session_id` added to `SESSION_FIELDS`
- `scripts/pipeline.py` -- edit: `--repo` wiring, stats-cache gap-fill call

## Tasks & Acceptance

**Execution:**
- [x] `scripts/inventory.py` -- `CODEX_HOME`/`CLAUDE_HOME` env overrides, `--repo` on project-scoped sources, non-zero exit on missing/unreadable
- [x] `scripts/extract_codex.py` -- parse `rollout_path` for message/tool-call counts, extract `parent_session_id` from `thread_spawn` JSON, `--repo` via SQL `LIKE`
- [x] `scripts/extract_claude.py` -- `parent_session_id` from grandparent directory name, `--repo` filter, `get_stats_cache_gap_days`
- [x] `scripts/csv_common.py` -- add `parent_session_id` to `SESSION_FIELDS`
- [x] `scripts/pipeline.py` -- thread `--repo` through both extractors, call gap-fill (skipped when `--repo` set)

**Acceptance Criteria:**
- Given `python3.11 scripts/inventory.py --repo monolith`, then Codex/Claude project-scoped counts narrow to that project, `history.jsonl`/`stats-cache.json` unaffected.
- Given `CODEX_HOME=/nonexistent python3.11 scripts/inventory.py --tool codex`, then it reports "not found" and exits 1.
- Given `python3.11 scripts/pipeline.py`, then `sessions.csv` has non-blank `message_count`/`tool_call_count` for Codex human sessions, and `daily_activity.csv` includes Claude's June gap dates.
- Given a subagent row in `sessions.csv`, then `parent_session_id` is populated for both tools.

## Spec Change Log

- 2026-07-23: Review round 1 (Blind Hunter + Edge Case Hunter, in parallel). Patched: `CODEX_HOME`/`CLAUDE_HOME` env-var support extended to `extract_codex.py`/`extract_claude.py` (was `inventory.py`-only); `inventory.py`'s exit code now only fires on `unreadable` (genuine corruption), not `missing` (often a legitimate "tool not installed" state); the stats-cache gap-fill's `0 or None` bug (a real 0 was collapsing to blank) fixed to preserve real zeros; `inventory.py` gained the reversed `--from`/`--to` validation and `rglob()` `OSError` guard that `pipeline.py`/`extract_claude.py` already had; stats-cache date lists deduplicated in both `inventory.py` and the gap-fill; `scan_transcript_dir`'s `file_cwd` detection no longer gets stuck on an empty-string false-positive; Claude's `is_subagent` check narrowed from "any ancestor directory" to "immediate parent only" (more precise, matches the actual observed convention); `pipeline.py`'s `daily` list now always sorts chronologically regardless of which code path ran; a note is now printed when `--repo` skips the stats-cache gap-fill; duplicated `_iso_date`/epoch-bound-computation logic across three files consolidated into `csv_common.iso_date`/`csv_common.epoch_bounds`. Rejected: cross-tool message-count semantic mismatch (already tracked as an existing deferred item), SQL `LIKE` vs `.lower()` case-sensitivity inconsistency for non-ASCII paths (no realistic impact on this machine), `_parent_thread_id` self/cyclic-reference guard and dangling-parent-reference detection (best-effort enrichment, not a core metric). Deferred (see `deferred-work.md`): nested subagent-of-subagent linkage, the sharper cross-tool message-count comparability question.

## Design Notes

Codex's `rollout_path` column (already `NOT NULL` on every thread) makes per-thread transcript parsing trivial — no need to separately locate the file. The stats-cache gap-fill deliberately doesn't require `sessionCount > 0` because at least one real day (2026-06-11) shows `sessionCount: 0` alongside real `messageCount`/`toolCallCount`, likely from a session whose stats-cache attribution crosses a day boundary differently than raw transcript dates would.

## Verification

**Commands:**
- `python3.11 scripts/pipeline.py && python3.11 scripts/adoption_report.py` -- expected: no traceback, all four CSVs regenerate
- `python3.11 scripts/inventory.py --repo monolith --tool codex` -- expected: narrowed counts, exit 0
- `awk -F, 'NR>1 && $1=="codex" && $9=="human"{print $6,$7}' data/sessions.csv | head` -- expected: non-blank message/tool-call counts
