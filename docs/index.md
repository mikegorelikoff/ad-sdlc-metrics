# Why this exists

I use two AI coding tools day to day — Codex CLI and Claude Code — and had no real
answer to a simple question: *am I actually adopting these tools, or just occasionally
poking at them?* Both tools ship their own local dashboards and stats files, but they
don't agree with each other, don't cover the same time range, and don't let you compare
one tool against the other.

## What started this

A routine "what data do we have" investigation into `~/.codex` and `~/.claude` turned up
a few things that made "just eyeball the built-in stats" not good enough:

- **Retention windows differ wildly by source.** Codex's session transcripts and its
  `threads` sqlite table go back to day one (2026-03-19). Claude Code's raw session
  transcripts only cover the last few weeks — anything older has already been pruned
  from disk. Claude's own `stats-cache.json` has some older daily aggregates, but with
  real gaps in it.
- **"Sessions" aren't what they look like.** 58% of Codex's `threads` table turned out to
  be subagent-spawned work, not sessions a human actually sat down and typed into.
  Claude Code has the same thing under `<session>/subagents/`. Any adoption number that
  doesn't separate these out is counting autonomous background work as if it were
  hands-on usage.
- **Neither tool's dashboard lets you ask "which one am I actually reaching for."** That's
  the single most useful adoption question for someone using two tools side by side, and
  it required building something new to answer.

## What "adoption" means here

Rather than invent a metric, this project is scoped against the industry-standard DX AI
Measurement Framework, which breaks AI-tool impact into five pillars: Adoption, Code
Share, Velocity, Quality, and Cost/ROI, plus a qualitative survey layer. Of those, only
Adoption (active-day rate, session volume, tool-share trend) is fully answerable from
what's sitting in `~/.codex` and `~/.claude` — everything else needs git/PR history or
self-reported input this project intentionally doesn't try to fake. See Methodology for
the full breakdown of what's covered and what isn't, and why, and Framework reference
for the underlying source data.

## What this actually is

A small, dependency-free Python pipeline that:

1. Inventories what data exists and for what period (`inventory.py`) — no writes, just
   ground truth before trusting anything downstream.
2. Normalizes both tools' session logs into one shared schema
   (`sessions.csv` / `daily_activity.csv`, split per tool).
3. Rolls that up into weekly/monthly adoption metrics
   (`adoption_weekly.csv` / `adoption_monthly.csv`) — active-day rate, volume, and
   each tool's share of total usage.

Everything runs locally, reads only your own machine's data, and writes nothing back to
either tool. See Usage to run it, and Limitations & open questions for what's still
rough around the edges.
