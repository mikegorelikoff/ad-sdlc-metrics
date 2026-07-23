"""Shared schema and atomic CSV writing for the Codex/Claude adoption-metrics pipeline."""

import argparse
import csv
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

SESSION_FIELDS = (
    "source",
    "session_id",
    "date",
    "project_path",
    "model",
    "message_count",
    "tool_call_count",
    "tokens_used",
    "session_kind",
    "parent_session_id",
)

DAILY_FIELDS = (
    "source",
    "date",
    "active",
    "session_count",
    "message_count",
    "tool_call_count",
    "tokens_used",
)


def iso_date(value: str) -> str:
    """argparse `type=` validator for a YYYY-MM-DD date string."""
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid date {value!r}, expected YYYY-MM-DD") from exc
    return value


def epoch_bounds(date_from: Optional[str], date_to: Optional[str]) -> tuple:
    """Convert inclusive YYYY-MM-DD bounds to (from_epoch, to_epoch) UTC seconds, either None if unset."""
    from_epoch = None
    to_epoch = None
    if date_from:
        from_epoch = int(datetime.strptime(date_from, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())
    if date_to:
        to_epoch = int(datetime.strptime(date_to, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()) + 86399
    return (from_epoch, to_epoch)


def atomic_write_csv(path: Path, fieldnames: Iterable[str], rows: Iterable[dict]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(f"{path.suffix}.{os.getpid()}.tmp")
    with tmp_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(fieldnames), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    os.replace(tmp_path, path)


def sum_optional(values: Iterable[Optional[float]]) -> Optional[float]:
    """Sum only the non-None values; return None if every value is None."""
    known = [v for v in values if v is not None]
    if not known:
        return None
    return sum(known)


def aggregate_daily(sessions: Iterable[dict]) -> list:
    """Group normalized session rows into one daily_activity row per (source, date)."""
    buckets: dict = {}
    for s in sessions:
        key = (s["source"], s["date"])
        buckets.setdefault(key, []).append(s)

    rows = []
    for (source, date), group in sorted(buckets.items()):
        rows.append(
            {
                "source": source,
                "date": date,
                "active": 1,
                "session_count": len(group),
                "message_count": sum_optional(g.get("message_count") for g in group),
                "tool_call_count": sum_optional(g.get("tool_call_count") for g in group),
                "tokens_used": sum_optional(g.get("tokens_used") for g in group),
            }
        )
    return rows
