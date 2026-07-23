---
title: 'Codex + Claude Code unified daily-activity CSV for AI adoption tracking'
type: 'feature'
created: '2026-07-22'
status: 'done'
review_loop_iteration: 0
context: []
baseline_commit: 'NO_VCS'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Assessing personal AI-tool adoption (per the DX AI Measurement Framework's utilization dimension — active days, session frequency, volume) requires the data to leave `~/.codex`/`~/.claude` in one identical schema per tool. `inventory.py` only reports counts to stdout; it writes nothing to disk.

**Approach:** Build `scripts/extract_codex.py` and `scripts/extract_claude.py`, each normalizing their tool's sessions into the same two output shapes, and `scripts/pipeline.py` to run both and write `data/sessions.csv` (one row per session) and `data/daily_activity.csv` (one row per `(source, date)`) with identical columns across tools — so weekly/monthly active-day counts can be computed downstream by a simple groupby with no per-tool special-casing. This script only produces the normalized CSVs; it does not compute DAU/WAU/MAU itself, and (see Design Notes) covers only dates with direct transcript/thread evidence.

## Boundaries & Constraints

**Always:**
- Read-only on `~/.codex`/`~/.claude`; write only inside this repo's `data/` directory.
- `sessions.csv` columns (identical across tools): `source` (`codex`|`claude`), `session_id`, `date` (session start, `YYYY-MM-DD`), `project_path`, `model`, `message_count`, `tool_call_count`, `tokens_used` (last three blank if unknown).
- `daily_activity.csv` columns (identical across tools): `source`, `date`, `active` (`1` if any usage that date), `session_count`, `message_count`, `tool_call_count`, `tokens_used`. One row per `(source, date)` that has *any* transcript/thread evidence of activity — never fabricate a zero-activity row, and never source a row from `stats-cache.json` in this pass (see Design Notes).
- `pipeline.py` supports `--tool {codex,claude}` and `--from`/`--to YYYY-MM-DD`, matching `inventory.py`'s existing flags and validation, applied as row filters on both outputs.
- Full regeneration each run (write to temp file, atomic rename) — no upsert/dedup logic.
- Reuse `inventory.py`'s tolerant-parsing (skip malformed lines, never crash) and read-only sqlite URI pattern. Stdlib only (`sqlite3`, `json`, `csv`, `argparse`, `pathlib`).

**Ask First:** none — mirrors `inventory.py`'s existing CLI pattern and known source facts; no new decisions needed.

**Never:**
- No parsing of `~/.codex/logs_2.sqlite` or `~/.codex/usage_report.json` — still out of scope (per prior decision).
- No `--repo` filter — that flag is still its own deferred spec, not built yet.
- Do not compute DAU/WAU/MAU or any rollup math in this script — downstream analysis, out of scope here.
- Do not read `~/.claude/stats-cache.json` in this pass — gap-fill is a separate deferred spec.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| First run | `data/*.csv` absent | Both CSVs created from all available sources | N/A |
| Re-run, unchanged sources | `data/*.csv` exist | Regenerated CSVs byte-identical | N/A |
| Claude gap date | Date in `stats-cache.json` but no matching transcript file | No row in either CSV for that date in this pass | N/A |
| `--tool`/`--from`/`--to` given | e.g. `--tool codex --from 2026-07-01 --to 2026-07-31` | Both CSVs contain only matching rows | N/A |
| Malformed transcript line | Truncated/corrupt line in a `*.jsonl` file | Skip the line, continue, session still counted from remaining valid lines | Log one warning per bad line, don't crash |

</frozen-after-approval>

## Code Map

- `scripts/csv_common.py` -- new: shared column definitions (`SESSION_FIELDS`, `DAILY_FIELDS`) and an atomic CSV writer used by both extractors
- `scripts/extract_codex.py` -- new: reads `threads` table, yields session rows + per-day aggregates
- `scripts/extract_claude.py` -- new: reads `projects/**/*.jsonl`, yields session rows + per-day aggregates (no `stats-cache.json` fallback in this pass)
- `scripts/pipeline.py` -- new: CLI (`--tool`/`--from`/`--to`), orchestrates both extractors, writes both CSVs
- `.gitignore` -- edit: add `data/*.csv`

## Tasks & Acceptance

**Execution:**
- [x] `scripts/csv_common.py` -- define `SESSION_FIELDS`, `DAILY_FIELDS` tuples and `atomic_write_csv(path, fieldnames, rows)`, plus a shared `aggregate_daily(sessions)` that both tools' session rows feed into for `daily_activity.csv` -- shared contract, avoids duplicating CSV-writing/aggregation logic per tool
- [x] `scripts/extract_codex.py` -- read `threads` table read-only, yield one session dict per thread (`date` = `created_at`'s day)
- [x] `scripts/extract_claude.py` -- walk `projects/**/*.jsonl` tolerantly, yield one session row per transcript file
- [x] `scripts/pipeline.py` -- `argparse` `--tool`/`--from`/`--to` (same validation as `inventory.py`), call both extractors, aggregate, write both CSVs via `csv_common`
- [x] `.gitignore` -- add `data/*.csv`

**Acceptance Criteria:**
- Given a first run, when `python3.11 scripts/pipeline.py` runs, then `sessions.csv` has ~1058 Codex rows plus one row per parseable Claude transcript, and `daily_activity.csv` covers both tools' transcript-evidenced dates.
- Given Claude's gap dates (2026-06-10 → 2026-06-30, `stats-cache.json`-only), when the pipeline runs, then neither CSV contains rows for those dates.
- Given the pipeline is run twice unchanged, then both CSVs are byte-identical across runs.
- Given `python3.11 scripts/pipeline.py --tool codex --from 2026-07-01 --to 2026-07-31`, then both CSVs contain only Codex rows dated within that window.

## Spec Change Log

- 2026-07-22: Review round 1 (Blind Hunter + Edge Case Hunter, in parallel). Patched: swallowed `sqlite3.Error` in `extract_codex.py` now logs a warning; `atomic_write_csv` uses a PID-suffixed temp file (was clobber-prone across concurrent runs) and `extrasaction="ignore"`; `extract_claude.py`'s directory walk is now guarded against `PermissionError`/`OSError`; non-string numeric `timestamp` values now have an epoch fallback; `pipeline.py`'s sort is defensive against a `None` `session_id`; reversed `--from`/`--to` now errors clearly instead of silently producing empty CSVs. Rejected as already-verified-correct or structurally unreachable: UTC-consistency concern (both sources use UTC — confirmed), epoch-in-seconds concern (confirmed during investigation), session dedup (thread `id` is a SQL `PRIMARY KEY`, transcript filenames are UUIDs), `active` always `1` (matches the spec's explicit no-fabricated-zero-row design). Deferred (see `deferred-work.md`): `message_count` counting tool-result echoes as messages, a row-count-anomaly guard, `project_path` redaction, test suite.
- 2026-07-23: Human requested Codex/Claude reports be separate files rather than one merged file with a `source` column. `pipeline.py` now writes `data/codex/sessions.csv`+`daily_activity.csv` and `data/claude/sessions.csv`+`daily_activity.csv` (same column schema, including `source`, in both). `.gitignore` updated to ignore all of `data/` instead of `data/*.csv`.

## Design Notes

Schema shape follows the DX AI Measurement Framework's utilization dimension (active days / DAU-WAU-MAU style tracking): one `(source, date)` row per day with an `active` flag and volume counts lets a downstream consumer compute active-days-per-week/month via a plain groupby — this script stops at producing that row, not the rollup. `stats-cache.json` gap-fill is deferred (see `deferred-work.md`) so this pass has one clean evidence source per tool. Both tools attribute a session's entire activity to its start date (Codex: `threads.created_at`; Claude: earliest transcript `timestamp`) — consistent across tools, but a session spanning multiple days is counted entirely on day one.

## Verification

**Commands:**
- `python3.11 scripts/pipeline.py && python3.11 scripts/pipeline.py` -- expected: second run's CSVs byte-identical to the first
- `awk -F, 'NR>1{print $1}' data/sessions.csv | sort | uniq -c` -- expected: ~1058 codex rows, one row per Claude transcript file
- `grep 2026-06-15 data/daily_activity.csv` -- expected: no match (gap date correctly absent in this pass)
