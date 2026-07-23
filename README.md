# metrics

Personal AI-tool adoption metrics for Codex CLI and Claude Code, built entirely from
data already on your machine (`~/.codex`, `~/.claude`) — read-only, nothing is uploaded
anywhere.

## Run it — no clone, no install

```bash
curl -fsSL https://raw.githubusercontent.com/mikegorelikoff/ad-sdlc-metrics/main/scripts/remote-run.sh | bash
```

That's it. It downloads the scripts into a temp dir, runs the full pipeline, prints
where the CSVs landed, and tells you how to delete the temp dir when you're done.
Pass flags after `--`, e.g. only Codex, last 30 days:

```bash
curl -fsSL https://raw.githubusercontent.com/mikegorelikoff/ad-sdlc-metrics/main/scripts/remote-run.sh | bash -s -- --tool codex --from 2026-07-01
```

## Run it from a local clone

```bash
git clone https://github.com/mikegorelikoff/ad-sdlc-metrics.git
cd ad-sdlc-metrics
./scripts/run.sh
```

`data/` is gitignored — the CSVs it generates contain your own local usage data
(project paths, timestamps, token counts) and are never meant to be committed.

## What's here

| Script | What it does |
|---|---|
| `scripts/run.sh` | Runs the three scripts below in order. This is what you actually want to run. |
| `scripts/inventory.py` | Read-only report: what data sources exist, their date range, record counts. No files written. |
| `scripts/pipeline.py` | Normalizes Codex + Claude Code sessions into `data/codex/` and `data/claude/` CSVs (`sessions.csv`, `daily_activity.csv`). |
| `scripts/adoption_report.py` | Rolls `daily_activity.csv` up into `adoption_weekly.csv` / `adoption_monthly.csv` per tool — active-day rate, volume, and each tool's share of total sessions. |

Requires Python 3.11+ (stdlib only, no dependencies to install) and bash.

## Flags

`run.sh` (and `inventory.py`/`pipeline.py` directly) accept:

- `--tool {codex,claude}` — only process one tool
- `--from YYYY-MM-DD` / `--to YYYY-MM-DD` — inclusive date window
- `--repo <substring>` — only include sessions whose project path contains this substring (skips the Claude `stats-cache.json` gap-fill, which has no per-project attribution)

```bash
./scripts/run.sh --tool codex --repo my-project --from 2026-07-01 --to 2026-07-31
```

## Notes

- `CODEX_HOME`/`CLAUDE_HOME` env vars override the default `~/.codex`/`~/.claude` paths.
- Subagent-spawned sessions (background/parallel agent work) are tracked separately
  (`session_kind` column in `sessions.csv`) and excluded from `daily_activity.csv` by
  default, so adoption numbers reflect direct human usage.
- Design history and known limitations: `_bmad-output/implementation-artifacts/`
  (specs) and `deferred-work.md` in the same directory.

## Docs

`docs/` has the full write-up: why this exists, the methodology it's scoped against,
the data model, and known limitations. View it with:

```bash
pip install mkdocs-material
mkdocs serve
```
