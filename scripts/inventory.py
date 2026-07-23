#!/usr/bin/env python3
"""Read-only inventory of Codex CLI (~/.codex) and Claude Code (~/.claude) local data.

For each known data source, reports its location, format, record count, and the
actual min/max date found by reading the data itself (not file mtimes).
"""

import argparse
import json
import os
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import csv_common

CODEX_HOME = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")
CLAUDE_HOME = Path(os.environ.get("CLAUDE_HOME") or Path.home() / ".claude")


@dataclass
class SourceReport:
    label: str
    path: str
    fmt: str
    count: Optional[int] = None
    min_date: Optional[str] = None
    max_date: Optional[str] = None
    note: str = ""
    status: str = "ok"  # ok | missing | unreadable


def _fmt_epoch(ts, is_ms: bool = False) -> Optional[str]:
    """Format an epoch timestamp as YYYY-MM-DD, or None if ts isn't a valid epoch value."""
    if not isinstance(ts, (int, float)) or isinstance(ts, bool):
        return None
    if is_ms:
        ts = ts / 1000
    try:
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
    except (OverflowError, OSError, ValueError):
        return None


def _in_range(date_str: str, date_from: Optional[str], date_to: Optional[str]) -> bool:
    if date_from and date_str < date_from:
        return False
    if date_to and date_str > date_to:
        return False
    return True


def scan_jsonl_field(
    path: Path,
    epoch_field: str,
    is_ms: bool = False,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> SourceReport:
    """Scan a flat jsonl file for a top-level epoch timestamp field per line."""
    label = path.name
    report = SourceReport(label=label, path=str(path), fmt="jsonl")
    if not path.exists():
        report.status = "missing"
        return report

    count = 0
    min_date: Optional[str] = None
    max_date: Optional[str] = None
    bad_lines = 0
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            for lineno, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    ts = record[epoch_field]
                    date = _fmt_epoch(ts, is_ms=is_ms)
                except (json.JSONDecodeError, KeyError, TypeError):
                    date = None
                if date is None:
                    bad_lines += 1
                    print(f"warning: skipping malformed line {lineno} in {path}", file=sys.stderr)
                    continue
                if not _in_range(date, date_from, date_to):
                    continue
                count += 1
                if min_date is None or date < min_date:
                    min_date = date
                if max_date is None or date > max_date:
                    max_date = date
    except (OSError, UnicodeDecodeError):
        report.status = "unreadable"
        return report

    report.count = count
    report.min_date = min_date if min_date else "n/a"
    report.max_date = max_date if max_date else "n/a"
    if bad_lines:
        report.note = f"{bad_lines} malformed line(s) skipped"
    return report


def scan_transcript_dir(
    root: Path,
    label: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    repo: Optional[str] = None,
) -> SourceReport:
    """Scan a directory of per-session transcript *.jsonl files.

    Count = number of transcript files (sessions) whose own date (its earliest
    line timestamp) falls within [date_from, date_to] and whose "cwd" contains
    `repo` (case-insensitive substring), if given. Min/max date comes from each
    line's top-level ISO "timestamp" field, scanned across included files.
    """
    report = SourceReport(label=label, path=str(root), fmt="jsonl (per-session files)")
    if not root.exists():
        report.status = "missing"
        return report
    if not root.is_dir():
        report.status = "unreadable"
        return report

    try:
        files = sorted(root.rglob("*.jsonl"))
    except OSError:
        report.status = "unreadable"
        return report
    min_date: Optional[str] = None
    max_date: Optional[str] = None
    bad_files = 0
    included = 0

    for fpath in files:
        file_min: Optional[str] = None
        file_max: Optional[str] = None
        file_cwd: Optional[str] = None
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
                    if not file_cwd:
                        cwd = record.get("cwd")
                        if isinstance(cwd, str) and cwd:
                            file_cwd = cwd
                        else:
                            payload = record.get("payload")
                            if isinstance(payload, dict) and isinstance(payload.get("cwd"), str) and payload["cwd"]:
                                file_cwd = payload["cwd"]
                    ts = record.get("timestamp")
                    if not isinstance(ts, str) or len(ts) < 10:
                        continue
                    date = ts[:10]
                    if file_min is None or date < file_min:
                        file_min = date
                    if file_max is None or date > file_max:
                        file_max = date
        except (OSError, UnicodeDecodeError):
            bad_files += 1
            print(f"warning: could not read {fpath}", file=sys.stderr)
            continue

        if file_min is None:
            continue
        if not _in_range(file_min, date_from, date_to):
            continue
        if repo and (not file_cwd or repo.lower() not in file_cwd.lower()):
            continue

        included += 1
        if min_date is None or file_min < min_date:
            min_date = file_min
        if max_date is None or file_max > max_date:
            max_date = file_max

    report.count = included
    report.min_date = min_date if min_date else "n/a"
    report.max_date = max_date if max_date else "n/a"
    if bad_files:
        report.note = f"{bad_files} file(s) unreadable, skipped"
    return report


def scan_codex_threads(
    db_path: Path,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    repo: Optional[str] = None,
) -> SourceReport:
    report = SourceReport(label="threads table", path=str(db_path), fmt="sqlite")
    if not db_path.exists():
        report.status = "missing"
        return report

    from_epoch, to_epoch = csv_common.epoch_bounds(date_from, date_to)
    where = []
    params: list = []
    if from_epoch is not None:
        where.append("created_at >= ?")
        params.append(from_epoch)
    if to_epoch is not None:
        where.append("created_at <= ?")
        params.append(to_epoch)
    if repo:
        where.append("cwd LIKE ? ESCAPE '\\'")
        escaped = repo.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        params.append(f"%{escaped}%")
    where_clause = f"WHERE {' AND '.join(where)}" if where else ""

    try:
        uri = f"file:{db_path}?mode=ro"
        con = sqlite3.connect(uri, uri=True)
        try:
            cur = con.execute(
                f"SELECT COUNT(*), MIN(created_at), MAX(updated_at) FROM threads {where_clause}",
                params,
            )
            count, min_ts, max_ts = cur.fetchone()
        finally:
            con.close()
    except sqlite3.Error:
        report.status = "unreadable"
        return report

    report.count = count or 0
    report.min_date = _fmt_epoch(min_ts) or "n/a"
    report.max_date = _fmt_epoch(max_ts) or "n/a"
    return report


def scan_claude_stats_cache(
    path: Path,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> SourceReport:
    report = SourceReport(label="stats-cache.json", path=str(path), fmt="json")
    if not path.exists():
        report.status = "missing"
        return report

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        report.status = "unreadable"
        return report

    if not isinstance(data, dict):
        report.status = "unreadable"
        return report

    daily = data.get("dailyActivity", [])
    if not isinstance(daily, list):
        daily = []
    dates = {
        entry["date"]
        for entry in daily
        if isinstance(entry, dict) and isinstance(entry.get("date"), str)
    }
    dates = {d for d in dates if _in_range(d, date_from, date_to)}
    report.count = len(dates)
    report.min_date = min(dates) if dates else "n/a"
    report.max_date = max(dates) if dates else "n/a"
    return report


def print_report(report: SourceReport) -> None:
    print(f"[{report.label}]")
    print(f"  path:   {report.path}")
    if report.status == "missing":
        print("  status: not found")
    elif report.status == "unreadable":
        print("  status: unreadable")
    else:
        print(f"  format: {report.fmt}")
        print(f"  count:  {report.count}")
        print(f"  range:  {report.min_date} -> {report.max_date}")
        if report.note:
            print(f"  note:   {report.note}")
    print()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tool", choices=["codex", "claude"], default=None,
                         help="only report this tool's sources")
    parser.add_argument("--from", dest="date_from", type=csv_common.iso_date, default=None,
                         help="inclusive lower date bound (YYYY-MM-DD)")
    parser.add_argument("--to", dest="date_to", type=csv_common.iso_date, default=None,
                         help="inclusive upper date bound (YYYY-MM-DD)")
    parser.add_argument("--repo", dest="repo", default=None,
                         help="only count sessions whose cwd contains this substring "
                              "(project-scoped sources only; history.jsonl/stats-cache.json unaffected)")
    parser.add_argument("--redact-paths", dest="redact_paths", action="store_true",
                         help="accepted for compatibility with run.sh's flag forwarding to "
                              "pipeline.py -- inventory.py never prints project paths, so this "
                              "is a no-op here")
    args = parser.parse_args()
    if args.date_from and args.date_to and args.date_from > args.date_to:
        parser.error(f"--from {args.date_from} is after --to {args.date_to}")
    return args


def main() -> None:
    args = parse_args()
    date_from, date_to, repo = args.date_from, args.date_to, args.repo

    codex_sources = [
        scan_jsonl_field(CODEX_HOME / "history.jsonl", epoch_field="ts", is_ms=False,
                          date_from=date_from, date_to=date_to),
        scan_transcript_dir(CODEX_HOME / "sessions", label="sessions/*.jsonl",
                             date_from=date_from, date_to=date_to, repo=repo),
        scan_codex_threads(CODEX_HOME / "state_5.sqlite", date_from=date_from, date_to=date_to, repo=repo),
    ]
    claude_sources = [
        scan_jsonl_field(CLAUDE_HOME / "history.jsonl", epoch_field="timestamp", is_ms=True,
                          date_from=date_from, date_to=date_to),
        scan_transcript_dir(CLAUDE_HOME / "projects", label="projects/**/*.jsonl",
                             date_from=date_from, date_to=date_to, repo=repo),
        scan_claude_stats_cache(CLAUDE_HOME / "stats-cache.json", date_from=date_from, date_to=date_to),
    ]

    printed = []
    if args.tool in (None, "codex"):
        print("=== Codex (~/.codex) ===\n")
        for report in codex_sources:
            print_report(report)
            printed.append(report)

    if args.tool in (None, "claude"):
        print("=== Claude Code (~/.claude) ===\n")
        for report in claude_sources:
            print_report(report)
            printed.append(report)

    # "missing" is often legitimate (e.g. this machine only uses one of the two
    # tools) -- only "unreadable" (a source that exists but genuinely failed to
    # parse/open) is treated as an error worth a non-zero exit.
    if any(r.status == "unreadable" for r in printed):
        sys.exit(1)


if __name__ == "__main__":
    main()
