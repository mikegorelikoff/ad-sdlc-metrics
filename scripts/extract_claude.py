"""Normalize Claude Code's ~/.claude/projects/**/*.jsonl transcripts into session rows."""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

CLAUDE_HOME = Path(os.environ.get("CLAUDE_HOME") or Path.home() / ".claude")

_USAGE_KEYS = (
    "input_tokens",
    "output_tokens",
    "cache_read_input_tokens",
    "cache_creation_input_tokens",
)


def _parse_transcript(fpath: Path) -> Optional[dict]:
    session_id = fpath.stem
    min_date: Optional[str] = None
    project_path = ""
    model = ""
    message_count = 0
    tool_call_count = 0
    tokens_total = 0
    tokens_seen = False

    try:
        with fpath.open("r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(record, dict):
                    continue

                ts = record.get("timestamp")
                date = None
                if isinstance(ts, str) and len(ts) >= 10:
                    date = ts[:10]
                elif isinstance(ts, (int, float)) and not isinstance(ts, bool):
                    try:
                        epoch = ts / 1000 if ts > 10**12 else ts
                        date = datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m-%d")
                    except (OverflowError, OSError, ValueError):
                        date = None
                if date is not None and (min_date is None or date < min_date):
                    min_date = date

                if not project_path:
                    cwd = record.get("cwd")
                    if isinstance(cwd, str):
                        project_path = cwd

                if record.get("type") in ("user", "assistant"):
                    message = record.get("message")
                    if isinstance(message, dict):
                        content = message.get("content")
                        # Claude Code represents a tool's result as a synthetic
                        # "user" record whose content is only tool_result blocks --
                        # not something a human authored. Codex's rollout format
                        # keeps tool output as its own "function_call_output" type,
                        # never a "message", so excluding these here keeps the two
                        # tools' message_count columns comparable.
                        is_tool_result_echo = (
                            message.get("role") == "user"
                            and isinstance(content, list)
                            and bool(content)
                            and all(isinstance(b, dict) and b.get("type") == "tool_result" for b in content)
                        )
                        if not is_tool_result_echo:
                            message_count += 1
                        m = message.get("model")
                        if not model and isinstance(m, str):
                            model = m
                        if isinstance(content, list):
                            for block in content:
                                if isinstance(block, dict) and block.get("type") == "tool_use":
                                    tool_call_count += 1
                        usage = message.get("usage")
                        if isinstance(usage, dict):
                            for key in _USAGE_KEYS:
                                v = usage.get(key)
                                if isinstance(v, (int, float)):
                                    tokens_total += v
                                    tokens_seen = True
    except (OSError, UnicodeDecodeError):
        print(f"warning: could not read {fpath}", file=sys.stderr)
        return None

    if min_date is None:
        return None

    # Claude Code writes subagent transcripts as <session_uuid>/subagents/agent-*.jsonl
    # nested under the parent session's own directory -- checking only the
    # immediate parent directory's name (not any ancestor) avoids both false
    # positives from an unrelated dir named e.g. "my-subagents-tool" and from
    # some unrelated deeper ancestor happening to be named "subagents".
    is_subagent = fpath.parent.name.lower() == "subagents"
    # The directory immediately above "subagents" is this transcript's direct
    # parent's own id -- correct at any nesting depth, since a nested
    # subagent-of-subagent would sit at <parent_agent_id>/subagents/agent-*.jsonl,
    # not necessarily under the top-level human session directly.
    parent_session_id = fpath.parent.parent.name if is_subagent else None
    return {
        "source": "claude",
        "session_id": session_id,
        "date": min_date,
        "project_path": project_path,
        "model": model,
        "message_count": message_count,
        "tool_call_count": tool_call_count,
        "tokens_used": tokens_total if tokens_seen else None,
        "session_kind": "subagent" if is_subagent else "human",
        "parent_session_id": parent_session_id,
    }


def get_sessions(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    repo: Optional[str] = None,
) -> list:
    root = CLAUDE_HOME / "projects"
    if not root.exists() or not root.is_dir():
        return []

    try:
        files = sorted(root.rglob("*.jsonl"))
    except OSError as exc:
        print(f"warning: could not list {root}: {exc}", file=sys.stderr)
        return []

    sessions = []
    for fpath in files:
        session = _parse_transcript(fpath)
        if session is None:
            continue
        if date_from and session["date"] < date_from:
            continue
        if date_to and session["date"] > date_to:
            continue
        if repo and repo.lower() not in session["project_path"].lower():
            continue
        sessions.append(session)
    return sessions


def get_stats_cache_gap_days(
    known_dates: set,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> list:
    """Daily-activity rows for Claude dates covered only by stats-cache.json.

    `known_dates` is the set of dates already represented by transcript-based
    sessions -- this only fills in dates stats-cache.json has but transcripts
    don't (e.g. pruned/rotated-away raw session files).
    """
    path = CLAUDE_HOME / "stats-cache.json"
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return []
    if not isinstance(data, dict):
        return []

    daily = data.get("dailyActivity", [])
    daily = daily if isinstance(daily, list) else []
    tokens_by_date = {}
    for entry in data.get("dailyModelTokens", []) if isinstance(data.get("dailyModelTokens"), list) else []:
        if not isinstance(entry, dict) or not isinstance(entry.get("date"), str):
            continue
        by_model = entry.get("tokensByModel")
        if isinstance(by_model, dict):
            total = sum(v for v in by_model.values() if isinstance(v, (int, float)))
            tokens_by_date[entry["date"]] = total

    rows = []
    seen_dates = set()
    for entry in daily:
        if not isinstance(entry, dict) or not isinstance(entry.get("date"), str):
            continue
        date = entry["date"]
        if date in known_dates or date in seen_dates:
            continue
        if date_from and date < date_from:
            continue
        if date_to and date > date_to:
            continue
        session_count = entry.get("sessionCount") if isinstance(entry.get("sessionCount"), int) else 0
        message_count = entry.get("messageCount") if isinstance(entry.get("messageCount"), int) else 0
        tool_call_count = entry.get("toolCallCount") if isinstance(entry.get("toolCallCount"), int) else 0
        if session_count <= 0 and message_count <= 0 and tool_call_count <= 0:
            continue
        seen_dates.add(date)
        rows.append(
            {
                "source": "claude",
                "date": date,
                "active": 1,
                "session_count": session_count,
                # 0 is a real, known count here (stats-cache always reports a
                # number) -- unlike sum_optional's blank-means-unknown convention,
                # so it must stay 0, not collapse to blank.
                "message_count": message_count,
                "tool_call_count": tool_call_count,
                "tokens_used": tokens_by_date.get(date),
            }
        )
    return rows
