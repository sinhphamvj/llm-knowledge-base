---
title: "Domain MOCs Guide"
tags: [meta, domains]
created: 2026-01-01
updated: 2026-01-01
---

# Domain MOCs — Organization Guide

## What Is a Domain?

A domain is an **entry point** for a knowledge area, not a container.
- Concepts live in `wiki/concepts/` — they can belong to multiple domains
- A domain MOC is simply a navigation map (Map of Content)

---

## When to Create a New Domain?

**Only create one when you have ≥10 concepts clearly belonging to the same topic.**
Don't design domains upfront — let them emerge naturally from your data.

Use `lint` to automatically detect potential domains:
```bash
./tools/lint.sh
```

See **Section 6** (domain stats) and **Section 7** (tag clusters):
- Section 6: counts concepts by `domain:` field — alerts when ≥10 exist without a MOC
- Section 7: analyzes tag clusters — suggests potential domains from popular tags

---

## Workflow for Adding a New Domain

1. Ingest ≥10 articles on the same topic → `scan /raw`
2. Run `lint` → Sections 6/7 will suggest a domain if the threshold is met
3. Create `wiki/domains/<domain-name>.md` using the template below
4. Run `index` to rebuild index.md and _brief.md

---

## Template for New Domain

```markdown
---
title: "Domain: <Domain Name>"
tags: [domain, <tag1>, <tag2>]
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

# Domain: <Domain Name>

> Map of Content — entry point for knowledge about <short description>.

## Concepts

<!-- BUILD_INDEX:CONCEPTS_START -->
<!-- BUILD_INDEX:CONCEPTS_END -->

## Topics

| Topic | Description |
|-------|-------------|
| _(none yet)_ | |

## Source Summaries

- [[summaries/<article-slug>]] — <source>, <author> <year>

## Concept Seeds

> For ingest direction only — don't create concepts before you have a source.

- **<Concept A>**: <short description>
- **<Concept B>**: <short description>

## Related Domains

- [[domains/ai]] — <reason for connection>
```

---

## The `domain:` Field in Concept Frontmatter

Every concept file **must** include a `domain:` field in its frontmatter:

```yaml
---
title: "Concept Name"
domain: ai          # ← slug of the domain MOC
tags: [tag1, tag2]
created: YYYY-MM-DD
---
```

**Valid values:**
- Name of an existing domain MOC: `ai`, `product`, `project`, `technology`
- New domain without a MOC yet: use a short slug → `lint` will track it and alert when ≥10 concepts
- Wiki system concepts: `meta`

**Linting**: Section 8 in `lint` will flag concepts that have a `domain:` field but aren't listed in the corresponding domain MOC file.

---

## Cross-Domain Connections

When a concept appears in ≥2 domains → create a **bridge note**:
- Name it after the connection itself: `cognitive-load-in-ux.md`
- Link to both domain MOCs
- Bridge notes are often the most valuable insights in the wiki
- `lint` Section 9 will detect bridge note candidates

---

## Domain Files

| Domain | File | Status |
|--------|------|--------|
| _(none yet — create after ingesting ≥10 concepts per domain)_ | - | ⚪ Awaiting content |

*Auto-updated when running `lint`*

---

## Common Domains by Use Case

For reference only — use domains that fit **your** knowledge, not these:

| Use case | Suggested domains |
|----------|-------------------|
| AI/ML Engineer | AI, Technology, Research Methods |
| Product Manager | Product, Business, Psychology |
| Startup Founder | Product, Business, Leadership, Finance |
| Knowledge Worker | Systems Thinking, Psychology, Philosophy |
| Researcher | Research Methods, Statistics, Domain Specific |
| Writer | Writing, Rhetoric, Psychology, Philosophy |
