# Contributing

Thanks for considering a contribution. This started as a personal tool, so the bar for
change is "does this make the local-only, dependency-free, read-only nature of the
project better," not "does this add a feature I want."

## Before you start

- Read `docs/index.md` (why this exists) and `docs/methodology.md` (what's in scope and
  what deliberately isn't) first. A lot of "why doesn't this do X" questions are answered
  there — several pillars of the underlying measurement framework are intentionally out
  of scope because the data to support them honestly isn't in `~/.codex`/`~/.claude`.
- Check `_bmad-output/implementation-artifacts/deferred-work.md` — known gaps and open
  questions are tracked there, and might already cover what you're about to propose.

## Ground rules

- **Stdlib only.** No new third-party dependencies in `scripts/`. The whole point is
  that it runs anywhere with Python 3.11+ and nothing else.
- **Read-only against `~/.codex`/`~/.claude`.** Nothing in this project should ever
  write to, move, or delete anything under those directories.
- **No invented metrics.** If a number can't be honestly derived from the data that
  exists, it doesn't belong here — see `docs/methodology.md` for why several
  measurement-framework pillars are explicitly left out rather than approximated.
- **Idempotent by full regeneration.** The CSV outputs are fully rewritten on each run,
  not incrementally upserted. Keep new features consistent with that model unless you
  have a strong reason not to.

## Making a change

1. Open an issue first for anything beyond a small fix, so the approach can be discussed
   before code is written.
2. Keep changes focused — one logical change per pull request.
3. Run the test suite (`pip install pytest && python3 -m pytest`) — it uses fixture
   `~/.codex`/`~/.claude` directories under `tmp_path`, so it never touches your real
   data. Add tests for new behavior; `tests/conftest.py` has the fixtures for building
   fake Codex threads and Claude transcripts.
4. Update `README.md`/`docs/` if the change affects what a user sees or runs.

## Reporting bugs or gaps

Open an issue with what you ran, what you expected, and what actually happened. If it's
a data-accuracy concern (a number that looks wrong), include the specific CSV row and
the source data shape that produced it if you can.

For security issues, see `SECURITY.md` instead of opening a public issue.
