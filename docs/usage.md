# Usage

Requires Python 3.11+ (stdlib only — nothing to `pip install`) and bash.

## No clone, no install

```bash
curl -fsSL https://raw.githubusercontent.com/mikegorelikoff/ai-sdlc-metrics/main/scripts/remote-run.sh | bash
```

Downloads the scripts into a temp directory, runs the full pipeline, prints where the
CSVs landed, and tells you how to delete the temp dir afterward. Pass flags after `--`:

```bash
curl -fsSL https://raw.githubusercontent.com/mikegorelikoff/ai-sdlc-metrics/main/scripts/remote-run.sh | bash -s -- --tool codex --from 2026-07-01
```

## From a local clone

```bash
git clone https://github.com/mikegorelikoff/ai-sdlc-metrics.git
cd ai-sdlc-metrics
./scripts/run.sh
```

`data/` is gitignored — the CSVs contain your own local usage data (project paths,
timestamps, token counts) and are never meant to be committed.

## Running the pieces individually

`run.sh` just calls these three in order — useful to know if you want just one:

```bash
python3 scripts/inventory.py        # read-only report, writes nothing
python3 scripts/pipeline.py         # writes data/codex/, data/claude/ CSVs
python3 scripts/adoption_report.py  # writes adoption_weekly.csv / adoption_monthly.csv
```

## Flags

`run.sh`, `inventory.py`, and `pipeline.py` all accept:

| Flag | Meaning |
|---|---|
| `--tool {codex,claude}` | Only process one tool |
| `--from YYYY-MM-DD` / `--to YYYY-MM-DD` | Inclusive date window |
| `--repo <substring>` | Only sessions whose project path contains this substring. Skips the Claude `stats-cache.json` gap-fill, which has no per-project attribution to filter by. |
| `--redact-paths` | `pipeline.py` only (accepted as a no-op by `inventory.py` for `run.sh`'s flag forwarding). Replaces `project_path` in `sessions.csv` with a stable one-way hash — same path always hashes the same, so grouping by project still works, but the real path can't be recovered. Use before exporting or sharing the CSVs. |

```bash
./scripts/run.sh --tool codex --repo my-project --from 2026-07-01 --to 2026-07-31
./scripts/run.sh --redact-paths
```

`CODEX_HOME`/`CLAUDE_HOME` env vars override the default `~/.codex`/`~/.claude` paths.

## Viewing the docs site locally

```bash
pip install mkdocs-material
mkdocs serve
```
