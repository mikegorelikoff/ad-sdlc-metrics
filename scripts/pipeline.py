#!/usr/bin/env python3
"""Regenerate data/codex/ and data/claude/ sessions.csv + daily_activity.csv.

Each tool gets its own pair of output files (same column schema in both) so
Codex and Claude Code reports stay separate rather than interleaved in one
file. `session_share_pct` in adoption_report.py's output still compares
across both when computing each tool's share of total volume. Covers only
dates with direct transcript/thread evidence.
"""

import argparse
import sys
from pathlib import Path

import csv_common
import extract_claude
import extract_codex

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tool", choices=["codex", "claude"], default=None,
                         help="only process this tool's data")
    parser.add_argument("--from", dest="date_from", type=csv_common.iso_date, default=None,
                         help="inclusive lower date bound (YYYY-MM-DD)")
    parser.add_argument("--to", dest="date_to", type=csv_common.iso_date, default=None,
                         help="inclusive upper date bound (YYYY-MM-DD)")
    parser.add_argument("--repo", dest="repo", default=None,
                         help="only include sessions whose project_path contains this substring")
    args = parser.parse_args()
    if args.date_from and args.date_to and args.date_from > args.date_to:
        parser.error(f"--from {args.date_from} is after --to {args.date_to}")
    return args


def main() -> None:
    args = parse_args()

    sessions = []
    if args.tool in (None, "codex"):
        sessions.extend(extract_codex.get_sessions(args.date_from, args.date_to, repo=args.repo))
    if args.tool in (None, "claude"):
        sessions.extend(extract_claude.get_sessions(args.date_from, args.date_to, repo=args.repo))

    sessions.sort(key=lambda s: (s["source"], s["date"], s["session_id"] or ""))

    # sessions.csv (written below) keeps every row, human and subagent alike.
    # daily_activity.csv -- and therefore everything downstream in
    # adoption_report.py -- is deliberately human-only, so adoption numbers
    # reflect direct usage rather than autonomous subagent work.
    human_sessions = []
    for s in sessions:
        kind = s.get("session_kind")
        if kind not in ("human", "subagent"):
            print(f"warning: session {s.get('session_id')!r} has unrecognized "
                  f"session_kind {kind!r}, excluding from daily_activity.csv", file=sys.stderr)
            continue
        if kind == "human":
            human_sessions.append(s)
    daily = csv_common.aggregate_daily(human_sessions)

    # Fill in Claude dates covered only by stats-cache.json (no surviving raw
    # transcript) -- skipped when --repo is set, since stats-cache.json has no
    # per-project attribution to filter by.
    if args.tool in (None, "claude") and not args.repo:
        known_claude_dates = {d["date"] for d in daily if d["source"] == "claude"}
        gap_rows = extract_claude.get_stats_cache_gap_days(known_claude_dates, args.date_from, args.date_to)
        daily.extend(gap_rows)
    elif args.repo and args.tool in (None, "claude"):
        print("note: --repo set, skipping stats-cache.json gap-fill "
              "(it has no per-project attribution to filter by)", file=sys.stderr)
    daily.sort(key=lambda d: (d["date"], d["source"]))

    for tool in ("codex", "claude"):
        if args.tool not in (None, tool):
            continue
        tool_sessions = [s for s in sessions if s["source"] == tool]
        tool_daily = [d for d in daily if d["source"] == tool]
        tool_dir = DATA_DIR / tool
        csv_common.atomic_write_csv(tool_dir / "sessions.csv", csv_common.SESSION_FIELDS, tool_sessions)
        csv_common.atomic_write_csv(tool_dir / "daily_activity.csv", csv_common.DAILY_FIELDS, tool_daily)
        print(f"{tool}/sessions.csv: {len(tool_sessions)} rows")
        print(f"{tool}/daily_activity.csv: {len(tool_daily)} rows")


if __name__ == "__main__":
    main()
