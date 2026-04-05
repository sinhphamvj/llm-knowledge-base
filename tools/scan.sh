#!/usr/bin/env bash
# scan.sh — Track and list raw files that need processing
#
# Usage:
#   ./tools/scan.sh              # show all raw files + wiki status
#   ./tools/scan.sh --new        # only files not yet compiled
#   ./tools/scan.sh --status     # full table: processed / unprocessed / modified
#   ./tools/scan.sh --log        # view scan log
#   ./tools/scan.sh --mark <file> [--note "text"]  # mark file as compiled
#   ./tools/scan.sh --info <file> # check file length + suggest compile strategy

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RAW="$ROOT/raw"
LOG="$ROOT/wiki/.scan-log"

# Create log file if it doesn't exist
touch "$LOG"

_hash() {
  # Hash file content to detect changes
  md5 -q "$1" 2>/dev/null || md5sum "$1" 2>/dev/null | awk '{print $1}'
}

_all_raw() {
  find "$RAW" -type f \( -name "*.md" -o -name "*.txt" -o -name "*.pdf" -o -name "*.docx" -o -name "*.pptx" -o -name "*.xlsx" \) \
    -not -path "*/archived/*" -not -name ".gitkeep" | sort
}

case "${1:-}" in

  --new)
    echo "=== FILES NOT YET COMPILED ==="
    count=0
    while IFS= read -r f; do
      rel="${f#$ROOT/}"
      # Check log: no entry or hash has changed
      current_hash=$(_hash "$f")
      logged=$(grep "^$rel|" "$LOG" 2>/dev/null | tail -1 || true)
      if [[ -z "$logged" ]]; then
        echo "  [NEW]      $rel"
        if [[ "$rel" =~ \.(pdf|docx|pptx|xlsx)$ ]]; then
          echo "             ⚠️  File not yet converted — run ./tools/convert.sh first"
        fi
        ((count++)) || true
      else
        logged_hash=$(echo "$logged" | cut -d'|' -f2)
        if [[ "$current_hash" != "$logged_hash" ]]; then
          echo "  [MODIFIED] $rel"
          if [[ "$rel" =~ \.(pdf|docx|pptx|xlsx)$ ]]; then
            echo "             ⚠️  File not yet converted — run ./tools/convert.sh first"
          fi
          ((count++)) || true
        fi
      fi
    done < <(_all_raw)

    if [[ $count -eq 0 ]]; then
      echo "  All files already compiled. Nothing new."
    else
      echo ""
      echo "  → Total: $count file(s) pending"
      echo "  → Run 'scan /raw' in Claude Code to compile"
    fi
    ;;

  --status)
    echo "=== SCAN STATUS ==="
    printf "%-55s %-12s %-22s\n" "File" "Status" "Compiled at"
    printf "%-55s %-12s %-22s\n" "----" "------" "-----------"
    while IFS= read -r f; do
      rel="${f#$ROOT/}"
      current_hash=$(_hash "$f")
      logged=$(grep "^$rel|" "$LOG" 2>/dev/null | tail -1 || true)
      if [[ -z "$logged" ]]; then
        printf "%-55s %-12s %-22s\n" "$rel" "⚪ NEW" "-"
      else
        logged_hash=$(echo "$logged" | cut -d'|' -f2)
        logged_date=$(echo "$logged" | cut -d'|' -f3)
        if [[ "$current_hash" != "$logged_hash" ]]; then
          printf "%-55s %-12s %-22s\n" "$rel" "🟡 MODIFIED" "$logged_date"
        else
          printf "%-55s %-12s %-22s\n" "$rel" "✅ DONE" "$logged_date"
        fi
      fi
    done < <(_all_raw)

    echo ""
    total=$(_all_raw | wc -l | tr -d ' ')
    done_count=$(grep -c '^' "$LOG" 2>/dev/null | tr -d ' ' || echo 0)
    echo "Total: $total files | Compiled: $done_count entries in log"
    echo ""
    echo "=== WIKI ==="
    echo "Concepts : $(find "$ROOT/wiki/concepts" -name "*.md" | wc -l | tr -d ' ')"
    echo "Topics   : $(find "$ROOT/wiki/topics" -name "*.md" | wc -l | tr -d ' ')"
    echo "Summaries: $(find "$ROOT/wiki/summaries" -name "*.md" | wc -l | tr -d ' ')"
    echo "Domains  : $(find "$ROOT/wiki/domains" -name "*.md" -not -name "_*" | wc -l | tr -d ' ')"
    ;;

  --log)
    echo "=== SCAN LOG (wiki/.scan-log) ==="
    if [[ ! -s "$LOG" ]]; then
      echo "  (empty — no files compiled yet)"
    else
      printf "%-55s %-12s %-22s\n" "File" "Hash" "Date"
      printf "%-55s %-12s %-22s\n" "----" "----" "----"
      while IFS='|' read -r file hash date rest; do
        printf "%-55s %-12s %-22s\n" "$file" "${hash:0:8}..." "$date"
      done < "$LOG"
    fi
    ;;

  --mark)
    # Mark file as compiled — call after Claude finishes processing
    # Usage: ./tools/scan.sh --mark "raw/articles/foo.md" [--note "part 1/3 done"]
    target="${2:-}"
    if [[ -z "$target" ]]; then
      echo "Usage: $0 --mark <relative-path> [--note \"text\"]"
      echo "Example: $0 --mark 'raw/articles/foo.md'"
      echo "Example: $0 --mark 'raw/papers/big.pdf' --note 'part 1/3 done'"
      exit 1
    fi
    # Parse optional --note
    note=""
    shift 2 2>/dev/null || true
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --note) note="$2"; shift 2 ;;
        *) shift ;;
      esac
    done
    full="$ROOT/$target"
    if [[ ! -f "$full" ]]; then
      echo "File does not exist: $full"
      exit 1
    fi
    h=$(_hash "$full")
    ts=$(date '+%Y-%m-%d %H:%M')
    echo "${target}|${h}|${ts}|${note}" >> "$LOG"
    if [[ -n "$note" ]]; then
      echo "✅ Marked: $target (hash: ${h:0:8}..., time: $ts, note: $note)"
    else
      echo "✅ Marked: $target (hash: ${h:0:8}..., time: $ts)"
    fi
    ;;

  --info)
    # Check file length and suggest compile strategy
    # Usage: ./tools/scan.sh --info raw/papers/paper.pdf
    target="${2:-}"
    if [[ -z "$target" ]]; then
      echo "Usage: $0 --info <relative-path>"
      echo "Example: $0 --info raw/papers/attention-paper.pdf"
      exit 1
    fi
    full="$ROOT/$target"
    if [[ ! -f "$full" ]]; then
      echo "File does not exist: $full"
      exit 1
    fi
    ext="${target##*.}"
    ext_lower=$(echo "$ext" | tr '[:upper:]' '[:lower:]')

    echo "=== FILE INFO: $target ==="
    size=$(du -sh "$full" | cut -f1)
    echo "Size      : $size"

    # Check status in log
    rel="$target"
    current_hash=$(_hash "$full")
    logged=$(grep "^$rel|" "$LOG" 2>/dev/null | tail -1 || true)
    if [[ -z "$logged" ]]; then
      echo "Status     : ⚪ NEW — not yet compiled"
    else
      logged_hash=$(echo "$logged" | cut -d'|' -f2)
      logged_date=$(echo "$logged" | cut -d'|' -f3)
      logged_note=$(echo "$logged" | cut -d'|' -f4)
      if [[ "$current_hash" != "$logged_hash" ]]; then
        echo "Status     : 🟡 MODIFIED (compiled at $logged_date)"
      else
        echo "Status     : ✅ DONE (compiled at $logged_date${logged_note:+ — $logged_note})"
      fi
    fi

    echo ""

    case "$ext_lower" in
      pdf|docx|pptx|xlsx)
        echo "Type       : $ext_lower (Binary/Office Format)"
        echo "Strategy   : ⚠️ CONVERT FIRST (run: ./tools/convert.sh)"
        echo "  → After converting to .md, use AI to read using the Text/Markdown file thresholds."
        ;;
      md|txt)
        words=$(wc -w < "$full" | tr -d ' ')
        echo "Type       : Text / Markdown"
        echo "Word count : ~$words words"
        echo ""
        if [[ "$words" -lt 4000 ]]; then
          echo "Suggested strategy: STUFFING"
          echo "  → Read entire file at once, compile as normal"
        elif [[ "$words" -le 10000 ]]; then
          echo "Suggested strategy: REFINE"
          echo "  → Read sequentially by section, maintain a running summary"
          echo "  → Estimated ~$((words / 500 + 1)) reads (each chunk ~500 words)"
        elif [[ "$words" -le 25000 ]]; then
          echo "Suggested strategy: MAP-REDUCE"
          echo "  → Split into parallel chunks of ~4000 words each"
          echo "  → Combine chunk summaries into a final summary"
        else
          echo "Suggested strategy: HIERARCHICAL SPLIT"
          echo "  → Document too long. Create part summaries for each section, then synthesize."
        fi
        ;;
      *)
        echo "Type       : $ext_lower"
        echo "Strategy   : Read directly (no special handling needed)"
        ;;
    esac
    echo ""
    ;;

  *)
    # Default: show all + wiki status
    echo "=== ALL RAW FILES ==="
    _all_raw | while read -r f; do
      echo "  ${f#$ROOT/}"
    done

    echo ""
    echo "=== WIKI STATUS ==="
    echo "Concepts : $(find "$ROOT/wiki/concepts" -name "*.md" | wc -l | tr -d ' ')"
    echo "Topics   : $(find "$ROOT/wiki/topics" -name "*.md" | wc -l | tr -d ' ')"
    echo "Summaries: $(find "$ROOT/wiki/summaries" -name "*.md" | wc -l | tr -d ' ')"
    echo "Domains  : $(find "$ROOT/wiki/domains" -name "*.md" -not -name "_*" | wc -l | tr -d ' ')"
    echo ""
    echo "Run './tools/scan.sh --status' to see per-file status"
    ;;
esac
