#!/usr/bin/env bash
# Runs the full pipeline: inventory -> normalize to CSV -> adoption rollups.
# Any flags you pass (--tool/--from/--to/--repo) are forwarded to inventory.py
# and pipeline.py.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

PYTHON=python3
command -v python3.11 >/dev/null 2>&1 && PYTHON=python3.11

"$PYTHON" inventory.py "$@"
"$PYTHON" pipeline.py "$@"
"$PYTHON" adoption_report.py

echo
echo "Done. CSVs are in $(dirname "$(pwd)")/data/codex/ and $(dirname "$(pwd)")/data/claude/"
