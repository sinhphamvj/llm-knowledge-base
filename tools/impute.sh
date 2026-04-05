#!/usr/bin/env bash
# impute.sh — Create a skeleton concept file for the web-impute workflow
#
# When AI runs "web-impute: <topic>", call this script first to:
#   - Pre-create a file with correctly formatted frontmatter
#   - Set confidence: low (web-sourced)
#   - Automatically mark [needs verification]
#   - AI only needs to fill in content, no need to worry about format
#
# Usage:
#   ./tools/impute.sh "mixture of experts"
#   ./tools/impute.sh "KV Cache" --domain ai
#   ./tools/impute.sh "design patterns" --domain technology
#   ./tools/impute.sh --list   # list files recently imputed (confidence: low)

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WIKI="$ROOT/wiki"

# ─── Parse args ───────────────────────────────────────────────────────────────
TERM="${1:-}"
DOMAIN="${3:-}"  # default empty, AI will fill in
TODAY=$(date '+%Y-%m-%d')

# --list mode
if [[ "$TERM" == "--list" ]]; then
  echo "=== IMPUTED CONCEPTS (confidence: low) ==="
  found=0
  while IFS= read -r -d '' f; do
    if grep -q "^confidence: low" "$f" 2>/dev/null; then
      name=$(basename "$f" .md)
      created=$(grep "^created:" "$f" 2>/dev/null | head -1 | sed 's/created: *//' || echo "?")
      domain=$(grep "^domain:" "$f" 2>/dev/null | head -1 | sed 's/domain: *//' || echo "?")
      echo "  📄 $name  [domain: $domain, created: $created]"
      ((found++)) || true
    fi
  done < <(find "$WIKI/concepts" -name "*.md" -print0 2>/dev/null)
  echo ""
  [[ $found -eq 0 ]] && echo "  (none — all concepts have raw sources)" || echo "  Total: $found concept(s) need verification"
  exit 0
fi

if [[ -z "$TERM" ]]; then
  echo "Usage: $0 \"<topic name>\" [--domain <domain>]"
  echo "       $0 --list"
  echo ""
  echo "Examples:"
  echo "  $0 \"mixture of experts\""
  echo "  $0 \"KV Cache\" --domain ai"
  echo "  $0 \"design patterns\" --domain technology"
  exit 1
fi

# Parse --domain flag
if [[ "${2:-}" == "--domain" && -n "${3:-}" ]]; then
  DOMAIN="${3}"
fi

# ─── Generate slug ─────────────────────────────────────────────────────────────
SLUG=$(echo "$TERM" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cs 'a-z0-9-' '-' | sed 's/-*$//' | sed 's/^-*//')
TITLE=$(echo "$TERM" | sed 's/\b./\u&/g')  # Title Case

OUTPUT="$WIKI/concepts/${SLUG}.md"

# ─── Check if already exists ──────────────────────────────────────────────────
if [[ -f "$OUTPUT" ]]; then
  existing_domain=$(grep "^domain:" "$OUTPUT" 2>/dev/null | head -1 | sed 's/domain: *//' || echo "?")
  existing_conf=$(grep "^confidence:" "$OUTPUT" 2>/dev/null | head -1 | sed 's/confidence: *//' || echo "high")
  echo "⚠️  File already exists: wiki/concepts/${SLUG}.md"
  echo "   domain: $existing_domain | confidence: $existing_conf"
  echo ""
  echo "Skipping creation. To edit: open \"$OUTPUT\""
  exit 0
fi

# ─── Detect domain from existing wiki if not specified ────────────────────────
if [[ -z "$DOMAIN" ]]; then
  # Try to guess domain from slug keywords
  if echo "$SLUG" | grep -qiE "model|llm|gpt|bert|attention|training|alignment|rlhf|safety|inference|token|embed"; then
    DOMAIN="ai"
  elif echo "$SLUG" | grep -qiE "product|pmf|user|growth|metric|ux|design|discovery"; then
    DOMAIN="product"
  elif echo "$SLUG" | grep -qiE "agile|sprint|kanban|project|delivery|stakeholder|planning"; then
    DOMAIN="project"
  elif echo "$SLUG" | grep -qiE "system|api|database|cloud|infra|security|docker|code|architecture"; then
    DOMAIN="technology"
  else
    DOMAIN="ai"  # default
  fi
  echo "ℹ️  Domain auto-detected: $DOMAIN (can be changed in file)"
fi

# ─── Write skeleton file ──────────────────────────────────────────────────────
cat > "$OUTPUT" << SKELETON
---
title: "${TITLE}"
domain: ${DOMAIN}
tags: [${SLUG}]
created: ${TODAY}
updated: ${TODAY}
source: "web search ${TODAY}"
confidence: low
---

# ${TITLE}

> ⚠️ **[needs verification]** — Created via \`web-impute\`, no raw source in \`/raw\` yet.
> When official source is available: update \`source:\` and change \`confidence: low\` → \`medium\` or \`high\`.

## Definition

[Fill in — short, clear explanation. Why does this concept matter?]

## How It Works

[Fill in — mechanism, formula if applicable, concrete examples]

## Applications / Significance

[Fill in — where it's used, why it matters in current context]

## Limitations / Trade-offs

[Fill in — when it doesn't work well, trade-offs]

## See also

- [[domains/${DOMAIN}]]
- [Add links to related concepts]

---

*Imputed via web search — ${TODAY}*
SKELETON

echo ""
echo "✅ Skeleton created: wiki/concepts/${SLUG}.md"
echo ""
echo "Next steps:"
echo "  1. AI searches the web: \"${TERM} explanation\""
echo "  2. Fill in content in file: wiki/concepts/${SLUG}.md"
echo "  3. Update domain MOC: wiki/domains/${DOMAIN}.md"
echo "  4. Update index.md and _brief.md"
echo ""
echo "After verifying with a raw source:"
echo "  → Change confidence: low → medium or high"
echo "  → Update source: \"<paper name or URL>\""
