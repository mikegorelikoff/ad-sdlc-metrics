# ai-sdlc-metrics

Personal AI-tool adoption metrics for Codex CLI and Claude Code, built entirely from
data already on your machine — read-only, nothing uploaded anywhere, nothing invented.

## Why this exists

Using two AI coding tools day to day and wanting an honest answer to "am I actually
adopting these, or just occasionally poking at them" turns out to be harder than
checking either tool's built-in dashboard. Investigation into the raw data under
`~/.codex` and `~/.claude` found the two tools don't retain history on the same
timeline, that a large share of what looks like "sessions" is actually autonomous
subagent work rather than a human typing, and that neither tool's dashboard can answer
the two-tool comparison question at all. This project exists to fix that: normalize
both tools' logs into one comparable shape, separate real human usage from background
agent work, and roll it up into a metric grounded in an existing industry framework
(the DX AI Measurement Framework) rather than an invented number.

The full reasoning — including the specific data-quality findings that drove every
design decision — is in `docs/index.md` and `docs/methodology.md`. This README is the
quick version.

## Quick start

Requires Python 3.11+ (standard library only — nothing to install) and bash.

No clone needed:

```bash
curl -fsSL https://raw.githubusercontent.com/mikegorelikoff/ai-sdlc-metrics/main/scripts/remote-run.sh | bash
```

This downloads the scripts into a temp directory, runs the full pipeline, prints where
the CSVs landed, and tells you how to delete the temp dir afterward. Pass flags after
`--` (see Flags below):

```bash
curl -fsSL https://raw.githubusercontent.com/mikegorelikoff/ai-sdlc-metrics/main/scripts/remote-run.sh | bash -s -- --tool codex --from 2026-07-01
```

Or from a local clone:

```bash
git clone https://github.com/mikegorelikoff/ai-sdlc-metrics.git
cd ai-sdlc-metrics
./scripts/run.sh
```

`data/` is gitignored — the CSVs it generates contain your own local usage data
(project paths, timestamps, token counts) and are never meant to be committed.

## What's here

| Script | What it does |
|---|---|
| `scripts/run.sh` | Runs the three scripts below in order. This is what you actually want to run. |
| `scripts/inventory.py` | Read-only report: what data sources exist, their date range, record counts. Writes nothing. |
| `scripts/pipeline.py` | Normalizes Codex + Claude Code sessions into `data/codex/` and `data/claude/` CSVs (`sessions.csv`, `daily_activity.csv`), classifying every session as human-initiated or subagent-spawned. |
| `scripts/adoption_report.py` | Rolls `daily_activity.csv` up into `adoption_weekly.csv` / `adoption_monthly.csv` per tool — active-day rate, volume, and each tool's share of total sessions. |

Everything runs locally against your own machine's data. Nothing is written back to
either tool, and nothing leaves your machine.

## Flags

`run.sh` (and `inventory.py`/`pipeline.py` directly) accept:

| Flag | Meaning |
|---|---|
| `--tool {codex,claude}` | Only process one tool |
| `--from YYYY-MM-DD` / `--to YYYY-MM-DD` | Inclusive date window |
| `--repo <substring>` | Only sessions whose project path contains this substring. Skips the Claude `stats-cache.json` gap-fill, which has no per-project attribution. |
| `--redact-paths` | `pipeline.py` only. Replaces `project_path` in `sessions.csv` with a stable one-way hash — use before exporting or sharing the CSVs anywhere. |

```bash
./scripts/run.sh --tool codex --repo my-project --from 2026-07-01 --to 2026-07-31
./scripts/run.sh --redact-paths   # before sharing the output CSVs with anyone
```

`CODEX_HOME`/`CLAUDE_HOME` env vars override the default `~/.codex`/`~/.claude` paths.

## Documentation

`docs/` is a full mkdocs-material site covering the motivation, the methodology (mapped
against the DX AI Measurement Framework's five pillars, and why four of them are
intentionally out of scope here), the exact CSV schema, and known limitations. View it
locally:

```bash
pip install mkdocs-material
mkdocs serve
```

Design history — every decision this pipeline made and why, including what review
caught and fixed along the way — lives in `_bmad-output/implementation-artifacts/`.
Known gaps and open questions are tracked in `deferred-work.md` in that same directory.

## Tests

```bash
pip install pytest
python3 -m pytest
```

Tests run against fixture `~/.codex`/`~/.claude` directories built under pytest's
`tmp_path`, never your real data.

## Community

- Contributing: `CONTRIBUTING.md`
- Code of conduct: `CODE_OF_CONDUCT.md`
- Reporting a security issue: `SECURITY.md`

## License

Apache License 2.0 — see `LICENSE`.
