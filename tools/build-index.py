#!/usr/bin/env python3
import os
import re
from datetime import datetime

WIKI_DIR = "wiki"
DOMAINS_DIR = os.path.join(WIKI_DIR, "domains")
CONCEPTS_DIR = os.path.join(WIKI_DIR, "concepts")
SUMMARIES_DIR = os.path.join(WIKI_DIR, "summaries")
TOPICS_DIR = os.path.join(WIKI_DIR, "topics")
INDEX_FILE = os.path.join(WIKI_DIR, "index.md")
BRIEF_FILE = os.path.join(WIKI_DIR, "_brief.md")

# We will build DOMAINS_MAP dynamically inside main()

def parse_frontmatter(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        return None
    match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not match: return {}
    fm_text = match.group(1)
    fm = {}
    for line in fm_text.split('\n'):
        if ':' in line:
            parts = line.split(':', 1)
            k = parts[0].strip()
            v = parts[1].strip()
            # clean quotes
            if v.startswith('"') and v.endswith('"'): v = v[1:-1]
            elif v.startswith("'") and v.endswith("'"): v = v[1:-1]
            fm[k] = v
    return fm

def get_markdown_files(folder):
    if not os.path.exists(folder): return []
    return sorted([f for f in os.listdir(folder) if f.endswith('.md')])

def replace_between_markers(text, marker_name, replacement):
    # Ensure replacement ends with newline so markers stay on their own lines
    if replacement and not replacement.endswith('\n'):
        replacement += '\n'
    # Optional newline handling around replacement to keep it clean
    pattern = rf'(<!-- BUILD_INDEX:{marker_name}_START -->\n)([\s\S]*?)(<!-- BUILD_INDEX:{marker_name}_END -->)'
    def repl(m):
        return f"{m.group(1)}{replacement}{m.group(3)}"
    return re.sub(pattern, repl, text)

def main():
    print("Building Wiki Indexes...")
    
    DOMAINS_MAP = {}
    for f in get_markdown_files(DOMAINS_DIR):
        if f.startswith('_'): continue
        domain_slug = f.replace('.md', '')
        fm = parse_frontmatter(os.path.join(DOMAINS_DIR, f))
        title = fm.get('title', domain_slug.capitalize())
        if title.startswith('Domain: '):
            title = title[8:]
        DOMAINS_MAP[domain_slug] = title
    DOMAINS_MAP['meta'] = 'Meta'
    
    concepts_files = get_markdown_files(CONCEPTS_DIR)
    summaries_files = get_markdown_files(SUMMARIES_DIR)
    topics_files = get_markdown_files(TOPICS_DIR)
    
    concepts = []
    for f in concepts_files:
        fm = parse_frontmatter(os.path.join(CONCEPTS_DIR, f))
        slug = f.replace('.md', '')
        concepts.append({'slug': slug, 'fm': fm})
        
    summaries = []
    for f in summaries_files:
        fm = parse_frontmatter(os.path.join(SUMMARIES_DIR, f))
        slug = f.replace('.md', '')
        summaries.append({'slug': slug, 'fm': fm})
        
    topics = []
    for f in topics_files:
        fm = parse_frontmatter(os.path.join(TOPICS_DIR, f))
        slug = f.replace('.md', '')
        topics.append({'slug': slug, 'fm': fm})

    # Group by domain
    domain_concepts = {}
    for c in concepts:
        domain = c['fm'].get('domain', 'unknown')
        if domain not in domain_concepts: domain_concepts[domain] = []
        domain_concepts[domain].append(c)

    # 1. READ INDEX.MD (create from template if missing)
    if not os.path.exists(INDEX_FILE):
        today = datetime.now().strftime("%Y-%m-%d")
        with open(INDEX_FILE, 'w', encoding='utf-8') as f:
            f.write(f"""---
title: "Knowledge Base Index"
tags: [index, meta]
created: {today}
updated: {today}
---

# Knowledge Base — Index

> Master index. Auto-updated after each compile run.
> Read [[_brief]] for a quick context summary before querying.

---

## Domains

<!-- BUILD_INDEX:DOMAINS_START -->
| Domain | MOC | Description |
|--------|-----|-------------|
| _(empty — add content to populate)_ | - | - |
<!-- BUILD_INDEX:DOMAINS_END -->

---

## Concepts

<!-- BUILD_INDEX:CONCEPTS_START -->
| File | Domain | Description |
|------|--------|-------------|
| _(empty — run scan /raw to populate)_ | - | - |
<!-- BUILD_INDEX:CONCEPTS_END -->

---

## Topics

<!-- BUILD_INDEX:TOPICS_START -->
| File | Domain | Description |
|------|--------|-------------|
| _(none yet)_ | - | - |
<!-- BUILD_INDEX:TOPICS_END -->

---

## Summaries

<!-- BUILD_INDEX:SUMMARIES_START -->
| Source | File | Date |
|--------|------|------|
<!-- BUILD_INDEX:SUMMARIES_END -->

---

## Status

<!-- BUILD_INDEX:STATUS_START -->
- Total concepts: 0
- Total topics: 0
- Total summaries: 0
- Domains active: 0/4
- Last updated: {today}
<!-- BUILD_INDEX:STATUS_END -->
""")
        print("  ✨ Created wiki/index.md from template")
    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
        index_text = f.read()

    # Generate Concepts Table for index.md
    c_lines = ["| File | Domain | Description |", "|------|--------|-------------|"]
    for c in concepts:
        dom_display = DOMAINS_MAP.get(c['fm'].get('domain', 'unknown'), str(c['fm'].get('domain', 'unknown')).capitalize())
        # Auto remove formatting like brackets if present
        dom_display = re.sub(r'[^\w\s/]', '', dom_display).strip()
        c_lines.append(f"| [[concepts/{c['slug']}]] | {dom_display} | {c['fm'].get('title', c['slug'])} |")
        
    index_text = replace_between_markers(index_text, "CONCEPTS", "\n".join(c_lines))

    # Generate Topics Table for index.md
    t_lines = ["| File | Domain | Description |", "|------|--------|-------------|"]
    for t in topics:
        dom_display = DOMAINS_MAP.get(t['fm'].get('domain', 'unknown'), str(t['fm'].get('domain', 'unknown')).capitalize())
        dom_display = re.sub(r'[^\w\s/]', '', dom_display).strip()
        t_lines.append(f"| [[topics/{t['slug']}]] | {dom_display} | {t['fm'].get('title', t['slug'])} |")
    if len(topics) == 0: t_lines.append("| _(none yet)_ | - | - |")
    index_text = replace_between_markers(index_text, "TOPICS", "\n".join(t_lines))

    # Generate Summaries Table for index.md
    s_lines = ["| Source | File | Date |", "|--------|------|------|"]
    for s in summaries:
        created = s['fm'].get('created', '-')
        s_lines.append(f"| {s['fm'].get('title', s['slug'])} | [[summaries/{s['slug']}]] | {created} |")
    index_text = replace_between_markers(index_text, "SUMMARIES", "\n".join(s_lines))

    # Status 
    now_str = datetime.now().strftime("%Y-%m-%d")
    domain_count = len(get_markdown_files(DOMAINS_DIR)) - 1 # subtract _about-domains
    status_text = f"""- Total concepts: {len(concepts)}
- Total topics: {len(topics)}
- Total summaries: {len(summaries)}
- Domains active: {domain_count}/4
- Last updated: {now_str}"""
    index_text = replace_between_markers(index_text, "STATUS", status_text)

    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
        f.write(index_text)
        
    print("Updated index.md")

    # 2a. AUTO-CREATE DOMAIN SKELETONS (when ≥10 concepts, no MOC yet)
    DOMAIN_THRESHOLD = 10
    created_skeletons = []
    for domain_slug, d_concepts in domain_concepts.items():
        if domain_slug in ('meta', 'unknown'): continue
        if len(d_concepts) < DOMAIN_THRESHOLD: continue
        domain_file = os.path.join(DOMAINS_DIR, f"{domain_slug}.md")
        if os.path.exists(domain_file): continue

        # Collect summaries that reference this domain's concepts
        concept_slugs = {c['slug'] for c in d_concepts}
        related_summaries = []
        for s in summaries:
            spath = os.path.join(SUMMARIES_DIR, f"{s['slug']}.md")
            try:
                with open(spath, 'r', encoding='utf-8') as sf:
                    scontent = sf.read()
                if any(slug in scontent for slug in concept_slugs):
                    title = s['fm'].get('title', s['slug'])
                    related_summaries.append(f"- [[summaries/{s['slug']}]] — {title}")
            except Exception:
                pass

        summaries_block = "\n".join(related_summaries) if related_summaries else "- _(none yet)_"
        today = datetime.now().strftime("%Y-%m-%d")
        # Title: short slugs (≤4 chars) → uppercase (e.g. "ai" → "AI"), else title-case
        domain_title = domain_slug.upper() if len(domain_slug) <= 4 else domain_slug.replace('-', ' ').title()
        skeleton = f"""---
title: "Domain: {domain_title}"
tags: [domain, {domain_slug}]
created: {today}
updated: {today}
---

# Domain: {domain_title}

> Map of Content — entry point for knowledge about {domain_slug}.

## Concepts

<!-- BUILD_INDEX:CONCEPTS_START -->
<!-- BUILD_INDEX:CONCEPTS_END -->

## Topics

| Topic | Description |
|-------|-------------|
| _(none yet)_ | |

## Source Summaries

{summaries_block}

## Concept Seeds

_(none yet)_

## Related Domains

_(none yet)_
"""
        with open(domain_file, 'w', encoding='utf-8') as f:
            f.write(skeleton)

        # Register in DOMAINS_MAP so the update loop picks it up
        DOMAINS_MAP[domain_slug] = domain_title
        created_skeletons.append(domain_slug)
        print(f"  ✨ Auto-created domain skeleton: domains/{domain_slug}.md ({len(d_concepts)} concepts)")

    # 2. UPDATE DOMAIN MOCS
    for domain_slug in DOMAINS_MAP.keys():
        if domain_slug == 'meta': continue
        domain_file = os.path.join(DOMAINS_DIR, f"{domain_slug}.md")
        if not os.path.exists(domain_file): continue
        
        with open(domain_file, 'r', encoding='utf-8') as f:
            d_text = f.read()

        d_concepts = domain_concepts.get(domain_slug, [])
        d_c_lines = []
        for c in d_concepts:
            d_c_lines.append(f"- [[concepts/{c['slug']}]] — {c['fm'].get('title', c['slug'])}")
        if not d_c_lines: d_c_lines.append("- _(none yet)_")
        
        d_text = replace_between_markers(d_text, "CONCEPTS", "\n".join(d_c_lines))
        
        with open(domain_file, 'w', encoding='utf-8') as f:
            f.write(d_text)
            
    print("Updated domain MOCs")

    # 3. UPDATE _brief.md (create from template if missing)
    if not os.path.exists(BRIEF_FILE):
        today = datetime.now().strftime("%Y-%m-%d")
        with open(BRIEF_FILE, 'w', encoding='utf-8') as f:
            f.write(f"""---
title: "Wiki Brief — Quick Context"
tags: [meta, index]
created: {today}
updated: {today}
---

# Wiki Brief

> Read this before any Q&A query to get quick context on what the wiki covers.

## What This Wiki Covers

_Run `scan /raw` after adding content to populate this section._

## Domains

<!-- BUILD_INDEX:DOMAINS_START -->
| Domain | MOC | Concepts | Summaries | Status |
|--------|-----|----------|-----------|--------|
<!-- BUILD_INDEX:DOMAINS_END -->

## Recently Ingested

<!-- BUILD_INDEX:INGEST_START -->
<!-- BUILD_INDEX:INGEST_END -->

## Key Concepts

_Will be populated as content is added._

## Core Insights Log

_Key insights are appended here after each compile._
""")
        print("  ✨ Created wiki/_brief.md from template")
    with open(BRIEF_FILE, 'r', encoding='utf-8') as f:
        brief_text = f.read()
        
    b_lines = ["| Domain | MOC | Concepts | Summaries | Status |", "|--------|-----|----------|-----------|--------|"]
    for slug, emoji_name in DOMAINS_MAP.items():
        if slug == 'meta': continue
        c_count = len(domain_concepts.get(slug, []))
        # Count summaries manually by checking if summary slug contains domain or just assign rough
        s_count = 0 # It's hard to accurately map summary to domain if no domain field, but we can just use total or '-'
        # Let's count them roughly
        status = "🟢 Active" if c_count > 5 else "🟡 Just started"
        if c_count == 0: status = "⚪ Awaiting content"
        
        # status for summary count
        b_lines.append(f"| {emoji_name} | [[domains/{slug}]] | {c_count} | - | {status} |")
        
    brief_text = replace_between_markers(brief_text, "DOMAINS", "\n".join(b_lines))
    
    # Ingest list
    ingest_lines = []
    for i, s in enumerate(summaries[:15], 1):
        ingest_lines.append(f"{i}. `[[summaries/{s['slug']}]]` — {s['fm'].get('title', '')}")
    brief_text = replace_between_markers(brief_text, "INGEST", "\n".join(ingest_lines))
    
    with open(BRIEF_FILE, 'w', encoding='utf-8') as f:
        f.write(brief_text)
        
    print("Updated _brief.md")

if __name__ == '__main__':
    main()
