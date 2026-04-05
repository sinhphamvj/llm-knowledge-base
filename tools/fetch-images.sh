#!/usr/bin/env bash
# fetch-images.sh — Download external images from a markdown file to raw/images/
# and rewrite URLs in the file to local paths so Claude can read them.
#
# Usage:
#   ./tools/fetch-images.sh <file.md>          # download + rewrite
#   ./tools/fetch-images.sh <file.md> --dry-run # list only, do not download
#
# After running: compile the file as normal — Claude will be able to read local images.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
IMG_DIR="$ROOT/raw/images"
mkdir -p "$IMG_DIR"

FILE="${1:-}"
DRY_RUN=false
[[ "${2:-}" == "--dry-run" ]] && DRY_RUN=true

if [[ -z "$FILE" ]]; then
  echo "Usage: $0 <file.md> [--dry-run]"
  exit 1
fi

if [[ ! -f "$FILE" ]]; then
  echo "Error: file not found: $FILE"
  exit 1
fi

# Compute relative path from file to raw/images/
FILE_DIR="$(cd "$(dirname "$FILE")" && pwd)"
REL_TO_IMG="$(python3 -c "
import os
file_dir = '$FILE_DIR'
img_dir  = '$IMG_DIR'
print(os.path.relpath(img_dir, file_dir))
")"

echo "=== fetch-images: $(basename "$FILE") ==="
echo "Images → raw/images/  (relative: $REL_TO_IMG)"
echo ""

# Extract external image URLs from markdown and HTML img tags
# Pattern 1: Markdown ![alt](https://...)
MD_URLS=$(grep -oE '!\[[^]]*\]\(https?://[^)]+\)' "$FILE" \
       | grep -oE 'https?://[^)]+' || true)

# Pattern 2: HTML <img src="https://..."> (double quotes)
HTML_URLS_DQ=$(grep -oE '<img[^>]+src="https?://[^"]*"' "$FILE" \
       | grep -oE 'https?://[^"]+' || true)

# Pattern 3: HTML <img src='https://...'> (single quotes)
HTML_URLS_SQ=$(grep -oE "<img[^>]+src='https?://[^']*'" "$FILE" \
       | grep -oE "https?://[^']+" || true)

# Combine and deduplicate
URLS=$(printf '%s\n%s\n%s\n' "$MD_URLS" "$HTML_URLS_DQ" "$HTML_URLS_SQ" \
       | grep -v '^$' | sort -u || true)

if [[ -z "$URLS" ]]; then
  echo "✓ No external images found."
  exit 0
fi

COUNT=0
ERRORS=0
TMPFILE=$(mktemp)
cp "$FILE" "$TMPFILE"

while IFS= read -r URL; do
  # Generate filename from URL
  BASENAME=$(basename "$URL" | sed 's/[?#].*//')
  EXT="${BASENAME##*.}"
  [[ "$EXT" == "$BASENAME" || ${#EXT} -gt 5 ]] && EXT="png"
  # Slug from basename, keep extension
  SLUG=$(echo "${BASENAME%.*}" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | sed 's/-*$//')
  FILENAME="${SLUG}.${EXT}"
  LOCAL_PATH="$IMG_DIR/$FILENAME"
  MD_PATH="${REL_TO_IMG}/${FILENAME}"

  echo "  ↓ $FILENAME"
  echo "    $URL"

  if $DRY_RUN; then
    COUNT=$((COUNT + 1))
    continue
  fi

  # Download if not already cached
  if [[ -f "$LOCAL_PATH" ]]; then
    echo "    (already exists locally, skipping)"
  else
    if curl -sL --max-time 15 -o "$LOCAL_PATH" "$URL" 2>/dev/null; then
      SIZE=$(du -sh "$LOCAL_PATH" 2>/dev/null | cut -f1)
      echo "    ✅ $SIZE"
    else
      echo "    ❌ Download failed"
      ERRORS=$((ERRORS + 1))
      continue
    fi
  fi

  # Rewrite URL in file (escape for sed)
  ESC_URL=$(printf '%s\n' "$URL" | sed 's/[[\.*^$()+?{|]/\\&/g')
  ESC_PATH=$(printf '%s\n' "$MD_PATH" | sed 's/[[\.*^$()+?{|]/\\&/g')
  sed -i.bak "s|${URL}|${MD_PATH}|g" "$TMPFILE"

  COUNT=$((COUNT + 1))
  echo ""
done <<< "$URLS"

if ! $DRY_RUN; then
  cp "$TMPFILE" "$FILE"
  rm -f "${TMPFILE}" "${FILE}.bak" "${TMPFILE}.bak"
  echo "=== Done: $COUNT image(s) downloaded, $ERRORS error(s) ==="
  echo "File URLs rewritten: $FILE"
else
  rm -f "$TMPFILE"
  echo "=== Dry run: found $COUNT external image(s) ==="
fi
