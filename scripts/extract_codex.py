"""Normalize Codex CLI's ~/.codex/state_5.sqlite `threads` table into session rows."""

import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import csv_common

CODEX_HOME = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")


def _fmt_epoch(ts) -> Optional[str]:
    if not isinstance(ts, (int, float)) or isinstance(ts, bool):
        return None
    try:
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
    except (OverflowError, OSError, ValueError):
        return None


def _parse_rollout_counts(rollout_path: str) -> tuple:
    """Count conversational messages and tool calls in a Codex rollout jsonl file.

    Returns (message_count, tool_call_count), either None if the file can't be read.
    """
    path = Path(rollout_path)
    if not path.exists():
        return (None, None)

    message_count = 0
    tool_call_count = 0
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(record, dict) or record.get("type") != "response_item":
                    continue
                payload = record.get("payload")
                if not isinstance(payload, dict):
                    continue
                ptype = payload.get("type")
                if ptype == "message" and payload.get("role") in ("user", "assistant"):
                    message_count += 1
                elif ptype == "function_call":
                    tool_call_count += 1
    except (OSError, UnicodeDecodeError):
        print(f"warning: could not read {path}", file=sys.stderr)
        return (None, None)

    return (message_count, tool_call_count)


def _parent_thread_id(source_col) -> Optional[str]:
    """Extract the parent_thread_id from a thread_spawn JSON source column, if present."""
    if not isinstance(source_col, str) or not source_col.strip().startswith("{"):
        return None
    try:
        data = json.loads(source_col)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    subagent = data.get("subagent")
    spawn = subagent.get("thread_spawn") if isinstance(subagent, dict) else None
    parent = spawn.get("parent_thread_id") if isinstance(spawn, dict) else None
    return parent if isinstance(parent, str) else None


def get_sessions(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    repo: Optional[str] = None,
) -> list:
    db_path = CODEX_HOME / "state_5.sqlite"
    if not db_path.exists():
        return []

    from_epoch, to_epoch = csv_common.epoch_bounds(date_from, date_to)
    where = []
    params: list = []
    if from_epoch is not None:
        where.append("created_at >= ?")
        params.append(from_epoch)
    if to_epoch is not None:
        where.append("created_at <= ?")
        params.append(to_epoch)
    if repo:
        where.append("cwd LIKE ? ESCAPE '\\'")
        escaped = repo.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        params.append(f"%{escaped}%")
    where_clause = f"WHERE {' AND '.join(where)}" if where else ""

    try:
        uri = f"file:{db_path}?mode=ro"
        con = sqlite3.connect(uri, uri=True)
        try:
            cur = con.execute(
                f"SELECT id, created_at, cwd, model, tokens_used, source, rollout_path "
                f"FROM threads {where_clause}",
                params,
            )
            rows = cur.fetchall()
        finally:
            con.close()
    except sqlite3.Error as exc:
        print(f"warning: could not read {db_path}: {exc}", file=sys.stderr)
        return []

    sessions = []
    for session_id, created_at, cwd, model, tokens_used, source_col, rollout_path in rows:
        date = _fmt_epoch(created_at)
        if date is None:
            continue
        # threads.source holds a plain surface string ("cli"/"exec"/"vscode") for
        # human-initiated threads, or a JSON thread_spawn blob for subagent
        # threads -- verified against this machine's actual threads.source values.
        is_subagent = isinstance(source_col, str) and source_col.strip().startswith("{")
        message_count, tool_call_count = (
            _parse_rollout_counts(rollout_path) if isinstance(rollout_path, str) else (None, None)
        )
        sessions.append(
            {
                "source": "codex",
                "session_id": session_id,
                "date": date,
                "project_path": cwd or "",
                "model": model or "",
                "message_count": message_count,
                "tool_call_count": tool_call_count,
                "tokens_used": tokens_used if isinstance(tokens_used, (int, float)) else None,
                "session_kind": "subagent" if is_subagent else "human",
                "parent_session_id": _parent_thread_id(source_col),
            }
        )
    return sessions
