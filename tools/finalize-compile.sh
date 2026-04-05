#!/bin/bash
set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <raw_file_path> [key_insight]"
    exit 1
fi

RAW_FILE="$1"
INSIGHT="$2"

echo "[1/3] Marking file as compiled..."
./tools/scan.sh --mark "$RAW_FILE"

echo "[2/3] Building wiki indexes..."
python3 ./tools/build-index.py

if [ -n "$INSIGHT" ]; then
    echo "[3/3] Appending key insight to _brief.md..."
    perl -i -pe "s|<!-- BUILD_INDEX:INSIGHTS_END -->|- $INSIGHT\n<!-- BUILD_INDEX:INSIGHTS_END -->|" wiki/_brief.md
else
    echo "[3/3] No key insight provided. Skipping."
fi

echo "✅ Compile pipeline finished successfully."
