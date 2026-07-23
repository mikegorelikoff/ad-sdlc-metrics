# Limitations & open questions

Nothing below blocks using the numbers directionally — trends over time and
tool-vs-tool comparisons within the same tool are solid. These are the places where an
*exact* number needs a caveat, or where a decision is still open. Full detail lives in
`_bmad-output/implementation-artifacts/deferred-work.md`.

## Metric precision

- **The current (in-progress) week/month row is marked, not hidden.** `active_day_rate`
  is still computed against a full period length (7 days / calendar days in month) even
  when the period isn't over yet — a week that's 3 days in with 3 active days shows
  `3/7 = 0.43`, not `3/3 = 1.0`. The `is_partial` column flags exactly this: `1` means
  the period hasn't finished as of the day the report was run, so its `active_day_rate`
  should be read as "so far," not final.
- **`message_count` now excludes tool-result echoes on both tools**, so it's a fairer
  cross-tool comparison than earlier versions of this pipeline. Codex counts rollout
  `response_item` messages (its format keeps tool output as a separate
  `function_call_output` type, never a message). Claude counts every `user`/`assistant`
  transcript record *except* synthetic `user` turns whose content is only a
  `tool_result` block — those are Claude Code echoing a tool's own output back, not
  something a human typed.

## Data completeness

- **Codex `message_count`/`tool_call_count` come from parsing each thread's own rollout
  file** — accurate, but adds a per-session file read. If a rollout file has been moved
  or deleted, those two fields fall back to blank for that session rather than guessing.

## Robustness

- **The row-count sanity check is a warning, not a hard stop.** On a full, unfiltered
  `pipeline.py` run, if a tool's `sessions.csv` row count drops more than 50% from the
  previous run, a warning prints to stderr before the (smaller) result overwrites the
  old CSVs — on the assumption that a human should decide whether to investigate a
  transient read failure, rather than the script silently keeping stale data forever.
  The 50% threshold is a judgment call, not derived from anything; it hasn't needed
  tuning yet.
- **`adoption_report.py` warns rather than errors on all-empty input.** If every
  `data/<tool>/daily_activity.csv` parses to zero rows, it's ambiguous whether that
  means "legitimately no data yet" or "something upstream broke" — a warning is
  printed and empty rollup files are still written either way.

## Privacy

`project_path` (a raw absolute path, which can embed usernames or client/project names)
is included by default, since it's needed for `--repo` filtering and this data never
leaves your machine by default. `pipeline.py --redact-paths` replaces it in
`sessions.csv` with a stable one-way hash instead (`--repo` filtering still runs against
the real path first, so filtering and redaction compose correctly) — use it before
exporting or sharing the CSVs anywhere.

## Out of scope by design

Four of the five DX AI Measurement Framework pillars aren't attempted here at all —
see Methodology for why (they need git/PR history or self-reported
survey data this project intentionally doesn't try to approximate).
