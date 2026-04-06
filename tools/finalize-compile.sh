#!/bin/bash
set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <raw_file_path> [key_insight] [--model model_name]"
    exit 1
fi

RAW_FILE="$1"
INSIGHT=""
MODEL_FLAG=""

shift
while [ $# -gt 0 ]; do
    case "$1" in
        --model) MODEL_FLAG="$2"; shift 2 ;;
        *) [ -z "$INSIGHT" ] && INSIGHT="$1"; shift ;;
    esac
done

MARK_ARGS="--mark \"$RAW_FILE\""
[ -n "$MODEL_FLAG" ] && MARK_ARGS="$MARK_ARGS --model $MODEL_FLAG"

echo "[1/3] Marking file as compiled..."
eval ./tools/scan.sh $MARK_ARGS

echo "[2/3] Building wiki indexes..."
python3 ./tools/build-index.py

if [ -n "$INSIGHT" ]; then
    echo "[3/3] Appending key insight to _brief.md..."
    perl -i -pe "s|<!-- BUILD_INDEX:INSIGHTS_END -->|- $INSIGHT\n<!-- BUILD_INDEX:INSIGHTS_END -->|" wiki/_brief.md
else
    echo "[3/3] No key insight provided. Skipping."
fi

echo "✅ Compile pipeline finished successfully."
