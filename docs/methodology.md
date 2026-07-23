# Methodology

This project is scoped against the DX AI Measurement Framework,
which is the closest thing the industry has to a standard for measuring AI coding-tool
impact. It defines five pillars plus a qualitative layer. Here's what's covered from
local `~/.codex`/`~/.claude` data, and what genuinely isn't.

| Pillar | Covered here? | Why |
|---|---|---|
| **1. Adoption** (DAU/WAU/MAU-style utilization, tool-type split) | Yes | Fully derivable from session/thread timestamps. This is the whole point of the pipeline. |
| **2. AI Code Share** (% PRs/lines/commits AI-touched) | No | Needs git/PR history, which isn't in either tool's local data directory. |
| **3. Velocity** (complexity-weighted throughput, cycle time) | No | Needs ticket/PR complexity scoring and deploy timestamps. |
| **4. Quality** (code turnover, innovation rate) | No | Needs git diff history correlated with AI sessions over time. |
| **5. Cost & ROI** | Partial | `tokens_used` is real and tracked. Actual dollar cost isn't in the data — the one cost field found in Codex's own usage snapshot was always `$0.00` (flat-rate/subscription, not metered), so any dollar figure here would be an estimate against public pricing, not a fact. Not computed. |
| **Qualitative layer** (surveys, NPS, task fit) | No | Requires self-reported input on a cadence — there's nothing to mine from logs for this. |

## Why only Adoption, and why that's still useful

For a single person using two tools, population-level DAU/WAU/MAU collapses to a
simpler, still-useful question: **what fraction of days in a week/month did I actually
use each tool, and how does that trend over time?** That's `active_day_rate` in
`adoption_weekly.csv`/`adoption_monthly.csv` — the direct single-user analog of the
framework's utilization dimension, industry benchmarks for which run 30-40% average WAU,
60-70% at "mature" adoption.

## Design decisions this drove

- **`session_kind` (`human` vs `subagent`)** — adoption should reflect direct usage, not
  autonomous background work. Every session is classified and daily/weekly/monthly
  rollups default to human-only. See Data model.
- **Per-tool output files, not one merged file** — Codex and Claude Code reports live in
  `data/codex/` and `data/claude/` separately rather than one CSV with a `source` column,
  so each tool's report reads cleanly on its own.
- **No rollup math baked into the CSV pipeline itself** — `pipeline.py` only normalizes
  raw data; `adoption_report.py` is a separate step that computes the actual metrics.
  Keeping these separate means the normalized data (`sessions.csv`) stays reusable for
  questions this project hasn't asked yet.
- **Nothing invented.** Where a pillar needs data this project doesn't have (git history,
  self-reported surveys), it's left out rather than approximated. A wrong number is worse
  than no number.
