# Data model

## Sources and their retention

Discovered by `inventory.py`, which reads each source directly rather than trusting
file mtimes or vendor claims:

| Source | Format | Covers |
|---|---|---|
| Codex `sessions/**/*.jsonl` + `state_5.sqlite` `threads` table | jsonl / sqlite | Full history, 2026-03-19 → present |
| Codex `history.jsonl` (prompt text only) | jsonl | 2026-03-31 → present |
| Codex `logs_2.sqlite` (internal debug log) | sqlite | ~10-day rolling window only — not used |
| Claude `projects/**/*.jsonl` (raw transcripts) | jsonl | Only the last few weeks — older files get pruned from disk |
| Claude `stats-cache.json` (precomputed daily aggregates) | json | Partial, gappy older coverage where raw transcripts no longer exist |
| Claude `history.jsonl` (prompt text only) | jsonl | Since first use |

Because the two tools' retention windows don't overlap cleanly, `pipeline.py` treats
Codex's `threads` table and Claude's raw transcripts as the primary evidence, and only
falls back to `stats-cache.json` to fill Claude dates with no surviving transcript.

## `data/<tool>/sessions.csv`

One row per session (human-initiated *and* subagent-spawned — nothing is dropped here).

| Column | Notes |
|---|---|
| `source` | `codex` or `claude` |
| `session_id` | Thread id (Codex) or transcript filename (Claude) |
| `date` | Session start date, `YYYY-MM-DD` |
| `project_path` | Working directory the session ran in. Replaced with a stable one-way hash if `pipeline.py` ran with `--redact-paths` — see Limitations & open questions |
| `model` | Model used, if known |
| `message_count` | Conversational turns (see caveat below) |
| `tool_call_count` | Tool/function calls made |
| `tokens_used` | Total tokens, where available |
| `session_kind` | `human` or `subagent` — see below |
| `parent_session_id` | For `subagent` rows, the session that spawned them |

!!! note "How `message_count` stays comparable across tools"
    Codex counts `response_item` messages from the tool's own rollout format, which
    already keeps tool output as a separate `function_call_output` type, never a
    message. Claude counts every `user`/`assistant` transcript record *except*
    synthetic `user` turns whose content is only a `tool_result` block — Claude Code's
    way of echoing a tool's own output back, not something a human typed. Excluding
    those keeps the two tools' counts on the same footing: human/assistant
    conversational turns only.

### `session_kind`: human vs subagent

Investigation found that a large share of both tools' "sessions" are actually
subagent-spawned work — not something a human sat down and typed into:

- **Codex:** 58% of `threads` rows turned out to be subagent threads, detectable because
  the `source` column holds a `thread_spawn` JSON blob instead of a plain string like
  `cli`/`exec`/`vscode`.
- **Claude Code:** subagent transcripts live at `<session>/subagents/agent-*.jsonl`,
  nested under their parent session's own directory.

Every row is labeled `human` or `subagent`. `sessions.csv` keeps both; `daily_activity.csv`
and everything downstream default to human-only, so adoption numbers reflect direct
usage rather than autonomous background work.

## `data/<tool>/daily_activity.csv`

One row per `(source, date)` with **any** evidence of human activity that day — never a
fabricated zero-activity row.

| Column | Notes |
|---|---|
| `active` | Always `1` — a row only exists when there's evidence |
| `session_count` | Sessions that day |
| `message_count`, `tool_call_count`, `tokens_used` | Summed from that day's sessions; blank if genuinely unknown |

## `data/<tool>/adoption_weekly.csv` / `adoption_monthly.csv`

One row per `(source, period_start)`, built entirely from `daily_activity.csv` — no
direct access to the source directories at this stage.

| Column | Notes |
|---|---|
| `active_days` / `days_in_period` / `active_day_rate` | The core adoption signal — `active_days / days_in_period`, DX framework's utilization dimension applied to a single user |
| `is_partial` | `1` if this period hasn't finished as of the day the report ran (e.g. the current week) — its `active_day_rate` is a "so far" number, not final |
| `session_share_pct` | This tool's share of combined Codex+Claude session volume that period |

`days_in_period` uses a fixed length (7 for weekly, calendar days for monthly) rather
than clipping to the dataset's actual start/end — so the very first and last periods in
the output can understate `active_day_rate` even when `is_partial` is `0`. See
Limitations & open questions.
