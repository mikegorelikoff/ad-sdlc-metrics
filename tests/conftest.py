"""Shared pytest fixtures for testing scripts/*.py.

The scripts under scripts/ are flat sibling modules (no package, no __init__.py) --
this puts scripts/ on sys.path so `import pipeline` etc. works the same way it does
when the scripts are actually run directly.
"""

import sqlite3
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

THREADS_SCHEMA = """
CREATE TABLE threads (
    id TEXT PRIMARY KEY,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    cwd TEXT NOT NULL,
    model TEXT,
    tokens_used INTEGER NOT NULL DEFAULT 0,
    source TEXT NOT NULL,
    rollout_path TEXT NOT NULL
);
"""


@pytest.fixture
def codex_home(tmp_path, monkeypatch):
    """A fake ~/.codex with an empty threads table, ready for rows to be inserted."""
    home = tmp_path / "codex_home"
    home.mkdir()
    db_path = home / "state_5.sqlite"
    con = sqlite3.connect(db_path)
    con.execute(THREADS_SCHEMA)
    con.commit()
    con.close()

    import extract_codex
    import inventory

    monkeypatch.setattr(extract_codex, "CODEX_HOME", home)
    monkeypatch.setattr(inventory, "CODEX_HOME", home)
    return home


def insert_thread(db_path, *, id, created_at, updated_at=None, cwd="/Users/x/proj",
                   model="gpt-5", tokens_used=100, source="cli", rollout_path=None):
    """Insert one row into the fake threads table, writing a matching rollout file
    when rollout_path points somewhere so message/tool-call counting has real data."""
    con = sqlite3.connect(db_path)
    con.execute(
        "INSERT INTO threads (id, created_at, updated_at, cwd, model, tokens_used, source, rollout_path) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (id, created_at, updated_at or created_at, cwd, model, tokens_used, source, rollout_path or ""),
    )
    con.commit()
    con.close()


@pytest.fixture
def claude_home(tmp_path, monkeypatch):
    """A fake ~/.claude with an empty projects/ directory."""
    home = tmp_path / "claude_home"
    (home / "projects").mkdir(parents=True)

    import extract_claude
    import inventory

    monkeypatch.setattr(extract_claude, "CLAUDE_HOME", home)
    monkeypatch.setattr(inventory, "CLAUDE_HOME", home)
    return home


def write_transcript(path, lines):
    """Write a list of dicts as a jsonl transcript file, creating parent dirs."""
    import json
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for line in lines:
            f.write(json.dumps(line) + "\n")


def user_msg(ts, cwd=None, model=None, tool_use=False):
    content = [{"type": "tool_use", "name": "x"}] if tool_use else [{"type": "text", "text": "hi"}]
    rec = {"type": "user", "timestamp": ts, "message": {"role": "user", "content": [{"type": "text", "text": "hi"}]}}
    if cwd:
        rec["cwd"] = cwd
    return rec


def assistant_msg(ts, model="claude-x", tool_use=False, usage=None):
    content = [{"type": "text", "text": "hi"}]
    if tool_use:
        content.append({"type": "tool_use", "name": "x"})
    msg = {"role": "assistant", "model": model, "content": content}
    if usage:
        msg["usage"] = usage
    return {"type": "assistant", "timestamp": ts, "message": msg}
