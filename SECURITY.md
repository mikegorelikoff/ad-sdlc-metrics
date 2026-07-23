# Security Policy

## Scope

This project reads local files under `~/.codex` and `~/.claude` (and, for
`extract_codex.py`, opens `state_5.sqlite` read-only) and writes normalized CSVs into a
local `data/` directory. It makes no network calls and sends no data anywhere. The
realistic security surface is narrow, but the categories worth reporting are:

- Anything that would let this code write, modify, or delete files outside its own
  `data/` output directory
- Anything that would let this code read files outside `~/.codex`/`~/.claude`/`data/`
  without being asked to (e.g. via `CODEX_HOME`/`CLAUDE_HOME` overrides behaving
  unexpectedly)
- Any path-traversal, command-injection, or arbitrary-code-execution issue in how
  `pipeline.py`/`inventory.py`/`adoption_report.py` parse untrusted input (a session's
  own timestamp/path fields)
- Anything in `scripts/remote-run.sh` that could be exploited when piped into `bash`
  from a compromised or spoofed source

## Supported Versions

This is a small personal-scale project without formal versioned releases. Security
fixes are applied to the `main` branch only.

## Reporting a Vulnerability

Please do not open a public issue for a security concern. Instead, email
mike.gorelikov.dev@gmail.com with:

- A description of the issue and its potential impact
- Steps to reproduce, if possible
- Any suggested fix or mitigation you have in mind

Expect an initial response within a few days. This is a personal project maintained on
a best-effort basis, not a company with an SLA, but reports will be taken seriously and
credited unless you ask otherwise.
