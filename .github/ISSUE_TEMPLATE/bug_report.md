---
name: Bug report
about: Something in the pipeline or its output is wrong
title: ""
labels: bug
assignees: ""
---

## What happened

A clear description of what's wrong — a script crashed, a number looks incorrect, output
is missing, etc.

## What you expected instead

## How to reproduce

1. Command you ran (e.g. `./scripts/run.sh --tool codex --from 2026-07-01`)
2. Relevant environment details: OS, Python version (`python3 --version`), whether
   `CODEX_HOME`/`CLAUDE_HOME` are overridden

## Relevant output

Paste the exact error/traceback, or the CSV row(s) that look wrong. Redact any absolute
paths, project names, or other content you'd rather not share — a repro with the shape
of the problem (e.g. "a session row has X but should have Y") is enough; the underlying
session data doesn't need to be shared.

## Anything else

Anything you've already tried, or suspect might be the cause.
