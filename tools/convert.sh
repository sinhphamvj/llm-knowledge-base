#!/usr/bin/env bash
# convert.sh — Wrapper for convert-docs.py
#
# Usage:
#   ./tools/convert.sh                        # scan entire raw/ for pdf/docx/pptx/xlsx and convert
#   ./tools/convert.sh raw/papers/foo.pdf     # convert a specific file
#   ./tools/convert.sh --dry-run              # preview, do not convert
#   ./tools/convert.sh --keep                 # keep original file, do not move to archived
#

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV_PYTHON="$ROOT/tools/.venv/bin/python3"
SCRIPT="$ROOT/tools/convert-docs.py"

if [[ ! -f "$VENV_PYTHON" ]]; then
  echo "❌ Error: Virtual environment not found at tools/.venv"
  echo "   Please run: python3 -m venv tools/.venv && source tools/.venv/bin/activate && pip install pymupdf4llm markitdown"
  exit 1
fi

if [[ $# -eq 0 ]]; then
  echo "=== SCANNING AND CONVERTING ALL FILES ==="
  "$VENV_PYTHON" "$SCRIPT" --scan
  exit $?
fi

# Forward all arguments to the Python script
if [[ "$1" == "--dry-run" || "$1" == "--keep" || "$1" == "--scan" ]]; then
  "$VENV_PYTHON" "$SCRIPT" --scan "$@"
else
  # If specific file, ensure it's an absolute or valid path
  TARGET="$1"
  if [[ ! -f "$TARGET" ]]; then
    # Try prepending ROOT if it's a relative path from project root
    TARGET="$ROOT/$1"
    if [[ ! -f "$TARGET" ]]; then
      echo "❌ File not found: $1"
      exit 1
    fi
  fi
  shift
  "$VENV_PYTHON" "$SCRIPT" "$TARGET" "$@"
fi
