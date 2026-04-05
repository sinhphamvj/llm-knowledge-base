---
title: "Dataview Examples"
tags: [meta, dataview]
created: 2026-01-01
updated: 2026-01-01
---

# Dataview Query Examples

> Open this file in Obsidian to see live query results.
> Requires the **Dataview** plugin to be installed and enabled.

---

## All Summaries (newest first)

```dataview
TABLE source, created
FROM "wiki/summaries"
WHERE file.name != "_template"
SORT created DESC
```

---

## Concepts by Domain

```dataview
TABLE tags, created
FROM "wiki/concepts"
SORT file.name ASC
```

---

## Concepts about AI Safety

```dataview
LIST
FROM "wiki/concepts"
WHERE contains(tags, "ai-safety") OR contains(tags, "alignment")
SORT file.name ASC
```

---

## All Generated Outputs

```dataview
TABLE file.folder AS "Type", created
FROM "outputs"
WHERE file.name != "_template"
SORT created DESC
```

---

## Wiki Health — Files missing tags

```dataview
LIST
FROM "wiki"
WHERE !tags
```
