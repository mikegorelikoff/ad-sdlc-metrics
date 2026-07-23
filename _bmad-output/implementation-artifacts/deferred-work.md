- source_spec: `_bmad-output/implementation-artifacts/spec-adoption-metrics-csv-pipeline.md`
  summary: Consider redacting/hashing `project_path` in sessions.csv (raw absolute paths can embed usernames/client or project names) if this data is ever exported or shared beyond local personal use.
  evidence: Blind Hunter flagged this; not a concern for the current personal-local-use scope, but worth revisiting before any sharing/export feature.
  status: open
