#!/usr/bin/env bash
# One-command bootstrap: downloads the scripts into a temp dir and runs them.
# Nothing is cloned or installed; only ~/.codex and ~/.claude are read.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/OWNER/REPO/main/scripts/remote-run.sh | bash
#   curl -fsSL .../remote-run.sh | bash -s -- --tool codex --from 2026-07-01
set -euo pipefail

RAW_BASE="https://raw.githubusercontent.com/OWNER/REPO/main/scripts"
TMP_DIR="$(mktemp -d -t ai-metrics)"
cd "$TMP_DIR"

for f in csv_common.py extract_codex.py extract_claude.py inventory.py pipeline.py adoption_report.py run.sh; do
  curl -fsSL "$RAW_BASE/$f" -o "$f"
done
chmod +x run.sh

./run.sh "$@"

echo
echo "This ran from a temp dir: $TMP_DIR"
echo "Remove it with: rm -rf $TMP_DIR"
