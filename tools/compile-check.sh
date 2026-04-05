#!/usr/bin/env bash
# compile-check.sh — Verify all 9 compile steps after AI finishes processing a raw file
#
# Run after compile is done to ensure no steps were skipped:
#   ./tools/compile-check.sh "raw/articles/ten-file.md"
#   ./tools/compile-check.sh "raw/repos/karpathy-nanoGPT.md"
#
# Exit code: 0 = pass, 1 = errors need fixing

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WIKI="$ROOT/wiki"
LOG="$WIKI/.scan-log"

# ─── Colors ───────────────────────────────────────────────────────────────────
GREEN="\033[0;32m"; YELLOW="\033[0;33m"; RED="\033[0;31m"; RESET="\033[0m"
ok()   { echo -e "  ${GREEN}✅ Step $1${RESET}: $2"; }
warn() { echo -e "  ${YELLOW}⚠️  Step $1${RESET}: $2"; }
fail() { echo -e "  ${RED}❌ Step $1${RESET}: $2"; }

# ─── Args ─────────────────────────────────────────────────────────────────────
TARGET="${1:-}"
if [[ -z "$TARGET" ]]; then
  echo "Usage: $0 <relative-path-to-raw-file>"
  echo "Example: $0 'raw/articles/my-article.md'"
  echo "Example: $0 'raw/repos/karpathy-nanoGPT.md'"
  exit 1
fi

FULL_PATH="$ROOT/$TARGET"
if [[ ! -f "$FULL_PATH" ]]; then
  # Check if the original file was archived after conversion
  ARCHIVED_PATH=$(echo "$FULL_PATH" | sed 's|/raw/|/raw/archived/|')
  if [[ -f "$ARCHIVED_PATH" ]]; then
    echo "⚠️  Original file has been archived at: $ARCHIVED_PATH"

    # Switch target to the corresponding converted .md file
    TARGET="${TARGET%.*}.md"
    FULL_PATH="$ROOT/$TARGET"
    if [[ ! -f "$FULL_PATH" ]]; then
       echo "❌ Converted Markdown file not found: $FULL_PATH"
       echo "   Please re-run ./tools/convert.sh"
       exit 1
    else
       echo "✅ Auto-redirected to converted Markdown: $TARGET"
    fi
  else
    echo "❌ File does not exist: $FULL_PATH"
    exit 1
  fi
fi

# Block check if input file is .pdf/.docx/etc. and has not been converted yet
TARGET_EXT_LOWER=$(echo "${TARGET##*.}" | tr '[:upper:]' '[:lower:]')
if [[ "$TARGET_EXT_LOWER" =~ ^(pdf|docx|pptx|xlsx)$ ]]; then
  echo "❌ File has not been converted yet ($TARGET)!"
  echo "   Please run: ./tools/convert.sh \"$TARGET\" before compiling."
  exit 1
fi

# ─── Derive expected artifacts ────────────────────────────────────────────────
# Slug = basename without extension, lowercased, spaces→hyphens
BASENAME=$(basename "$TARGET")
BASENAME_NOEXT="${BASENAME%.*}"
SLUG=$(echo "$BASENAME_NOEXT" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cs 'a-z0-9-' '-' | sed 's/-*$//')

# Timestamp of the raw file (modification time)
FILE_MTIME=$(stat -f "%m" "$FULL_PATH" 2>/dev/null || stat -c "%Y" "$FULL_PATH" 2>/dev/null || echo 0)

ISSUES=0
WARNINGS=0

echo ""
echo "=== COMPILE CHECK: $TARGET ==="
echo ""

# ─── Step 1: Has scan.sh --mark been run? ────────────────────────────────────
if grep -qF "$TARGET|" "$LOG" 2>/dev/null; then
  logged=$(grep "$TARGET|" "$LOG" | tail -1)
  logged_date=$(echo "$logged" | cut -d'|' -f3)
  ok "1" "scan.sh --mark already run ($logged_date)"
else
  fail "1" "scan.sh --mark NOT yet run for this file"
  echo "       → Run: ./tools/scan.sh --mark \"$TARGET\""
  ((ISSUES++)) || true
fi

# ─── Step 2: fetch-images.sh (warn only if external images exist) ────────────
# Check if the file contains external image URLs
if [[ "${TARGET##*.}" =~ ^(md|txt)$ ]]; then
  img_count=$(grep -cE '!\[[^]]*\]\(https?://' "$FULL_PATH" 2>/dev/null || true)
  img_html=$(grep -cE '<img[^>]+src="https?://' "$FULL_PATH" 2>/dev/null || true)
  total_imgs=$((img_count + img_html))
  if [[ $total_imgs -gt 0 ]]; then
    # Check if images were downloaded (raw/images/ has files newer than file)
    recent_images=$(find "$ROOT/raw/images" -newer "$FULL_PATH" -name "*.png" -o -name "*.jpg" -o -name "*.gif" -o -name "*.webp" 2>/dev/null | wc -l | tr -d ' ')
    if [[ "$recent_images" -gt 0 ]]; then
      ok "2" "fetch-images.sh already run ($recent_images new image(s) in raw/images/)"
    else
      warn "2" "File has $total_imgs external image(s) but no new images found in raw/images/"
      echo "       → If not yet fetched: ./tools/fetch-images.sh \"$TARGET\""
      ((WARNINGS++)) || true
    fi
  else
    ok "2" "No external images (skip fetch-images.sh)"
  fi
else
  ok "2" "File is not markdown/text (skip image check)"
fi

# ─── Step 3: Read raw file ────────────────────────────────────────────────────
# Cannot verify AI read it, but check file size > 0
if [[ -s "$FULL_PATH" ]]; then
  size=$(du -sh "$FULL_PATH" | cut -f1)
  ok "3" "Raw file exists and has content ($size)"
else
  fail "3" "Raw file is empty!"
  ((ISSUES++)) || true
fi

# ─── Step 4: wiki/summaries/<slug>.md exists ─────────────────────────────────
SUMMARY_EXACT="$WIKI/summaries/${SLUG}.md"
# Also search for any summary file that contains the slug
SUMMARY_FOUND=$(find "$WIKI/summaries" -name "*.md" -newer "$FULL_PATH" 2>/dev/null | head -1 || true)

if [[ -f "$SUMMARY_EXACT" ]]; then
  ok "4" "Summary: wiki/summaries/${SLUG}.md ✓"
elif [[ -n "$SUMMARY_FOUND" ]]; then
  found_name=$(basename "$SUMMARY_FOUND")
  ok "4" "Summary found (different slug): $found_name"
else
  fail "4" "Summary file not found"
  echo "       → Need to create: wiki/summaries/${SLUG}.md"
  echo "       → Or different filename? Check: ls wiki/summaries/ | grep -i \"${SLUG:0:10}\""
  ((ISSUES++)) || true
fi

# ─── Step 5: Any new files in wiki/concepts/? ────────────────────────────────
NEW_CONCEPTS=$(find "$WIKI/concepts" -name "*.md" -newer "$FULL_PATH" 2>/dev/null | wc -l | tr -d ' ')
if [[ "$NEW_CONCEPTS" -gt 0 ]]; then
  concept_names=$(find "$WIKI/concepts" -name "*.md" -newer "$FULL_PATH" 2>/dev/null | xargs -I{} basename {} .md | tr '\n' ', ' | sed 's/,$//')
  ok "5" "New concepts ($NEW_CONCEPTS): $concept_names"
else
  warn "5" "No new concept files found after the raw file's timestamp"
  echo "       → If only updating existing concepts: okay, ignore this warning"
  echo "       → If no concept created yet: need to create wiki/concepts/<name>.md"
  ((WARNINGS++)) || true
fi

# ─── Step 6: wiki/domains/<domain>.md has been updated ───────────────────────
UPDATED_DOMAINS=$(find "$WIKI/domains" -name "*.md" -not -name "_*" -newer "$FULL_PATH" 2>/dev/null | wc -l | tr -d ' ')
if [[ "$UPDATED_DOMAINS" -gt 0 ]]; then
  domain_names=$(find "$WIKI/domains" -name "*.md" -not -name "_*" -newer "$FULL_PATH" 2>/dev/null | xargs -I{} basename {} .md | tr '\n' ', ' | sed 's/,$//')
  ok "6" "Domain MOC updated: $domain_names"
else
  fail "6" "No domain MOC was updated after the raw file"
  echo "       → Need to update wiki/domains/<domain>.md"
  ((ISSUES++)) || true
fi

# ─── Step 7: wiki/index.md has been updated ──────────────────────────────────
if [[ "$WIKI/index.md" -nt "$FULL_PATH" ]]; then
  # Read current counter
  concepts_count=$(grep "Tổng concepts:" "$WIKI/index.md" 2>/dev/null | grep -oE '[0-9]+' || echo "?")
  ok "7" "index.md updated (Total concepts: $concepts_count)"
else
  fail "7" "wiki/index.md has not been updated"
  echo "       → Need to update: wiki/index.md (add concept + summary + increment counter)"
  ((ISSUES++)) || true
fi

# ─── Step 8: wiki/_brief.md has been updated ─────────────────────────────────
if [[ "$WIKI/_brief.md" -nt "$FULL_PATH" ]]; then
  updated=$(grep "^updated:" "$WIKI/_brief.md" 2>/dev/null | head -1 | sed 's/updated: *//' | tr -d '"' || echo "?")
  ok "8" "_brief.md updated (updated: $updated)"
else
  fail "8" "wiki/_brief.md has not been updated"
  echo "       → Need to update: wiki/_brief.md (domains table + key insights + gaps)"
  ((ISSUES++)) || true
fi

# ─── Step 9: scan.sh --mark (re-check) ───────────────────────────────────────
# Already checked in step 1 — just confirm
if grep -qF "$TARGET|" "$LOG" 2>/dev/null; then
  ok "9" "scan.sh --mark confirmed ✓"
else
  fail "9" "scan.sh --mark still not run"
  echo "       → Run: ./tools/scan.sh --mark \"$TARGET\""
  ((ISSUES++)) || true
fi

# ─── Summary ──────────────────────────────────────────────────────────────────
echo ""
echo "─────────────────────────────────────────"
if [[ $ISSUES -eq 0 && $WARNINGS -eq 0 ]]; then
  echo -e "${GREEN}✅ PASS — Compile complete! ($TARGET)${RESET}"
elif [[ $ISSUES -eq 0 ]]; then
  echo -e "${YELLOW}⚠️  PASS WITH WARNINGS — $WARNINGS warning(s) (see above)${RESET}"
else
  echo -e "${RED}❌ FAIL — $ISSUES error(s), $WARNINGS warning(s) need review${RESET}"
fi
echo "─────────────────────────────────────────"
echo ""

[[ $ISSUES -eq 0 ]] && exit 0 || exit 1
