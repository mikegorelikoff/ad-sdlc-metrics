import json

import extract_codex
from conftest import insert_thread


def _rollout(tmp_path, name, records):
    path = tmp_path / name
    with path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    return str(path)


def test_get_sessions_empty_when_no_db(tmp_path, monkeypatch):
    monkeypatch.setattr(extract_codex, "CODEX_HOME", tmp_path / "nonexistent")
    assert extract_codex.get_sessions() == []


def test_get_sessions_classifies_human_thread(codex_home, tmp_path):
    rollout = _rollout(tmp_path, "r1.jsonl", [
        {"type": "response_item", "payload": {"type": "message", "role": "user"}},
        {"type": "response_item", "payload": {"type": "message", "role": "assistant"}},
        {"type": "response_item", "payload": {"type": "function_call"}},
    ])
    insert_thread(codex_home / "state_5.sqlite", id="t1", created_at=1751328000,
                  source="cli", rollout_path=rollout)

    sessions = extract_codex.get_sessions()
    assert len(sessions) == 1
    s = sessions[0]
    assert s["session_kind"] == "human"
    assert s["parent_session_id"] is None
    assert s["message_count"] == 2
    assert s["tool_call_count"] == 1
    assert s["date"] == "2025-07-01"


def test_get_sessions_classifies_subagent_thread_with_parent(codex_home):
    spawn_blob = json.dumps({"subagent": {"thread_spawn": {"parent_thread_id": "parent-1"}}})
    insert_thread(codex_home / "state_5.sqlite", id="t2", created_at=1751328000,
                  source=spawn_blob)

    sessions = extract_codex.get_sessions()
    assert sessions[0]["session_kind"] == "subagent"
    assert sessions[0]["parent_session_id"] == "parent-1"


def test_get_sessions_malformed_subagent_json_has_no_parent(codex_home):
    insert_thread(codex_home / "state_5.sqlite", id="t3", created_at=1751328000,
                  source="{not valid json")

    sessions = extract_codex.get_sessions()
    # Still JSON-shaped (starts with "{"), so classified as subagent even though
    # unparseable -- but parent_session_id can't be extracted from garbage.
    assert sessions[0]["session_kind"] == "subagent"
    assert sessions[0]["parent_session_id"] is None


def test_get_sessions_filters_by_date_range(codex_home):
    insert_thread(codex_home / "state_5.sqlite", id="old", created_at=1735689600)  # 2025-01-01
    insert_thread(codex_home / "state_5.sqlite", id="new", created_at=1751328000)  # 2025-07-01

    sessions = extract_codex.get_sessions(date_from="2025-06-01")
    assert [s["session_id"] for s in sessions] == ["new"]


def test_get_sessions_filters_by_repo_substring(codex_home):
    insert_thread(codex_home / "state_5.sqlite", id="a", created_at=1751328000, cwd="/Users/x/my-project")
    insert_thread(codex_home / "state_5.sqlite", id="b", created_at=1751328000, cwd="/Users/x/other")

    sessions = extract_codex.get_sessions(repo="my-project")
    assert [s["session_id"] for s in sessions] == ["a"]


def test_get_sessions_missing_rollout_file_yields_blank_counts(codex_home):
    insert_thread(codex_home / "state_5.sqlite", id="t4", created_at=1751328000,
                  rollout_path=str(codex_home / "does-not-exist.jsonl"))

    sessions = extract_codex.get_sessions()
    assert sessions[0]["message_count"] is None
    assert sessions[0]["tool_call_count"] is None


def test_get_sessions_handles_broken_db(tmp_path, monkeypatch):
    bad_db = tmp_path / "state_5.sqlite"
    bad_db.write_text("not a sqlite file")
    monkeypatch.setattr(extract_codex, "CODEX_HOME", tmp_path)
    assert extract_codex.get_sessions() == []
