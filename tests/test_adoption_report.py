import sys
from datetime import date

import pytest

import adoption_report


def test_week_start_is_monday():
    # 2026-07-01 is a Wednesday
    assert adoption_report._week_start(date(2026, 7, 1)) == date(2026, 6, 29)


def test_month_start():
    assert adoption_report._month_start(date(2026, 7, 15)) == date(2026, 7, 1)


def test_days_in_month():
    assert adoption_report._days_in_month(date(2026, 2, 1)) == 28


def test_rollup_computes_active_day_rate_and_share():
    rows = [
        {"source": "codex", "date": date(2026, 6, 29), "session_count": 3,
         "message_count": 10, "tool_call_count": 2, "tokens_used": 100},
        {"source": "codex", "date": date(2026, 6, 30), "session_count": 1,
         "message_count": None, "tool_call_count": None, "tokens_used": None},
        {"source": "claude", "date": date(2026, 6, 29), "session_count": 1,
         "message_count": 5, "tool_call_count": 1, "tokens_used": 50},
    ]
    weekly = adoption_report._rollup(rows, adoption_report._week_start, adoption_report._days_in_week)
    by_source = {r["source"]: r for r in weekly}

    assert by_source["codex"]["active_days"] == 2
    assert by_source["codex"]["days_in_period"] == 7
    assert by_source["codex"]["active_day_rate"] == round(2 / 7, 2)
    assert by_source["codex"]["session_count"] == 4
    # 4 codex + 1 claude = 5 total that week
    assert by_source["codex"]["session_share_pct"] == 80.0
    assert by_source["claude"]["session_share_pct"] == 20.0


def test_rollup_clamps_active_days_to_days_in_period():
    # Duplicate-looking rows shouldn't push active_days above 7 in a weekly rollup
    rows = [{"source": "codex", "date": date(2026, 6, 29 - i), "session_count": 1,
             "message_count": None, "tool_call_count": None, "tokens_used": None}
            for i in range(10)]
    weekly = adoption_report._rollup(rows, adoption_report._week_start, adoption_report._days_in_week)
    assert all(r["active_day_rate"] <= 1.0 for r in weekly)


def test_load_daily_activity_skips_malformed_and_duplicate_rows(tmp_path):
    path = tmp_path / "daily_activity.csv"
    path.write_text(
        "source,date,active,session_count,message_count,tool_call_count,tokens_used\n"
        "codex,2026-07-01,1,3,10,2,100\n"
        "codex,2026-07-01,1,3,10,2,100\n"  # duplicate (source, date)
        "codex,not-a-date,1,3,10,2,100\n"  # malformed date
    )
    seen = set()
    rows = adoption_report._load_daily_activity(path, seen)
    assert len(rows) == 1


def test_main_errors_when_sessions_csv_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(adoption_report, "DATA_DIR", tmp_path)
    monkeypatch.setattr(sys, "argv", ["adoption_report.py"])
    with pytest.raises(SystemExit):
        adoption_report.main()


def test_main_writes_per_tool_rollups(tmp_path, monkeypatch):
    codex_dir = tmp_path / "codex"
    codex_dir.mkdir()
    (codex_dir / "sessions.csv").write_text("source,session_id\n")
    (codex_dir / "daily_activity.csv").write_text(
        "source,date,active,session_count,message_count,tool_call_count,tokens_used\n"
        "codex,2026-07-01,1,2,10,3,100\n"
    )
    monkeypatch.setattr(adoption_report, "DATA_DIR", tmp_path)
    monkeypatch.setattr(sys, "argv", ["adoption_report.py"])

    adoption_report.main()

    assert (codex_dir / "adoption_weekly.csv").exists()
    assert (codex_dir / "adoption_monthly.csv").exists()
    assert not (tmp_path / "claude").exists()
