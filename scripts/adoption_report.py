#!/usr/bin/env python3
"""Roll up data/<tool>/daily_activity.csv into per-tool weekly/monthly reports.

Per the DX AI Measurement Framework's utilization dimension: active-day rate,
volume, and Codex-vs-Claude session share, per week and per month. Reads only
the CSVs produced by pipeline.py -- never touches ~/.codex or ~/.claude.
`session_share_pct` is computed across both tools' combined volume even
though each tool's rollup is written to its own file.
"""

import calendar
import csv
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import csv_common

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"

ROLLUP_FIELDS = (
    "source",
    "period_start",
    "active_days",
    "days_in_period",
    "active_day_rate",
    "session_count",
    "message_count",
    "tool_call_count",
    "tokens_used",
    "session_share_pct",
)


def _to_int(value: str) -> Optional[int]:
    if value is None or value == "":
        return None
    return int(value)


def _require_csv(path: Path) -> None:
    # sessions.csv's content isn't read here -- its presence is just the signal
    # that pipeline.py has been run at least once before this script.
    if not path.exists():
        print(f"error: required input file not found: {path}", file=sys.stderr)
        sys.exit(1)


def _load_daily_activity(path: Path, seen: set) -> list:
    rows = []
    with path.open("r", encoding="utf-8", newline="") as f:
        for lineno, row in enumerate(csv.DictReader(f), start=2):
            try:
                key = (row["source"], row["date"])
                parsed = {
                    "source": row["source"],
                    "date": date.fromisoformat(row["date"]),
                    "session_count": _to_int(row["session_count"]) or 0,
                    "message_count": _to_int(row["message_count"]),
                    "tool_call_count": _to_int(row["tool_call_count"]),
                    "tokens_used": _to_int(row["tokens_used"]),
                }
            except (KeyError, ValueError) as exc:
                print(f"warning: skipping malformed row {lineno} in {path}: {exc}", file=sys.stderr)
                continue
            if key in seen:
                print(f"warning: skipping duplicate row {lineno} in {path} for {key}", file=sys.stderr)
                continue
            seen.add(key)
            rows.append(parsed)
    return rows


def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _month_start(d: date) -> date:
    return d.replace(day=1)


def _days_in_week(_period_start: date) -> int:
    return 7


def _days_in_month(period_start: date) -> int:
    return calendar.monthrange(period_start.year, period_start.month)[1]


def _rollup(rows: list, period_of, days_in_period_of) -> list:
    buckets: dict = {}
    for r in rows:
        key = (r["source"], period_of(r["date"]))
        buckets.setdefault(key, []).append(r)

    period_totals: dict = {}
    for (source, period_start), group in buckets.items():
        period_totals[period_start] = period_totals.get(period_start, 0) + sum(
            g["session_count"] for g in group
        )

    result = []
    for (source, period_start), group in sorted(buckets.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        days_in_period = days_in_period_of(period_start)
        active_days = min(len(group), days_in_period)
        session_count = sum(g["session_count"] for g in group)
        total_session_count = period_totals[period_start]
        share = round((session_count / total_session_count) * 100, 1) if total_session_count else 0.0
        result.append(
            {
                "source": source,
                "period_start": period_start.isoformat(),
                "active_days": active_days,
                "days_in_period": days_in_period,
                "active_day_rate": round(active_days / days_in_period, 2),
                "session_count": session_count,
                "message_count": csv_common.sum_optional(g["message_count"] for g in group),
                "tool_call_count": csv_common.sum_optional(g["tool_call_count"] for g in group),
                "tokens_used": csv_common.sum_optional(g["tokens_used"] for g in group),
                "session_share_pct": share,
            }
        )
    return result


def main() -> None:
    tools = [t for t in ("codex", "claude") if (DATA_DIR / t / "sessions.csv").exists()]
    if not tools:
        print(f"error: no data/<tool>/sessions.csv found under {DATA_DIR} -- run pipeline.py first",
              file=sys.stderr)
        sys.exit(1)

    rows = []
    seen: set = set()
    for tool in tools:
        _require_csv(DATA_DIR / tool / "sessions.csv")
        daily_path = DATA_DIR / tool / "daily_activity.csv"
        _require_csv(daily_path)
        rows.extend(_load_daily_activity(daily_path, seen))

    # session_share_pct is computed across both tools' combined volume even
    # though each tool's rollup is written to its own file below.
    weekly = _rollup(rows, _week_start, _days_in_week)
    monthly = _rollup(rows, _month_start, _days_in_month)

    for tool in tools:
        tool_weekly = [r for r in weekly if r["source"] == tool]
        tool_monthly = [r for r in monthly if r["source"] == tool]
        tool_dir = DATA_DIR / tool
        csv_common.atomic_write_csv(tool_dir / "adoption_weekly.csv", ROLLUP_FIELDS, tool_weekly)
        csv_common.atomic_write_csv(tool_dir / "adoption_monthly.csv", ROLLUP_FIELDS, tool_monthly)
        print(f"{tool}/adoption_weekly.csv: {len(tool_weekly)} rows")
        print(f"{tool}/adoption_monthly.csv: {len(tool_monthly)} rows")


if __name__ == "__main__":
    main()
