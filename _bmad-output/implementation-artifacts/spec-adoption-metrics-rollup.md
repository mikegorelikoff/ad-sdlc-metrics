---
title: 'Weekly/monthly AI adoption rollup (active-day rate, volume, tool share)'
type: 'feature'
created: '2026-07-22'
status: 'done'
review_loop_iteration: 0
context: []
baseline_commit: 'NO_VCS'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `data/sessions.csv`/`data/daily_activity.csv` (from `pipeline.py`) are per-day raw facts, not adoption metrics. Per the DX AI Measurement Framework and 2026 industry benchmarks (healthy WAU >50%, mature target 60–70%), the useful single-user analog is **active-day rate per week/month per tool** plus volume and tool-share trend — none of which exist yet.

**Approach:** Build `scripts/adoption_report.py`, reading only the two existing CSVs (never touching `~/.codex`/`~/.claude` directly), and writing `data/adoption_weekly.csv` (ISO week, Monday-start) and `data/adoption_monthly.csv` (calendar month) — one row per `(source, period_start)` with active-day rate, volume counts, and this tool's share of that period's total sessions across both tools.

## Boundaries & Constraints

**Always:**
- Input only `data/sessions.csv` and `data/daily_activity.csv`; never read `~/.codex`/`~/.claude` directly (re-run `pipeline.py` first if those are stale — this script doesn't do that itself).
- Output columns (identical for both CSVs): `source`, `period_start` (`YYYY-MM-DD`, Monday for weekly / 1st for monthly), `active_days`, `days_in_period` (`7` for weekly; actual calendar days for monthly), `active_day_rate` (`active_days / days_in_period`, rounded to 2 decimals), `session_count`, `message_count`, `tool_call_count`, `tokens_used`, `session_share_pct` (this source's `session_count` as a percent of both sources' combined `session_count` that period; `100.0` if the other source had zero sessions that period).
- One row per `(source, period_start)` only for periods where that source has `session_count > 0` — never fabricate a zero-activity period row (same rule as `daily_activity.csv`).
- `message_count`/`tool_call_count`/`tokens_used` are summed from `daily_activity.csv` for the period, staying blank if every contributing day has that field blank (reuse `csv_common._sum_optional` semantics).
- Full regeneration each run (atomic write via `csv_common.atomic_write_csv`) — no upsert logic.
- Stdlib only (`csv`, `datetime`, `pathlib`).

**Ask First:** none — schema and formulas are fully specified above.

**Never:**
- Do not read the source directories directly, or re-derive session-level data — this script only aggregates the two existing CSVs.
- Do not apply `days_in_period` clipping for partial first/last periods (e.g. a dataset starting mid-week) — always use the fixed `7`/calendar-days-in-month, even though this may understate `active_day_rate` for the very first/last period. Documented as a known limitation in Design Notes, not solved here.
- Do not compute any metric requiring data this repo doesn't have (e.g. acceptance rate, code churn, lines-of-code) — scope is strictly what's derivable from `sessions.csv`/`daily_activity.csv`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path | Both CSVs present with current data | Both rollup CSVs written, one row per active `(source, period)` | N/A |
| Missing input CSV | `data/sessions.csv` or `data/daily_activity.csv` absent | Print a clear message naming the missing file, exit non-zero, write nothing | N/A |
| Only one tool active in a period | e.g. only Codex has sessions that week | Codex row has `session_share_pct = 100.0`; no Claude row for that period | N/A |
| Re-run, unchanged inputs | Rollup CSVs already exist | Regenerated files byte-identical | N/A |

</frozen-after-approval>

## Code Map

- `scripts/adoption_report.py` -- new: reads both input CSVs, computes weekly/monthly rollups, writes both output CSVs
- `scripts/csv_common.py` -- reused: `atomic_write_csv`, `sum_optional` (renamed from `_sum_optional` during review since it's now used across module boundaries)

## Tasks & Acceptance

**Execution:**
- [x] `scripts/adoption_report.py` -- load `sessions.csv`/`daily_activity.csv` via stdlib `csv.DictReader`; exit clearly if either is missing
- [x] `scripts/adoption_report.py` -- group `daily_activity.csv` rows into ISO weeks (Monday-start) and calendar months per source, computing `active_days`, `days_in_period`, `active_day_rate`, and summed volume columns
- [x] `scripts/adoption_report.py` -- compute `session_share_pct` per `(source, period)` by joining against the other source's `session_count` for the same period (0 if absent)
- [x] `scripts/adoption_report.py` -- write `data/adoption_weekly.csv` and `data/adoption_monthly.csv` via `csv_common.atomic_write_csv`
- [x] `.gitignore` -- confirmed existing `data/*.csv` entry already covers `adoption_*.csv`

**Acceptance Criteria:**
- Given current `data/sessions.csv`/`data/daily_activity.csv`, when `python3.11 scripts/adoption_report.py` runs, then both rollup CSVs are created with plausible `active_day_rate` values between 0 and 1.
- Given a week where only Codex has sessions, then Codex's row that week has `session_share_pct = 100.0` and no Claude row exists for it.
- Given the script is run twice unchanged, then both output CSVs are byte-identical.
- Given `data/sessions.csv` is missing, when the script runs, then it prints a clear error naming the missing file and exits non-zero without writing anything.

## Spec Change Log

- 2026-07-22: Review round 1 (Blind Hunter + Edge Case Hunter, in parallel). Patched: `csv_common._sum_optional` renamed to public `sum_optional` (was a leaky-abstraction private-API reach across modules); per-row parsing of `daily_activity.csv` is now tolerant (malformed/duplicate rows skipped with a warning instead of raising); output rows sort chronologically (`period_start`, then `source`) instead of source-major; `active_days` defensively clamped to `days_in_period` so a residual data anomaly can't push `active_day_rate` above `1.0`. Rejected as already-deliberate spec decisions: the in-progress-period rate deflation (explicitly called out in this spec's own Never/Design Notes) and the unused-but-checked `sessions.csv` (its presence is intentionally used as a "pipeline has run" signal, not for its content — added a clarifying comment). Deferred (see `deferred-work.md`): marking the current period as partial, a test suite, warning on zero-row input.
- 2026-07-23: Human requested Codex/Claude reports be separate files. `adoption_report.py` now reads `data/<tool>/daily_activity.csv` for each tool with data present, and writes `data/codex/adoption_weekly.csv`+`adoption_monthly.csv` and `data/claude/adoption_weekly.csv`+`adoption_monthly.csv` separately. `session_share_pct` is still computed across both tools' combined volume internally before splitting the output.

## Design Notes

`days_in_period` is fixed (7 for weekly, calendar days for monthly) rather than clipped to the dataset's actual start/end — the very first and last periods in the output may understate `active_day_rate` if the dataset doesn't start/end on a period boundary. Metrics here answer "how active was I, as a share of a full week/month" per the DX framework's utilization dimension, not raw counts (already in `daily_activity.csv`).

## Verification

**Commands:**
- `python3.11 scripts/adoption_report.py` -- expected: both CSVs created, no traceback
- `column -s, -t data/adoption_weekly.csv | less -S` (or open in a spreadsheet) -- expected: `active_day_rate` between 0 and 1, `session_share_pct` between 0 and 100
