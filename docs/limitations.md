# Limitations & open questions

Nothing below blocks using the numbers directionally — trends over time and
tool-vs-tool comparisons within the same tool are solid. These are the places where an
*exact* number needs a caveat, or where a decision is still open. Full detail lives in
`_bmad-output/implementation-artifacts/deferred-work.md`.

## Metric precision

- **`message_count` isn't strictly comparable across tools.** Codex counts rollout
  `response_item` messages; Claude counts every `user`/`assistant` transcript record,
  which includes tool-result echoes Claude Code synthesizes internally. Both are
  internally consistent for tracking one tool's own trend — just not a fair head-to-head
  count yet.
- **The current (in-progress) week/month row looks artificially low-adoption.**
  `active_day_rate` is computed against a full period length (7 days / calendar days in
  month) even when the period isn't over yet. A week that's 3 days in with 3 active days
  shows `3/7 = 0.43`, not `3/3 = 1.0`. Deliberately left this way rather than guessing at
  a "partial period" convention — read the most recent row with that in mind.

## Data completeness

- **Codex `message_count`/`tool_call_count` come from parsing each thread's own rollout
  file** — accurate, but adds a per-session file read. If a rollout file has been moved
  or deleted, those two fields fall back to blank for that session rather than guessing.
- **Nested subagent-of-subagent transcripts aren't handled** — `parent_session_id`
  currently always resolves to the top-level human session, which would be wrong (not
  just missing) if a subagent ever spawns its own nested subagent. Not observed in
  practice yet; only one level of nesting has ever shown up in the data.

## Robustness

- **No automated test suite yet.** Coverage today is manual verification against real
  local data (documented in each spec's Verification section) — solid for catching
  regressions during development, but nothing runs automatically. Consolidating into one
  `pytest` suite is tracked as open work.
- **No row-count sanity check.** If `pipeline.py` returns suspiciously fewer sessions
  than a previous run (transient sqlite lock, moved directory), it overwrites the
  existing CSVs with the smaller result and no warning. Needs a human-chosen threshold
  for "suspicious," not an arbitrary guess.

## Privacy

- **`project_path` isn't redacted.** Raw absolute paths can embed usernames or
  client/project names. Not a concern for local personal use, which is the only use case
  today — worth revisiting before any export/sharing feature.

## Out of scope by design

Four of the five DX AI Measurement Framework pillars aren't attempted here at all —
see Methodology for why (they need git/PR history or self-reported
survey data this project intentionally doesn't try to approximate).
