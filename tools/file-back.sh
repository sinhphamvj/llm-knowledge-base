#!/usr/bin/env bash
# file-back.sh — Write insights from output/query back to wiki so knowledge compounds
#
# This implements the "filed back" loop from the Karpathy diagram:
# each answer/output produces new insights → file back to wiki → wiki grows smarter
#
# Usage:
#   ./tools/file-back.sh --list               # list output files not yet filed back
#   ./tools/file-back.sh --log                # view file-back history
#   ./tools/file-back.sh --mark <output-file> # mark as filed back
#
# In practice, "file back" is performed by Claude Code when running the command:
#   file-back: <output-file>   → Claude reads the output and updates the wiki accordingly

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUTPUTS="$ROOT/outputs"
FB_LOG="$ROOT/wiki/.fileback-log"
touch "$FB_LOG"

case "${1:-}" in

  --list)
    echo "=== OUTPUTS NOT YET FILED BACK ==="
    found=0
    while IFS= read -r -d '' f; do
      rel="${f#$ROOT/}"
      [[ "$(basename "$f")" == "_template.md" ]] && continue
      if ! grep -qF "$rel" "$FB_LOG" 2>/dev/null; then
        # Show preview — title nếu có
        title=$(grep '^title:' "$f" 2>/dev/null | head -1 | sed 's/title: *//' | tr -d '"' || true)
        created=$(grep '^created:' "$f" 2>/dev/null | head -1 | sed 's/created: *//' || true)
        if [[ -n "$title" ]]; then
          echo "  📄 $rel"
          echo "     \"$title\" ($created)"
        else
          echo "  📄 $rel"
        fi
        ((found++)) || true
      fi
    done < <(find "$OUTPUTS" -name "*.md" -print0 | sort -z)

    if [[ $found -eq 0 ]]; then
      echo "  All outputs have been filed back. ✅"
    else
      echo ""
      echo "  → Total: $found output(s) pending file-back"
      echo ""
      echo "  To file back an output, run in Claude Code:"
      echo "    file-back: outputs/reports/ten-report.md"
      echo ""
      echo "  To mark as done manually:"
      echo "    ./tools/file-back.sh --mark outputs/reports/ten-report.md"
    fi
    ;;

  --log)
    echo "=== FILE-BACK LOG ==="
    if [[ ! -s "$FB_LOG" ]]; then
      echo "  (empty — no outputs have been filed back yet)"
    else
      printf "%-50s %-12s %-22s\n" "Output" "Type" "Filed at"
      printf "%-50s %-12s %-22s\n" "------" "----" "--------"
      while IFS='|' read -r file type date note; do
        printf "%-50s %-12s %-22s\n" "$file" "$type" "$date"
        [[ -n "$note" ]] && echo "   → $note"
      done < "$FB_LOG"
    fi
    ;;

  --mark)
    target="${2:-}"
    note="${4:-}"  # optional --note "text"
    [[ "${3:-}" == "--note" ]] && note="${4:-}"

    if [[ -z "$target" ]]; then
      echo "Usage: $0 --mark <output-file> [--note \"insight added\"]"
      exit 1
    fi

    full="$ROOT/$target"
    if [[ ! -f "$full" ]]; then
      echo "File not found: $full"
      exit 1
    fi

    # Detect type from path
    if [[ "$target" == *"/reports/"* ]]; then
      type="report"
    elif [[ "$target" == *"/slides/"* ]]; then
      type="slides"
    elif [[ "$target" == *"/notes/"* ]]; then
      type="notes"
    else
      type="output"
    fi

    ts=$(date '+%Y-%m-%d %H:%M')
    echo "${target}|${type}|${ts}|${note}" >> "$FB_LOG"
    echo "✅ Filed back: $target ($type, $ts${note:+ — $note})"
    ;;

  --stats)
    total_outputs=$(find "$OUTPUTS" -name "*.md" -not -name "_template.md" | wc -l | tr -d ' ')
    filed=$(wc -l < "$FB_LOG" | tr -d ' ')
    pending=$((total_outputs - filed))
    echo "Total outputs : $total_outputs"
    echo "Filed back    : $filed"
    echo "Pending       : $pending"
    ;;

  --verify)
    # Verify: check that wiki concepts were updated after the output was created
    target="${2:-}"
    if [[ -z "$target" ]]; then
      echo "Usage: $0 --verify <output-file>"
      echo "Example: $0 --verify outputs/reports/report-ai-safety-2026-04-04.md"
      exit 1
    fi
    full="$ROOT/$target"
    if [[ ! -f "$full" ]]; then
      echo "File not found: $full"
      exit 1
    fi

    output_mtime=$(stat -f "%m" "$full" 2>/dev/null || stat -c "%Y" "$full" 2>/dev/null || echo 0)
    output_created=$(grep '^created:' "$full" 2>/dev/null | head -1 | sed 's/created: *//' || echo "unknown")

    echo ""
    echo "=== VERIFY file-back: $(basename "$target") ==="
    echo "   Output created: $output_created"
    echo ""

    # Extract [[wikilinks]] mentioned in output
    LINKS=$(grep -oE '\[\[[^]|#]+' "$full" 2>/dev/null | sed 's/\[\[//' | sort -u || true)

    if [[ -z "$LINKS" ]]; then
      echo "   (No [[wikilinks]] found in output)"
      exit 0
    fi

    pass=0; warn=0; skip=0
    echo "   Wiki files được mention:"
    while IFS= read -r link; do
      # Strip path prefix if any (e.g. "concepts/foo" -> "foo")
      name="${link##*/}"
      found=$(find "$ROOT/wiki" -name "${name}.md" 2>/dev/null | head -1 || true)
      if [[ -z "$found" ]]; then
        echo "     ⏳ $name  (file does not exist yet)"
        ((skip++)) || true
        continue
      fi
      wiki_mtime=$(stat -f "%m" "$found" 2>/dev/null || stat -c "%Y" "$found" 2>/dev/null || echo 0)
      wiki_date=$(grep '^updated:' "$found" 2>/dev/null | head -1 | sed 's/updated: *//' || echo "unknown")
      if [[ $wiki_mtime -ge $output_mtime ]]; then
        echo "     ✅ ${name}  (updated: $wiki_date)"
        ((pass++)) || true
      else
        echo "     ⚠️  ${name}  (updated: $wiki_date — BEFORE output, may not have been filed back)"
        ((warn++)) || true
      fi
    done <<< "$LINKS"

    echo ""
    echo "   Result: $pass updated ✅ | $warn needs review ⚠️ | $skip file(s) not yet created ⏳"
    if [[ $warn -gt 0 ]]; then
      echo "   → Files marked ⚠️ may not have been filed back"
      echo "   → Kiểm tra và chạy: file-back: $target"
    fi
    echo ""

    ;;

  *)
    echo "file-back.sh — Filed back loop tracker"
    echo ""
    echo "Usage:"
    echo "  $0 --list               # outputs not yet filed back"
    echo "  $0 --mark <file>        # mark as filed back"
    echo "  $0 --mark <file> --note \"added to wiki/concepts/foo.md\""
    echo "  $0 --verify <file>      # check wiki was updated after output"
    echo "  $0 --log                # history"
    echo "  $0 --stats              # summary stats"
    ;;
esac
