# Why this exists

## The question that started it

I use two AI coding tools day to day — Codex CLI and Claude Code — and genuinely
couldn't answer a simple question about my own behavior: *am I actually adopting these
tools as part of how I work, or am I just occasionally poking at them?* That's not a
rhetorical question. Personal habits are hard to self-assess accurately — recency bias
makes last week feel like "constant use" and a quiet month feel shorter than it was.
The only way to answer it honestly is to look at the actual usage data, not the
impression of it.

Both tools ship their own local dashboards and stats files. The obvious first move was
to just look at those. That turned out not to be good enough, for reasons that only
became clear once I went and read the raw data underneath the dashboards.

## What the investigation actually found

Before writing a line of pipeline code, the first step was a plain inventory: what data
exists in `~/.codex` and `~/.claude`, in what format, covering what dates. That
inventory (now `inventory.py`, kept in the repo as a permanent, rerunnable check) turned
up three separate problems, each of which would have quietly corrupted any adoption
number built on top of it.

### 1. The two tools don't retain data on the same timeline

Codex's session transcripts (`sessions/**/*.jsonl`) and its `threads` sqlite table go
back to the very first session on this machine. Claude Code's raw session transcripts
(`projects/**/*.jsonl`) only cover roughly the most recent few weeks — older transcript
files are deleted from disk once Claude Code decides they've aged out. Claude does keep
a secondary rollup, `stats-cache.json`, with some older daily aggregates — but it has
real gaps in the middle of its own coverage, and its own `lastComputedDate` field
claimed data was current up to a date well past where its actual `dailyActivity` array
stopped. In other words: even the vendor's own cache had drifted out of sync with
itself. If a tool's own internal dashboard can't be trusted to describe its own data
correctly, an adoption number pulled from that dashboard inherits the same problem
silently.

Trying to compute "days active in the last 90 days" naively against these two sources
would have produced numbers that looked precise and were actually comparing a complete
four-month history against three incomplete weeks — without anything telling you that's
what happened.

### 2. Most of what looks like a "session" isn't a human sitting down to type

Digging into Codex's `threads` table, 613 of 1058 rows — 58% — turned out to be
subagent threads: work spawned by another agent (a `thread_spawn` call, visible as a
JSON blob in the `source` column instead of a plain string like `cli` or `vscode`), not
a session a person opened and typed into. Claude Code has the identical pattern:
subagent transcripts live at `<session>/subagents/agent-*.jsonl`, nested under the
parent session that spawned them.

This matters enormously for an *adoption* metric specifically, because adoption is
supposed to measure human behavior — how often you reach for the tool — not how much
autonomous compute the tool did on your behalf after you reached for it once. A number
that doesn't separate these two things doesn't just have a small margin of error; it
systematically overstates usage in exact proportion to how much delegated/background
work happens to be running, which has nothing to do with how often you're actually
adopting the tool day to day. Every session in this project is labeled `human` or
`subagent` for exactly this reason — see Data model for the mechanics.

### 3. Neither tool's dashboard answers the comparative question

Even setting the above aside, neither tool's built-in stats page is designed to answer
"which of these two tools am I actually reaching for, and is that changing over time."
That's a two-tool question by definition, and a single-tool dashboard structurally can't
answer it. Answering it required pulling both tools' data into one comparable shape.

## Why this is grounded in an external framework instead of an invented metric

It would have been easy to invent a metric — "sessions per week," say — and call it
done. That number would have been fast to build and impossible to sanity-check against
anything. Instead this project is deliberately scoped against the DX AI Measurement
Framework, an existing industry attempt to define what "AI adoption" and "AI impact"
actually mean for engineering teams (see Framework reference for the source material).
Two things follow from that choice:

- **The metric this project computes — active-day rate — has a known, named
  counterpart** (DAU/WAU/MAU-style utilization) with published industry benchmarks to
  compare against, instead of being a number that only means something relative to
  itself.
- **The pillars this project does *not* attempt (Code Share, Velocity, Quality,
  Cost/ROI) are explicitly named as gaps**, not silently ignored. See Methodology for
  why each one specifically can't be answered from local tool data, and what would be
  required to answer it.

The guiding principle throughout was: a wrong number is worse than no number. Where the
data genuinely doesn't support a metric, that's stated outright rather than
approximated with something that looks precise and isn't.

## What this actually is

A small, dependency-free Python pipeline, run entirely locally, that:

1. **Inventories** what data exists and for what period (`inventory.py`) — read-only,
   no files written, just ground truth established before anything downstream is
   allowed to trust it.
2. **Normalizes** both tools' session logs into one shared schema, split into separate
   per-tool files (`data/codex/`, `data/claude/`) rather than one merged file, and
   explicitly classifies every session as `human` or `subagent`.
3. **Rolls up** the normalized daily data into weekly/monthly adoption metrics —
   active-day rate, volume, and each tool's share of total usage — as a distinct final
   step, so the normalized data stays reusable for questions this project hasn't asked
   yet.

Everything runs locally, reads only your own machine's data, and writes nothing back to
either tool. See Usage to run it, and Limitations & open questions for what's still
rough around the edges — including a few places where the numbers are directionally
solid but not yet exact.
