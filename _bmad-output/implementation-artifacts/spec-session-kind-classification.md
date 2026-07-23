---
title: 'Classify sessions as human-initiated vs subagent-spawned'
type: 'feature'
created: '2026-07-23'
status: 'done'
review_loop_iteration: 0
context: []
baseline_commit: 'NO_VCS'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `sessions.csv`/`daily_activity.csv` currently count subagent-spawned work identically to human-initiated sessions. Investigation found 613 of 1058 Codex threads (58%) are subagent threads (`threads.source` holds `thread_spawn` JSON metadata instead of `cli`/`exec`/`vscode`), and Claude Code writes subagent transcripts under `<session_id>/subagents/agent-*.jsonl` (7 of 22 matched files) — both currently inflate adoption numbers with autonomous agent work, not direct human usage.

**Approach:** Add a `session_kind` column (`human`|`subagent`) to `sessions.csv` for both extractors. `sessions.csv` keeps every row (both kinds, labeled). `pipeline.py` filters to `session_kind == "human"` before building `daily_activity.csv`, so `daily_activity.csv` and everything downstream (`adoption_weekly.csv`/`adoption_monthly.csv`, unchanged code) reflect real human activity by default.

## Boundaries & Constraints

**Always:**
- `sessions.csv` gains one new column, `session_kind`, appended after `tokens_used`; all existing columns keep their current meaning.
- Codex classification: `threads.source` is JSON-object-shaped (starts with `{`) → `subagent`; otherwise (`cli`, `exec`, `vscode`, or any other future plain string) → `human`.
- Claude classification: the transcript file's path contains a `subagents` directory component before the filename → `subagent`; otherwise → `human`.
- `pipeline.py` builds `daily_activity.csv` from only `session_kind == "human"` rows; `sessions.csv` itself still contains both kinds, unfiltered.
- `adoption_report.py` requires no code changes — it already only reads `daily_activity.csv`, which now already excludes subagent rows.
- Re-running `pipeline.py` then `adoption_report.py` regenerates all four CSVs consistently with the new classification.

**Ask First:** none — classification rule and default filtering behavior are fully specified above.

**Never:**
- Do not drop subagent rows from `sessions.csv` — they stay, labeled, for anyone who wants to look at total (human + subagent) work later.
- Do not add a `--include-subagents` CLI flag or any other override in this pass — out of scope, can be a follow-up if ever needed.
- Do not change `adoption_report.py`'s code — the fix flows through automatically once `daily_activity.csv` is regenerated.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Codex human thread | `threads.source = "cli"` | `session_kind = "human"` | N/A |
| Codex subagent thread | `threads.source` starts with `{` (thread_spawn JSON) | `session_kind = "subagent"` | N/A |
| Claude top-level session | `.../<uuid>.jsonl` (no `subagents` path segment) | `session_kind = "human"` | N/A |
| Claude subagent transcript | `.../<uuid>/subagents/agent-*.jsonl` | `session_kind = "subagent"` | N/A |
| Re-run full pipeline | `pipeline.py` then `adoption_report.py` | `sessions.csv` has both kinds; `daily_activity.csv`/`adoption_*.csv` counts drop to human-only levels | N/A |

</frozen-after-approval>

## Code Map

- `scripts/csv_common.py` -- edit: add `session_kind` to `SESSION_FIELDS`
- `scripts/extract_codex.py` -- edit: classify `session_kind` from `threads.source`
- `scripts/extract_claude.py` -- edit: classify `session_kind` from transcript file path
- `scripts/pipeline.py` -- edit: filter to `session_kind == "human"` before calling `aggregate_daily`

## Tasks & Acceptance

**Execution:**
- [x] `scripts/csv_common.py` -- add `"session_kind"` to `SESSION_FIELDS` tuple
- [x] `scripts/extract_codex.py` -- classify each thread's `session_kind` from `source` (JSON-object-shaped → `subagent`, else `human`)
- [x] `scripts/extract_claude.py` -- classify each transcript's `session_kind` from whether `subagents` appears as a path component before the filename
- [x] `scripts/pipeline.py` -- filter sessions to `session_kind == "human"` before `csv_common.aggregate_daily(...)`; `sessions.csv` itself still writes all rows

**Acceptance Criteria:**
- Given a full `pipeline.py` run, when inspecting `sessions.csv`, then Codex rows split roughly 445 `human` / 613 `subagent`, and Claude has some `subagent` rows for files under `subagents/` directories.
- Given the same run, when inspecting `daily_activity.csv`, then `session_count` per day only reflects `human`-kind sessions (lower than before this change).
- Given `pipeline.py` then `adoption_report.py` are re-run, then `adoption_weekly.csv`/`adoption_monthly.csv` regenerate with the corrected (lower, human-only) counts, with no code changes needed in `adoption_report.py`.

## Spec Change Log

- 2026-07-23: Review round 1 (Blind Hunter + Edge Case Hunter, in parallel). Patched: `pipeline.py`'s human/subagent filter now uses `.get()` with a warning for any unrecognized/missing `session_kind` instead of a direct dict-index that could `KeyError`; the Claude `subagents` path-segment check is now case-insensitive; added clarifying comments documenting both heuristics' empirical basis and the deliberate `sessions.csv` (unfiltered) vs `daily_activity.csv` (human-only) divergence. Rejected: concerns that the Codex `source`-column and Claude directory-name heuristics are unverified guesses — both were empirically checked against this machine's actual data before being written (Codex: `source` values are exactly `cli`/`exec`/`vscode` or a `thread_spawn` JSON blob, no other shapes observed; Claude: exact path-segment match, not substring, already guards the "unrelated directory named similarly" scenario). Deferred (see `deferred-work.md`): preserving parent/child thread linkage, populating Codex `message_count`/`tool_call_count`.

## Design Notes

Codex's `threads.source` column serves double duty: for human-initiated threads it holds a plain surface string (`cli`/`exec`/`vscode`); for subagent threads it holds a JSON blob describing the `thread_spawn` (parent thread, agent nickname/role). Detecting "is this JSON" is a reliable, forward-compatible way to separate the two without enumerating agent-role names.

## Verification

**Commands:**
- `python3.11 scripts/pipeline.py && python3.11 scripts/adoption_report.py` -- expected: no traceback, all four CSVs regenerate
- `awk -F, 'NR>1{print $1","$9}' data/sessions.csv | sort | uniq -c` -- expected: counts of `codex,human` / `codex,subagent` / `claude,human` / `claude,subagent`
- `awk -F, 'NR>1{s+=$4} END{print s}' data/daily_activity.csv` -- expected: total `session_count` sum drops from the pre-fix total (should now exclude subagent rows)
