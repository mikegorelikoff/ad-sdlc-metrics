import argparse

import pytest

import csv_common


def test_iso_date_accepts_valid_date():
    assert csv_common.iso_date("2026-07-01") == "2026-07-01"


def test_iso_date_rejects_invalid_date():
    with pytest.raises(argparse.ArgumentTypeError):
        csv_common.iso_date("not-a-date")


def test_epoch_bounds_none_when_unset():
    assert csv_common.epoch_bounds(None, None) == (None, None)


def test_epoch_bounds_to_is_end_of_day():
    from_epoch, to_epoch = csv_common.epoch_bounds("2026-07-01", "2026-07-01")
    assert to_epoch - from_epoch == 86399


def test_sum_optional_all_none_returns_none():
    assert csv_common.sum_optional([None, None]) is None


def test_sum_optional_ignores_none_mixed_with_values():
    assert csv_common.sum_optional([1, None, 2]) == 3


def test_sum_optional_empty_iterable_returns_none():
    assert csv_common.sum_optional([]) is None


def test_atomic_write_csv_roundtrip(tmp_path):
    path = tmp_path / "out.csv"
    rows = [{"a": "1", "b": "2"}, {"a": "3", "b": "4"}]
    csv_common.atomic_write_csv(path, ("a", "b"), rows)
    assert path.exists()
    assert path.read_text().splitlines() == ["a,b", "1,2", "3,4"]


def test_atomic_write_csv_ignores_extra_keys(tmp_path):
    path = tmp_path / "out.csv"
    rows = [{"a": "1", "b": "2", "extra": "ignored"}]
    csv_common.atomic_write_csv(path, ("a", "b"), rows)
    assert path.read_text().splitlines() == ["a,b", "1,2"]


def test_atomic_write_csv_no_leftover_tmp_file(tmp_path):
    path = tmp_path / "out.csv"
    csv_common.atomic_write_csv(path, ("a",), [{"a": "1"}])
    leftovers = [p for p in tmp_path.iterdir() if p.name != "out.csv"]
    assert leftovers == []


def test_aggregate_daily_groups_by_source_and_date():
    sessions = [
        {"source": "codex", "date": "2026-07-01", "message_count": 5, "tool_call_count": 1, "tokens_used": 100},
        {"source": "codex", "date": "2026-07-01", "message_count": 3, "tool_call_count": None, "tokens_used": 50},
        {"source": "claude", "date": "2026-07-01", "message_count": 2, "tool_call_count": 1, "tokens_used": 20},
    ]
    rows = csv_common.aggregate_daily(sessions)
    by_source = {r["source"]: r for r in rows}
    assert by_source["codex"]["session_count"] == 2
    assert by_source["codex"]["message_count"] == 8
    assert by_source["codex"]["tool_call_count"] == 1  # None ignored, not treated as 0
    assert by_source["codex"]["tokens_used"] == 150
    assert by_source["codex"]["active"] == 1
    assert by_source["claude"]["session_count"] == 1


def test_aggregate_daily_all_unknown_field_stays_blank():
    sessions = [{"source": "codex", "date": "2026-07-01", "message_count": None,
                 "tool_call_count": None, "tokens_used": None}]
    rows = csv_common.aggregate_daily(sessions)
    assert rows[0]["message_count"] is None


def test_aggregate_daily_empty_input_returns_empty_list():
    assert csv_common.aggregate_daily([]) == []
