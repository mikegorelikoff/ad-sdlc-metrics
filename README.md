# metrics

Personal AI-tool adoption metrics for [Codex CLI](https://github.com/openai/codex) and
[Claude Code](https://claude.com/claude-code), built entirely from data already on your
machine (`~/.codex`, `~/.claude`) — read-only, nothing is uploaded anywhere.

> Replace `OWNER/REPO` in the commands below with wherever this repo actually lives once pushed.

## What's here

| Script | What it does |
|---|---|
| `scripts/inventory.py` | Read-only report: what data sources exist, their date range, record counts. No files written. |
| `scripts/pipeline.py` | Normalizes Codex + Claude Code sessions into `data/codex/` and `data/claude/` CSVs (`sessions.csv`, `daily_activity.csv`). |
| `scripts/adoption_report.py` | Rolls `daily_activity.csv` up into `adoption_weekly.csv` / `adoption_monthly.csv` per tool — active-day rate, volume, and each tool's share of total sessions. |

Requires Python 3.11+ (stdlib only, no dependencies to install).

## Run it without cloning the repo

Everything below only reads `~/.codex`/`~/.claude` on the machine you run it on and writes
CSVs into a throwaway temp directory — nothing is installed or left behind.

```bash
mkdir -p /tmp/ai-metrics && cd /tmp/ai-metrics
for f in csv_common.py extract_codex.py extract_claude.py inventory.py pipeline.py adoption_report.py; do
  curl -fsSL "https://raw.githubusercontent.com/OWNER/REPO/main/scripts/$f" -o "$f"
done

python3 inventory.py                 # quick look: what data exists, what date range
python3 pipeline.py                  # writes data/codex/, data/claude/ CSVs here
python3 adoption_report.py           # writes data/<tool>/adoption_weekly.csv + adoption_monthly.csv

open data/codex/adoption_weekly.csv  # or just cat it / open in a spreadsheet
```

When you're done, `rm -rf /tmp/ai-metrics` removes everything — the repo itself was
never cloned.

## Run it from a local clone

```bash
git clone https://github.com/OWNER/REPO.git
cd REPO/scripts
python3 pipeline.py && python3 adoption_report.py
```

`data/` is gitignored — the CSVs it generates contain your own local usage data
(project paths, timestamps, token counts) and are never meant to be committed.

## Flags

All three scripts accept:

- `--tool {codex,claude}` — only process one tool
- `--from YYYY-MM-DD` / `--to YYYY-MM-DD` — inclusive date window (`inventory.py`/`pipeline.py` only)
- `--repo <substring>` — only include sessions whose project path contains this substring (`inventory.py`/`pipeline.py` only; skips the Claude `stats-cache.json` gap-fill, which has no per-project attribution)

```bash
python3 pipeline.py --tool codex --repo my-project --from 2026-07-01 --to 2026-07-31
```

## Notes

- `CODEX_HOME`/`CLAUDE_HOME` env vars override the default `~/.codex`/`~/.claude` paths.
- Subagent-spawned sessions (background/parallel agent work) are tracked separately
  (`session_kind` column in `sessions.csv`) and excluded from `daily_activity.csv` by
  default, so adoption numbers reflect direct human usage.
- Design history and known limitations: `_bmad-output/implementation-artifacts/`
  (specs) and `deferred-work.md` in the same directory.
