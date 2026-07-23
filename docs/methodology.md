# Methodology

This project is scoped against the DX AI Measurement Framework, which is the closest
thing the industry has to a standard for measuring AI coding-tool impact. It defines
five pillars plus a qualitative layer (full detail in Framework reference). This page
explains, pillar by pillar, what's covered from local `~/.codex`/`~/.claude` data, what
genuinely isn't, and — for each gap — specifically what data would be required to close
it and why that data isn't sitting on this machine.

| Pillar | Covered here? |
|---|---|
| 1. Adoption (utilization) | Yes |
| 2. AI Code Share | No |
| 3. Velocity | No |
| 4. Quality | No |
| 5. Cost and ROI | Partial |
| Qualitative layer | No |

## Pillar 1: Adoption — why this is the one pillar fully answerable here

The framework's utilization metrics (DAU/WAU/MAU) are population statistics: what
fraction of a team's developers used AI at least once in a given day/week/month. For a
single person, "population" collapses to one, and the question becomes: **what fraction
of days in a given week or month did I actually use each tool?** That's exactly
`active_days / days_in_period` — `active_day_rate` in `adoption_weekly.csv` and
`adoption_monthly.csv`. It's not a metaphor for WAU, it's the same formula with a
population size of one, which is why it's directly comparable to the framework's
published benchmarks (30-40% average WAU, 60-70% at "mature" adoption — see Framework
reference for the full numbers this is checked against).

This pillar is answerable because everything it needs — a timestamp and an indication
of which tool was used — is exactly what a session log inherently contains. Nothing had
to be inferred or estimated.

## Pillar 2: AI Code Share — why it isn't answerable here

This pillar asks what percentage of merged code was AI-touched (by PR, by line, by
commit). Answering it requires correlating AI session activity with actual git commits
and pull requests — commit SHAs, PR merge events, diff line counts. Neither Codex nor
Claude Code's local logs record a link back to the commits that came out of a session;
that link only exists in git history and, for PR-level attribution, a forge's API
(GitHub, GitLab). This project deliberately stays inside `~/.codex`/`~/.claude` and
doesn't reach into arbitrary git repositories on disk or call out to external APIs, so
this pillar is out of reach by design, not by oversight.

## Pillar 3: Velocity — why it isn't answerable here

Complexity-Adjusted Throughput requires two things this project has no access to: a
complexity/point estimate per unit of work (from a ticket tracker) and deployment/merge
timestamps (from a forge or CI system). Session logs record when *you* were active, not
when the resulting work shipped. Even with perfect session data, there's no way to
derive "time from first commit to production" without integrating a second system this
project intentionally doesn't touch.

## Pillar 4: Quality — why it isn't answerable here

Code Turnover Rate (how much AI-generated code gets rewritten or deleted within 30/90
days) is inherently longitudinal git-diff analysis: it needs to know which lines came
from an AI-assisted commit and then watch what happens to those specific lines over the
following weeks. That requires git blame history correlated with session timestamps —
again, outside the scope of what a local tool log contains, and the kind of analysis
that needs its own dedicated tooling against an actual git repository, not a session-log
normalizer.

## Pillar 5: Cost and ROI — why this is partial, not full

`tokens_used` is real, tracked per session, and rolled up into `daily_activity.csv` and
the adoption reports — token volume genuinely is derivable from local data. What isn't
derivable is an accurate dollar figure. Investigation into Codex's own historical usage
snapshot (`usage_report.json`, generated once and never refreshed) found every cost
field hardcoded to `$0.00`, which is a strong signal that at least this machine's Codex
usage is billed on a flat-rate/subscription basis rather than metered per token.
Computing a dollar estimate by multiplying `tokens_used` against public API list prices
would produce a number that looks precise and describes a billing model that isn't
actually the one in effect — exactly the kind of confident-but-wrong number this project
tries to avoid. So token volume is reported; a dollar figure is not.

## Qualitative layer — why it isn't attempted

Perceived time savings, post-acceptance edit rate, task fit, adoption barriers, and NPS
are all explicitly self-reported measurements on a survey cadence. There is no log entry
anywhere that encodes "how much time did this actually save me" — that's a subjective
judgment only the person doing the work can make. Mining logs for a proxy of this would
mean inventing a number and presenting it as if it were measured, which is exactly the
failure mode this project is trying to avoid throughout.

## Design decisions this drove

- **`session_kind` (`human` vs `subagent`)** — the single most consequential design
  decision in the whole pipeline. Investigation found 58% of Codex's `threads` table was
  actually subagent-spawned work, not direct human sessions (see Why this exists for the
  full finding). An adoption/utilization metric is specifically about *how often a
  person reaches for the tool* — the framework's own "power user" definition is "daily
  usage across multiple AI tool modes," which describes a human's behavior pattern, not
  an agent spawning background workers. Counting subagent threads as adoption would have
  systematically inflated the numbers in direct proportion to how much delegated work
  happened to be running, which is the opposite of what an adoption metric is for. Every
  session is labeled `human` or `subagent`; daily/weekly/monthly rollups default to
  human-only.
- **Per-tool output files, not one merged file with a `source` column** — Codex and
  Claude Code reports live in `data/codex/` and `data/claude/` separately, so each
  tool's report reads cleanly on its own without filtering, while `session_share_pct`
  still compares across both internally before the output is split.
- **No rollup math baked into the CSV normalization step** — `pipeline.py` only
  normalizes raw data into `sessions.csv`/`daily_activity.csv`; `adoption_report.py` is
  a separate step that computes the actual metrics from that normalized data. Keeping
  these separate means the normalized data stays reusable for questions this project
  hasn't asked yet, without needing to re-derive it from the source directories again.
- **Nothing invented.** Where a pillar needs data this project doesn't have, that's
  stated outright (this page) rather than approximated with a number that looks
  authoritative and isn't. A wrong number is worse than no number.
