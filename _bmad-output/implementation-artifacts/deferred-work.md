- source_spec: `_bmad-output/implementation-artifacts/spec-adoption-metrics-csv-pipeline.md`
  summary: Refine `extract_claude.py`'s `message_count` to exclude tool-result-echo "user" turns (content blocks that are only a `tool_result`), so it reflects actual human/assistant conversational turns rather than every raw transcript record.
  evidence: Blind Hunter flagged that the current count likely overstates true message volume; real methodological question for the "adoption" metric's precision, but doesn't invalidate directional/relative trend usage — needs a deliberate definition decision, not a quick patch.
  status: open

- source_spec: `_bmad-output/implementation-artifacts/spec-adoption-metrics-csv-pipeline.md`
  summary: Add a row-count sanity check to pipeline.py so a run that returns suspiciously fewer sessions than the previous run (e.g. due to a transient sqlite lock or moved directory) warns instead of silently overwriting good historical CSVs with a near-empty result.
  evidence: Blind Hunter flagged this; real risk, but needs a human-chosen threshold/policy (how much of a drop is "suspicious"?) rather than an arbitrary guess.
  status: open

- source_spec: `_bmad-output/implementation-artifacts/spec-adoption-metrics-csv-pipeline.md`
  summary: Consider redacting/hashing `project_path` in sessions.csv (raw absolute paths can embed usernames/client or project names) if this data is ever exported or shared beyond local personal use.
  evidence: Blind Hunter flagged this; not a concern for the current personal-local-use scope, but worth revisiting before any sharing/export feature.
  status: open

- source_spec: `_bmad-output/implementation-artifacts/spec-adoption-metrics-rollup.md`
  summary: Mark the current (in-progress) week/month row in adoption_weekly.csv/adoption_monthly.csv as partial (e.g. an `is_partial` column) instead of computing active_day_rate against the full period length.
  evidence: Both review agents flagged that the still-in-progress period looks artificially low-adoption rather than "not finished yet" — real interpretive risk, but the spec explicitly deferred this clipping problem already; tracking it here in case the "known limitation" ever needs solving.
  status: open

- source_spec: `_bmad-output/implementation-artifacts/spec-adoption-metrics-rollup.md`
  summary: Warn (rather than silently succeed) when daily_activity.csv parses to zero rows, so a broken upstream pipeline run isn't indistinguishable from "legitimately no data yet."
  evidence: Blind Hunter flagged this; low-cost to add later, not required by the current acceptance criteria.
  status: open

- source_spec: `_bmad-output/implementation-artifacts/spec-finish-deferred-work.md`
  summary: Handle nested subagent-of-subagent transcripts correctly in extract_claude.py — parent_session_id currently always resolves to the top-level human session's uuid (grandparent dir name), which would be wrong (not just missing) if a subagent ever spawns its own nested subagent.
  evidence: Blind Hunter flagged this; not observed in current data (only one level of subagent nesting seen), so left as a documented limitation rather than speculatively handling an unconfirmed shape.
  status: open

- source_spec: `_bmad-output/implementation-artifacts/spec-finish-deferred-work.md`
  summary: extract_codex.py's Codex message_count and extract_claude.py's Claude message_count are computed differently (Codex counts rollout response_item messages; Claude counts every user/assistant transcript record, which includes tool-result-echo turns) and are not truly comparable despite sharing a column name.
  evidence: Blind Hunter flagged this as a sharper version of the existing "tool-result echoes" deferred item above — both point at the same underlying metric-definition question, tracked together.
  status: open
