import extract_claude
from conftest import write_transcript


def test_get_sessions_empty_when_no_projects_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(extract_claude, "CLAUDE_HOME", tmp_path / "nonexistent")
    assert extract_claude.get_sessions() == []


def test_get_sessions_parses_human_transcript(claude_home):
    f = claude_home / "projects" / "-Users-x-proj" / "abc123.jsonl"
    write_transcript(f, [
        {"type": "user", "timestamp": "2026-07-01T10:00:00.000Z", "cwd": "/Users/x/proj",
         "message": {"role": "user", "content": [{"type": "text", "text": "hi"}]}},
        {"type": "assistant", "timestamp": "2026-07-01T10:01:00.000Z",
         "message": {"role": "assistant", "model": "claude-x",
                     "content": [{"type": "text", "text": "hi"},
                                 {"type": "tool_use", "name": "x"}],
                     "usage": {"input_tokens": 10, "output_tokens": 20}}},
    ])

    sessions = extract_claude.get_sessions()
    assert len(sessions) == 1
    s = sessions[0]
    assert s["session_id"] == "abc123"
    assert s["date"] == "2026-07-01"
    assert s["project_path"] == "/Users/x/proj"
    assert s["model"] == "claude-x"
    assert s["message_count"] == 2
    assert s["tool_call_count"] == 1
    assert s["tokens_used"] == 30
    assert s["session_kind"] == "human"
    assert s["parent_session_id"] is None


def test_get_sessions_classifies_subagent_transcript(claude_home):
    parent_dir = claude_home / "projects" / "-Users-x-proj" / "parent-uuid"
    f = parent_dir / "subagents" / "agent-xyz.jsonl"
    write_transcript(f, [
        {"type": "user", "timestamp": "2026-07-01T10:00:00.000Z",
         "message": {"role": "user", "content": [{"type": "text", "text": "hi"}]}},
    ])

    sessions = extract_claude.get_sessions()
    assert sessions[0]["session_kind"] == "subagent"
    assert sessions[0]["parent_session_id"] == "parent-uuid"


def test_get_sessions_ignores_dir_named_similarly_to_subagents(claude_home):
    # "my-subagents-tool" is a path segment but not exactly "subagents" -- must
    # not false-positive as a subagent transcript.
    f = claude_home / "projects" / "my-subagents-tool" / "abc.jsonl"
    write_transcript(f, [
        {"type": "user", "timestamp": "2026-07-01T10:00:00.000Z",
         "message": {"role": "user", "content": [{"type": "text", "text": "hi"}]}},
    ])
    sessions = extract_claude.get_sessions()
    assert sessions[0]["session_kind"] == "human"


def test_get_sessions_skips_malformed_lines(claude_home):
    f = claude_home / "projects" / "-Users-x-proj" / "abc.jsonl"
    f.parent.mkdir(parents=True)
    f.write_text(
        "not json at all\n"
        '{"type": "user", "timestamp": "2026-07-01T10:00:00.000Z", '
        '"message": {"role": "user", "content": []}}\n'
    )
    sessions = extract_claude.get_sessions()
    assert len(sessions) == 1
    assert sessions[0]["message_count"] == 1


def test_get_sessions_empty_transcript_yields_no_session(claude_home):
    f = claude_home / "projects" / "-Users-x-proj" / "abc.jsonl"
    write_transcript(f, [])
    assert extract_claude.get_sessions() == []


def test_get_sessions_filters_by_repo(claude_home):
    write_transcript(claude_home / "projects" / "p1" / "a.jsonl", [
        {"type": "user", "timestamp": "2026-07-01T10:00:00.000Z", "cwd": "/Users/x/my-project",
         "message": {"role": "user", "content": []}},
    ])
    write_transcript(claude_home / "projects" / "p2" / "b.jsonl", [
        {"type": "user", "timestamp": "2026-07-01T10:00:00.000Z", "cwd": "/Users/x/other",
         "message": {"role": "user", "content": []}},
    ])
    sessions = extract_claude.get_sessions(repo="my-project")
    assert [s["session_id"] for s in sessions] == ["a"]


def test_get_stats_cache_gap_days_fills_unknown_dates(claude_home):
    import json
    (claude_home / "stats-cache.json").write_text(json.dumps({
        "dailyActivity": [
            {"date": "2026-06-10", "sessionCount": 3, "messageCount": 100, "toolCallCount": 20},
            {"date": "2026-06-11", "sessionCount": 0, "messageCount": 50, "toolCallCount": 5},
            {"date": "2026-06-12", "sessionCount": 0, "messageCount": 0, "toolCallCount": 0},
        ],
        "dailyModelTokens": [
            {"date": "2026-06-10", "tokensByModel": {"claude-x": 1000}},
        ],
    }))

    rows = extract_claude.get_stats_cache_gap_days(known_dates=set())
    by_date = {r["date"]: r for r in rows}
    assert "2026-06-12" not in by_date  # zero everything -> not included
    assert by_date["2026-06-10"]["tokens_used"] == 1000
    # session_count 0 but real message/tool activity -- must stay 0, not blank
    assert by_date["2026-06-11"]["session_count"] == 0
    assert by_date["2026-06-11"]["message_count"] == 50


def test_get_stats_cache_gap_days_skips_known_dates(claude_home):
    import json
    (claude_home / "stats-cache.json").write_text(json.dumps({
        "dailyActivity": [{"date": "2026-06-10", "sessionCount": 3, "messageCount": 10, "toolCallCount": 1}],
    }))
    rows = extract_claude.get_stats_cache_gap_days(known_dates={"2026-06-10"})
    assert rows == []


def test_get_stats_cache_gap_days_missing_file_returns_empty(claude_home):
    assert extract_claude.get_stats_cache_gap_days(known_dates=set()) == []
