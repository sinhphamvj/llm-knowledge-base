#!/usr/bin/env bash
# fetch-repo.sh — Fetch GitHub repo content into raw/repos/ for Claude to ingest
#
# Obsidian Web Clipper cannot clip GitHub repos (JS-heavy, not a plain article).
# This script uses the GitHub API (no auth needed for public repos) to pull:
#   - Metadata (description, stars, language, topics)
#   - README
#   - File tree (top 2 levels)
#   - Docs/ or docs-like files if present
#
# Usage:
#   ./tools/fetch-repo.sh <github-url-or-owner/repo>
#   ./tools/fetch-repo.sh https://github.com/karpathy/nanoGPT
#   ./tools/fetch-repo.sh karpathy/nanoGPT
#   ./tools/fetch-repo.sh karpathy/nanoGPT --docs     # also fetch docs/ folder
#   ./tools/fetch-repo.sh karpathy/nanoGPT --dry-run  # preview what file will be created

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO_DIR="$ROOT/raw/repos"
mkdir -p "$REPO_DIR"

# ─── Parse args ───────────────────────────────────────────────────────────────
INPUT="${1:-}"
FETCH_DOCS=false
DRY_RUN=false

if [[ -z "$INPUT" ]]; then
  echo "Usage: $0 <github-url-or-owner/repo> [--docs] [--dry-run]"
  echo ""
  echo "Examples:"
  echo "  $0 karpathy/nanoGPT"
  echo "  $0 https://github.com/anthropics/anthropic-sdk-python"
  echo "  $0 huggingface/transformers --docs"
  exit 1
fi

for arg in "${@:2}"; do
  case "$arg" in
    --docs)    FETCH_DOCS=true ;;
    --dry-run) DRY_RUN=true ;;
  esac
done

# Normalize: strip https://github.com/ prefix
REPO_SLUG=$(echo "$INPUT" \
  | sed 's|https://github.com/||' \
  | sed 's|http://github.com/||' \
  | sed 's|github.com/||' \
  | sed 's|/$||')

# Validate format owner/repo
if [[ ! "$REPO_SLUG" =~ ^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$ ]]; then
  echo "❌ Unrecognized format: $INPUT"
  echo "   Expected: owner/repo or https://github.com/owner/repo"
  exit 1
fi

OWNER="${REPO_SLUG%%/*}"
REPO="${REPO_SLUG##*/}"
OUTPUT_FILE="$REPO_DIR/${OWNER}-${REPO}.md"

echo "=== fetch-repo: $REPO_SLUG ==="
echo "→ Output: raw/repos/${OWNER}-${REPO}.md"
echo ""

if $DRY_RUN; then
  echo "(dry-run — no actual fetching)"
  exit 0
fi

# ─── Helper: GitHub API ────────────────────────────────────────────────────────
gh_api() {
  local endpoint="$1"
  local url="https://api.github.com${endpoint}"
  curl -sSL \
    -H "Accept: application/vnd.github.v3+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "$url" 2>/dev/null
}

gh_raw() {
  # Fetch raw content of a single file
  local owner="$1" repo="$2" path="$3" ref="${4:-HEAD}"
  curl -sSL "https://raw.githubusercontent.com/${owner}/${repo}/${ref}/${path}" 2>/dev/null
}

# ─── 1. Metadata ──────────────────────────────────────────────────────────────
echo "1/4 Fetching metadata..."
META=$(gh_api "/repos/${REPO_SLUG}")

if echo "$META" | python3 -c "import sys,json; d=json.load(sys.stdin); exit(0 if 'id' in d else 1)" 2>/dev/null; then
  DESCRIPTION=$(echo "$META" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('description') or '')")
  STARS=$(echo "$META" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('stargazers_count',0))")
  LANGUAGE=$(echo "$META" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('language') or 'unknown')")
  DEFAULT_BRANCH=$(echo "$META" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('default_branch','main'))")
  TOPICS=$(echo "$META" | python3 -c "
import sys,json
d=json.load(sys.stdin)
topics = d.get('topics', [])
print(', '.join(topics) if topics else 'none')
")
  LICENSE=$(echo "$META" | python3 -c "
import sys,json
d=json.load(sys.stdin)
lic = d.get('license')
print(lic['spdx_id'] if lic else 'none')
")
  PUSHED=$(echo "$META" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('pushed_at','')[:10])")
  echo "   ✅ $DESCRIPTION ($STARS ⭐, $LANGUAGE)"
else
  echo "   ⚠️  Could not fetch metadata (private repo or does not exist?)"
  DESCRIPTION=""; STARS="?"; LANGUAGE="unknown"; DEFAULT_BRANCH="main"
  TOPICS=""; LICENSE=""; PUSHED=""
fi

# ─── 2. README ────────────────────────────────────────────────────────────────
echo "2/4 Fetching README..."
README_CONTENT=""
for readme_name in README.md README.rst README.txt readme.md; do
  content=$(gh_raw "$OWNER" "$REPO" "$readme_name" "$DEFAULT_BRANCH")
  if [[ -n "$content" && "$content" != "404: Not Found" ]]; then
    README_CONTENT="$content"
    echo "   ✅ $readme_name ($(echo "$README_CONTENT" | wc -w | tr -d ' ') words)"
    break
  fi
done
[[ -z "$README_CONTENT" ]] && echo "   ⚠️  README not found"

# ─── 3. File tree (top 2 levels) ──────────────────────────────────────────────
echo "3/4 Fetching file tree..."
TREE_JSON=$(gh_api "/repos/${REPO_SLUG}/git/trees/${DEFAULT_BRANCH}?recursive=0")
FILE_TREE=""
if echo "$TREE_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); exit(0 if 'tree' in d else 1)" 2>/dev/null; then
  FILE_TREE=$(echo "$TREE_JSON" | python3 -c "
import sys,json
d=json.load(sys.stdin)
entries = d.get('tree',[])
lines = []
for e in entries:
  path = e.get('path','')
  typ  = e.get('type','')
  size = e.get('size')
  prefix = '📁' if typ == 'tree' else '📄'
  if size:
    kb = f'{size/1024:.1f}KB' if size > 1024 else f'{size}B'
    lines.append(f'{prefix} {path}  ({kb})')
  else:
    lines.append(f'{prefix} {path}')
print('\n'.join(lines[:60]))
if len(entries) > 60:
    print(f'... (+ {len(entries)-60} more)')
")
  echo "   ✅ $(echo "$FILE_TREE" | wc -l | tr -d ' ') entries"
else
  echo "   ⚠️  Could not fetch file tree"
fi

# ─── 4. Docs folder (optional) ────────────────────────────────────────────────
DOCS_CONTENT=""
if $FETCH_DOCS; then
  echo "4/4 Fetching docs/..."
  for docs_dir in docs/ doc/ documentation/ DOCS/; do
    DOCS_JSON=$(gh_api "/repos/${REPO_SLUG}/contents/${docs_dir%/}")
    if echo "$DOCS_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); exit(0 if isinstance(d,list) else 1)" 2>/dev/null; then
      DOC_FILES=$(echo "$DOCS_JSON" | python3 -c "
import sys,json
files=json.load(sys.stdin)
md_files=[f for f in files if f.get('name','').endswith('.md') and f.get('type')=='file']
for f in md_files[:5]:  # max 5 doc files
  print(f['path'])
")
      if [[ -n "$DOC_FILES" ]]; then
        echo "   Found docs in $docs_dir"
        while IFS= read -r doc_path; do
          doc_content=$(gh_raw "$OWNER" "$REPO" "$doc_path" "$DEFAULT_BRANCH")
          if [[ -n "$doc_content" && "$doc_content" != "404: Not Found" ]]; then
            DOCS_CONTENT+="\n\n## 📄 ${doc_path}\n\n${doc_content}"
            echo "   ✅ $doc_path"
          fi
        done <<< "$DOC_FILES"
        break
      fi
    fi
  done
  [[ -z "$DOCS_CONTENT" ]] && echo "4/4 (--docs requested but no docs/ folder found)"
else
  echo "4/4 (skip docs — use --docs to fetch)"
fi

# ─── 5. Write output file ─────────────────────────────────────────────────────
echo ""
echo "Generating raw/repos/${OWNER}-${REPO}.md..."

TODAY=$(date '+%Y-%m-%d')

cat > "$OUTPUT_FILE" << FRONTMATTER
---
title: "${OWNER}/${REPO}"
source: "https://github.com/${REPO_SLUG}"
type: github-repo
language: "${LANGUAGE}"
stars: ${STARS}
topics: "${TOPICS}"
license: "${LICENSE}"
last_pushed: "${PUSHED}"
created: ${TODAY}
description: "${DESCRIPTION}"
tags:
  - "repo"
---

# ${REPO}

> ${DESCRIPTION}

**GitHub**: https://github.com/${REPO_SLUG}
**Language**: ${LANGUAGE} | **Stars**: ${STARS} | **License**: ${LICENSE}
**Topics**: ${TOPICS}
**Last pushed**: ${PUSHED}

---

## README

FRONTMATTER

# Append README
if [[ -n "$README_CONTENT" ]]; then
  echo "$README_CONTENT" >> "$OUTPUT_FILE"
else
  echo "_README not found_" >> "$OUTPUT_FILE"
fi

# Append file tree
cat >> "$OUTPUT_FILE" << 'TREE_SECTION'

---

## File Structure

TREE_SECTION

if [[ -n "$FILE_TREE" ]]; then
  echo '```' >> "$OUTPUT_FILE"
  echo "$FILE_TREE" >> "$OUTPUT_FILE"
  echo '```' >> "$OUTPUT_FILE"
else
  echo "_File tree could not be fetched_" >> "$OUTPUT_FILE"
fi

# Append docs if fetched
if [[ -n "$DOCS_CONTENT" ]]; then
  echo "" >> "$OUTPUT_FILE"
  echo "---" >> "$OUTPUT_FILE"
  echo "" >> "$OUTPUT_FILE"
  echo "## Documentation" >> "$OUTPUT_FILE"
  printf "%b" "$DOCS_CONTENT" >> "$OUTPUT_FILE"
fi

SIZE=$(du -sh "$OUTPUT_FILE" | cut -f1)
WORDS=$(wc -w < "$OUTPUT_FILE" | tr -d ' ')
echo ""
echo "=== Done ==="
echo "File: raw/repos/${OWNER}-${REPO}.md ($SIZE, ~$WORDS words)"
echo ""
echo "Next steps:"
echo "  1. Preview: cat raw/repos/${OWNER}-${REPO}.md | head -50"
echo "  2. Ingest: compile raw/repos/${OWNER}-${REPO}.md  (in Claude Code)"
echo "  3. Or: scan /raw  (to compile all new files at once)"
