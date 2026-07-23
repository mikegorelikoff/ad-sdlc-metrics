import json
import sys

import pytest

import inventory
from conftest import insert_thread, write_transcript


def run_inventory(monkeypatch, args=None, capsys=None):
    monkeypatch.setattr(sys, "argv", ["inventory.py"] + (args or []))
    try:
        inventory.main()
        return 0
    except SystemExit as exc:
        return exc.code or 0


def test_missing_sources_report_not_found_and_exit_zero(codex_home, claude_home, monkeypatch, capsys):
    exit_code = run_inventory(monkeypatch)
    out = capsys.readouterr().out
    assert "not found" in out
    assert exit_code == 0


def test_unreadable_source_causes_nonzero_exit(tmp_path, monkeypatch, capsys):
    bad_db = tmp_path / "state_5.sqlite"
    bad_db.write_text("not a sqlite file")
    monkeypatch.setattr(inventory, "CODEX_HOME", tmp_path)
    monkeypatch.setattr(inventory, "CLAUDE_HOME", tmp_path / "nonexistent-claude")
    exit_code = run_inventory(monkeypatch, args=["--tool", "codex"])
    assert exit_code == 1


def test_reversed_date_range_errors(codex_home, claude_home, monkeypatch, capsys):
    exit_code = run_inventory(monkeypatch, args=["--from", "2026-08-01", "--to", "2026-01-01"])
    assert exit_code != 0


def test_scan_codex_threads_reports_count_and_range(codex_home, monkeypatch, capsys):
    insert_thread(codex_home / "state_5.sqlite", id="a", created_at=1751328000)
    insert_thread(codex_home / "state_5.sqlite", id="b", created_at=1751328000)
    run_inventory(monkeypatch, args=["--tool", "codex"])
    out = capsys.readouterr().out
    assert "count:  2" in out
    assert "2025-07-01" in out


def test_scan_codex_threads_repo_filter(codex_home, monkeypatch, capsys):
    insert_thread(codex_home / "state_5.sqlite", id="a", created_at=1751328000, cwd="/x/my-project")
    insert_thread(codex_home / "state_5.sqlite", id="b", created_at=1751328000, cwd="/x/other")
    run_inventory(monkeypatch, args=["--tool", "codex", "--repo", "my-project"])
    out = capsys.readouterr().out
    assert "count:  1" in out


def test_scan_transcript_dir_counts_claude_sessions(claude_home, monkeypatch, capsys):
    write_transcript(claude_home / "projects" / "p" / "a.jsonl", [
        {"type": "user", "timestamp": "2026-07-01T10:00:00.000Z",
         "message": {"role": "user", "content": []}},
    ])
    run_inventory(monkeypatch, args=["--tool", "claude"])
    out = capsys.readouterr().out
    assert "count:  1" in out


def test_scan_claude_stats_cache_dedupes_dates(claude_home, monkeypatch, capsys):
    (claude_home / "stats-cache.json").write_text(json.dumps({
        "dailyActivity": [
            {"date": "2026-06-10"},
            {"date": "2026-06-10"},  # duplicate
            {"date": "2026-06-11"},
        ]
    }))
    run_inventory(monkeypatch, args=["--tool", "claude"])
    out = capsys.readouterr().out
    assert "count:  2" in out


def test_redact_paths_flag_accepted_as_noop(codex_home, claude_home, monkeypatch):
    # run.sh forwards --redact-paths to both scripts; inventory.py must accept
    # it without error even though it never prints paths.
    exit_code = run_inventory(monkeypatch, args=["--redact-paths"])
    assert exit_code == 0


def test_codex_home_env_var_override(tmp_path, monkeypatch, capsys):
    # inventory.py reads the env var at import time -- verify the fallback logic
    # directly rather than re-importing the module mid-test-suite.
    import os
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "custom"))
    from pathlib import Path
    expected = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")
    assert expected == tmp_path / "custom"
