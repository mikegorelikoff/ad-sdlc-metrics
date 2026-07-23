---
title: 'Codex + Claude Code local usage data inventory script'
type: 'feature'
created: '2026-07-22'
status: 'done'
review_loop_iteration: 0
context: []
baseline_commit: 'NO_VCS'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Usage/session history for Codex CLI (`~/.codex`) and Claude Code (`~/.claude`) is scattered across jsonl logs and sqlite files with very different, undocumented retention windows (see Design Notes for the specific dates found). There's no script to inventory what's actually available and for what period before building anything on top of it.

**Approach:** Build one read-only Python 3.11 script, `scripts/inventory.py`, that scans both directories and, for each known data source, reports its location, format, record count, and the actual min/max date found by reading the data itself (not file mtimes). Optional `--tool {codex,claude}` restricts output to one tool's three sources; optional `--from YYYY-MM-DD`/`--to YYYY-MM-DD` restrict every source's counted records to that inclusive date window before computing count/min/max. This establishes the ground truth that a later CSV extraction pipeline (deferred, see `deferred-work.md`) will build on.

## Boundaries & Constraints

**Always:**
- Read-only: open every file/db in read-only mode; never write, move, or delete anything under `~/.codex` or `~/.claude`.
- Inventory these six sources specifically: Codex `history.jsonl`, Codex `sessions/**/*.jsonl`, Codex `state_5.sqlite` (`threads` table), Claude `history.jsonl`, Claude `projects/**/*.jsonl`, Claude `stats-cache.json`.
- For each source, report: human label, absolute path(s), format (jsonl/sqlite/json), record count, min date, max date, and one-line note on anything notable (e.g. "rotates, ~10-day window" style gaps) if the min/max reveals a gap versus another source covering the same tool.
- Use only Python 3.11 stdlib (`sqlite3`, `json`, `pathlib`, `argparse`) — no new dependencies.
- Open Codex sqlite files read-only via URI mode (`file:...?mode=ro`) so a running Codex process holding the WAL isn't blocked or corrupted.
- No source's reader may raise an uncaught exception on malformed/unexpected data (non-numeric timestamp, non-string date field, non-dict JSON, out-of-range epoch, non-UTF8 file, non-directory path) — always degrade that one source to "unreadable"/skip-the-record, never abort the whole run.
- `--from`/`--to` are inclusive date bounds (`YYYY-MM-DD`) compared lexically against each record's own date; a record outside the window is excluded from that source's count/min/max, same as if it didn't exist. `--tool` simply omits the other tool's three sections from output; it does not affect counts of the sections still shown.

**Ask First:** none — scope is fully resolved for this spec (the CSV extraction pipeline and `--repo` filtering are both deferred, not in scope here).

**Never:**
- No network calls, no writing any output file — this script only prints to stdout.
- No parsing of `~/.codex/logs_2.sqlite` (198M-row internal log) or `~/.codex/usage_report.json` (stale snapshot) — both explicitly out of scope for this script per prior decision; they belong to the deferred pipeline work if ever revisited.
- Do not attempt to fix or explain retention gaps beyond reporting the observed min/max dates — no speculative root-causing in output.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path | Both `~/.codex` and `~/.claude` present with normal data | Prints all six sources with path, format, count, min/max date | N/A |
| Missing directory | `~/.codex` or `~/.claude` absent on this machine | Reports that tool's sources as "not found", still reports the other tool's sources | N/A |
| Malformed/partial jsonl line | A transcript file has a truncated last line (process killed mid-write) | Skip the bad line, continue parsing the rest of the file, still contributes to count/min/max | Log one warning line with file path, don't crash |
| Codex sqlite locked (app running) | `state_5.sqlite` has an open WAL from a live Codex process | Read-only URI open succeeds without blocking the writer | On any lock/open failure, report that source as "unreadable" and continue with the rest |
| Empty source | A source file exists but has zero records | Report count 0, min/max date as "n/a" | N/A |
| `--tool codex` given | User only wants Codex sources | Only the three Codex sections print | N/A |
| `--from`/`--to` given, no records in window | `--from 2020-01-01 --to 2020-01-02` | Every source reports count 0, min/max "n/a" | N/A |
| Malformed record survives type checks but is structurally wrong (e.g. `timestamp` is an int, not a string; sqlite column holds text instead of epoch) | Any source | Treat as a malformed/unreadable record for that item only, per the crash-safety rule above | Never propagate as an uncaught exception |

</frozen-after-approval>

## Code Map

- `scripts/inventory.py` -- new: scans both dirs, prints per-source report (path, format, count, min/max date)

## Tasks & Acceptance

**Execution:**
- [x] `scripts/inventory.py` -- implement six source-specific readers (two jsonl-line-scan helpers reused across both tools' `history.jsonl` and Codex's `sessions/**/*.jsonl`/Claude's `projects/**/*.jsonl`, one sqlite reader for Codex `threads`, one json reader for Claude `stats-cache.json`), each returning `(path, format, count, min_date, max_date)`; print a formatted report section per source
- [x] `scripts/inventory.py` -- add `argparse` CLI: `--tool {codex,claude}` filters which sections print; `--from`/`--to` (`YYYY-MM-DD`) thread through to every reader to bound which records are counted
- [x] `scripts/inventory.py` -- harden every reader against malformed/unexpected data per the crash-safety rule (type checks before string-slicing or float conversion, broadened exception catches, non-directory guard, non-dict JSON guard) so no single bad record aborts the run

**Acceptance Criteria:**
- Given both `~/.codex` and `~/.claude` exist with current data, when `python3.11 scripts/inventory.py` runs, then it prints exactly six source sections, each with a non-crashing min/max date.
- Given the script is run twice in a row with no changes to source data, then both runs print identical output.
- Given `~/.codex/state_5.sqlite` is open by a live Codex process (WAL present), when the script runs, then it still successfully reads `threads` without erroring or blocking.
- Given `python3.11 scripts/inventory.py --tool claude` runs, then only the three Claude sections print.
- Given `python3.11 scripts/inventory.py --from 2026-07-01 --to 2026-07-31` runs, then every source's count/min/max reflects only records dated within that window.

## Spec Change Log

- 2026-07-22: Original spec covered inventory + a full CSV extraction pipeline (extract_codex.py, extract_claude.py, pipeline.py with a `--repo` filter). Token count (~2398) exceeded the 1600 guideline; human chose to split off `inventory.py` as this spec and defer the CSV pipeline (see `deferred-work.md`).
- 2026-07-22: Human first moved `--repo` into this spec's scope, then, after it pushed the token count back to ~1786, chose to split `--repo` into its own small follow-up spec instead (see `deferred-work.md`). This spec is now unfiltered inventory only. Deduplicated retention-date findings, which had been repeated in both Intent and Design Notes — kept once, in Design Notes.
- 2026-07-22: Review round 1 (Blind Hunter + Edge Case Hunter, run in parallel) found multiple uncaught-exception crash paths on malformed data (non-numeric timestamps, non-string date fields, non-dict JSON, out-of-range epochs, non-UTF8 files, non-directory paths) — classified as `patch` since the spec already required no-crash behavior, code just under-implemented it; fixed directly. `MIN(created_at)`/`MAX(updated_at)` column-mixing in the threads reader was rejected as a finding — it's the intentional design for reporting the table's full coverage span. Missing test suite, no non-zero exit code, and no env-var path overrides were deferred (see `deferred-work.md`) as real but out-of-scope for this small script. Separately, human requested `--tool`/`--from`/`--to` flags mid-review; added to scope here (KEEP: the six-source reader structure and read-only/no-crash guarantees from round 1 survive unchanged).

## Design Notes

Known retention findings from investigation, which this script must be able to reproduce from live data:
- Codex `sessions/*.jsonl` and `state_5.sqlite.threads`: full history, 2026-03-19 → present (1058 sessions).
- Claude `projects/**/*.jsonl`: only 2026-07-01 → present (older sessions already pruned from disk).
- Claude `stats-cache.json`: partial daily aggregates 2026-06-10 → 2026-07-07 (gappy, not continuous).

## Verification

**Commands:**
- `python3.11 scripts/inventory.py` -- expected: prints six sections (Codex history.jsonl, Codex sessions/, Codex threads table, Claude history.jsonl, Claude projects/*.jsonl, Claude stats-cache.json), each with a min/max date and no traceback
- `python3.11 scripts/inventory.py --tool codex` -- expected: only the three Codex sections print
- `python3.11 scripts/inventory.py --from 2026-07-01 --to 2026-07-31` -- expected: counts/dates narrow to that window across all sections, no traceback

## Suggested Review Order

**CLI surface**

- Entry point — argument parsing and dispatch of `--tool`/`--from`/`--to`.
  [`inventory.py:289`](../../scripts/inventory.py#L289)

**Crash-safety hardening (review round 1 fixes)**

- Epoch formatting now returns `None` instead of raising on bad input; callers treat that as a malformed record.
  [`inventory.py:33`](../../scripts/inventory.py#L33)
- Flat jsonl reader: extraction and float/date conversion unified inside one try/except, no more uncaught `ValueError`.
  [`inventory.py:53`](../../scripts/inventory.py#L53)
- Per-session transcript reader: type-checks `timestamp` before slicing, guards non-directory `root`.
  [`inventory.py:106`](../../scripts/inventory.py#L106)
- stats-cache.json reader: guards non-dict top-level JSON and non-dict `dailyActivity` entries.
  [`inventory.py:218`](../../scripts/inventory.py#L218)

**Per-source readers**

- Codex threads table — date-bounded `WHERE` clause added for `--from`/`--to`; `MIN(created_at)`/`MAX(updated_at)` intentionally mixed to report full coverage span.
  [`inventory.py:177`](../../scripts/inventory.py#L177)

