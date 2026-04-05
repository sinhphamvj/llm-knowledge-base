#!/usr/bin/env bash
# save-image.sh — Download an image from a URL to raw/images/ with metadata
# Karpathy workflow: hotkey download related images to local so LLM can reference them
#
# Usage:
#   ./tools/save-image.sh <url> [name] [--source "article title"]
#   ./tools/save-image.sh https://example.com/diagram.png transformer-diagram --source "Attention Is All You Need"
#
# Setup browser hotkey (optional):
#   Use Raycast / Automator / Alfred:
#   → Grab URL from clipboard → call this script → copy local path back to clipboard

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
IMG_DIR="$ROOT/raw/images"
META_FILE="$ROOT/raw/images/_index.md"

mkdir -p "$IMG_DIR"

URL="${1:-}"
NAME="${2:-}"
SOURCE=""
DATE=$(date '+%Y-%m-%d')

# Parse args
shift 2 2>/dev/null || true
while [[ $# -gt 0 ]]; do
  case "$1" in
    --source) SOURCE="$2"; shift 2 ;;
    *) shift ;;
  esac
done

if [[ -z "$URL" ]]; then
  echo "Usage: $0 <url> [name] [--source \"article title\"]"
  echo ""
  echo "Examples:"
  echo "  $0 https://example.com/diagram.png transformer-arch --source 'Attention Is All You Need'"
  echo "  $0 https://example.com/chart.jpg   # auto-named by date"
  echo ""
  echo "Images saved to: raw/images/"
  echo "Index at: raw/images/_index.md"
  exit 1
fi

# Auto-generate name from URL if not provided
if [[ -z "$NAME" ]]; then
  url_basename=$(basename "$URL" | sed 's/[?#].*//')
  ext="${url_basename##*.}"
  [[ "$ext" == "$url_basename" ]] && ext="png"
  NAME="${DATE}-$(echo "$url_basename" | sed 's/\.[^.]*$//' | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | sed 's/-*$//')"
  FILENAME="${NAME}.${ext}"
else
  # Detect extension from URL
  url_ext=$(basename "$URL" | sed 's/[?#].*//' | grep -oE '\.[a-zA-Z]{3,4}$' || echo ".png")
  FILENAME="${NAME}${url_ext}"
fi

OUT="$IMG_DIR/$FILENAME"

echo "Downloading: $URL"
echo "Saving to:   raw/images/$FILENAME"

# Download
if command -v curl &>/dev/null; then
  curl -sL -o "$OUT" "$URL"
elif command -v wget &>/dev/null; then
  wget -q -O "$OUT" "$URL"
else
  echo "Error: curl or wget required"
  exit 1
fi

# Get file size
SIZE=$(du -sh "$OUT" | cut -f1)
echo "✅ Saved ($SIZE)"

# Update metadata index
if [[ ! -f "$META_FILE" ]]; then
  cat > "$META_FILE" << 'EOF'
---
title: "Image Index"
tags: [raw, images, index]
---

# Image Index

| File | Source | Date | Notes |
|------|--------|------|-------|
EOF
fi

# Append to index
echo "| ![$NAME](${FILENAME}) | ${SOURCE:-$URL} | $DATE | |" >> "$META_FILE"

# Print markdown reference for use in wiki
echo ""
echo "Markdown reference:"
echo "  ![${NAME}](../../raw/images/${FILENAME})"
echo ""
echo "Updated: raw/images/_index.md"
