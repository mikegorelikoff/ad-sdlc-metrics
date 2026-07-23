import sys

import pytest

import pipeline
from conftest import insert_thread, write_transcript


def run_pipeline(monkeypatch, tmp_path, data_dir, args=None):
    monkeypatch.setattr(pipeline, "DATA_DIR", data_dir)
    monkeypatch.setattr(sys, "argv", ["pipeline.py"] + (args or []))
    pipeline.main()


def test_pipeline_writes_per_tool_files(codex_home, claude_home, tmp_path, monkeypatch, capsys):
    insert_thread(codex_home / "state_5.sqlite", id="t1", created_at=1751328000, source="cli")
    write_transcript(claude_home / "projects" / "p" / "a.jsonl", [
        {"type": "user", "timestamp": "2026-07-01T10:00:00.000Z",
         "message": {"role": "user", "content": []}},
    ])

    data_dir = tmp_path / "data"
    run_pipeline(monkeypatch, tmp_path, data_dir)

    assert (data_dir / "codex" / "sessions.csv").exists()
    assert (data_dir / "codex" / "daily_activity.csv").exists()
    assert (data_dir / "claude" / "sessions.csv").exists()
    assert (data_dir / "claude" / "daily_activity.csv").exists()


def test_pipeline_excludes_subagents_from_daily_activity(codex_home, claude_home, tmp_path, monkeypatch):
    import json
    spawn_blob = json.dumps({"subagent": {"thread_spawn": {"parent_thread_id": "human-1"}}})
    insert_thread(codex_home / "state_5.sqlite", id="human-1", created_at=1751328000, source="cli")
    insert_thread(codex_home / "state_5.sqlite", id="sub-1", created_at=1751328000, source=spawn_blob)

    data_dir = tmp_path / "data"
    run_pipeline(monkeypatch, tmp_path, data_dir)

    sessions_csv = (data_dir / "codex" / "sessions.csv").read_text()
    assert "human-1" in sessions_csv
    assert "sub-1" in sessions_csv  # sessions.csv keeps both kinds

    daily_csv = (data_dir / "codex" / "daily_activity.csv").read_text()
    lines = daily_csv.splitlines()
    assert len(lines) == 2  # header + one day
    assert ",1," in lines[1] or lines[1].split(",")[3] == "1"  # session_count == 1 (human only)


def test_pipeline_tool_filter_only_writes_that_tool(codex_home, claude_home, tmp_path, monkeypatch):
    insert_thread(codex_home / "state_5.sqlite", id="t1", created_at=1751328000)
    data_dir = tmp_path / "data"
    run_pipeline(monkeypatch, tmp_path, data_dir, args=["--tool", "codex"])

    assert (data_dir / "codex" / "sessions.csv").exists()
    assert not (data_dir / "claude").exists()


def test_pipeline_idempotent_on_unchanged_data(codex_home, claude_home, tmp_path, monkeypatch):
    insert_thread(codex_home / "state_5.sqlite", id="t1", created_at=1751328000)
    data_dir = tmp_path / "data"

    run_pipeline(monkeypatch, tmp_path, data_dir)
    first = (data_dir / "codex" / "sessions.csv").read_bytes()
    run_pipeline(monkeypatch, tmp_path, data_dir)
    second = (data_dir / "codex" / "sessions.csv").read_bytes()

    assert first == second


def test_pipeline_reversed_date_range_errors(codex_home, claude_home, tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    with pytest.raises(SystemExit):
        run_pipeline(monkeypatch, tmp_path, data_dir,
                     args=["--from", "2026-08-01", "--to", "2026-01-01"])


def test_pipeline_repo_filter_skips_gap_fill(codex_home, claude_home, tmp_path, monkeypatch, capsys):
    import json
    (claude_home / "stats-cache.json").write_text(json.dumps({
        "dailyActivity": [{"date": "2026-06-10", "sessionCount": 1, "messageCount": 1, "toolCallCount": 0}],
    }))
    data_dir = tmp_path / "data"
    run_pipeline(monkeypatch, tmp_path, data_dir, args=["--repo", "nonexistent"])
    captured = capsys.readouterr()
    assert "skipping stats-cache.json gap-fill" in captured.err
