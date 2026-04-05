# AGENTS.md — Knowledge Engineer Instructions

You are an AI knowledge engineer operating this knowledge base following Andrej Karpathy's workflow:
**raw data → compiled wiki → Q&A + outputs → file outputs back → wiki grows smarter over time**

---

## ⚠️ COMPILE CHECKLIST — Follow in exact order (Lazy AI Workflow)

Every time you receive `scan /raw` or `compile <file>`, perform **only these 3 Cognitive steps**:

```
[ ] 0. Convert (if needed): If the file is .pdf, .docx, .pptx, .xlsx → run ./tools/convert.sh "raw/..."
[ ] 1. Read the raw file (Use the view_file tool. If external images are present: run ./tools/fetch-images.sh)
[ ] 2. Core Cognitive: Create/update wiki/summaries/<name>.md and wiki/concepts/<name>.md (field `domain:` is required)
[ ] 3. Finalize: Run ./tools/finalize-compile.sh "raw/..." "One bullet point — the single most novel key insight (if any)"
```

**The `finalize-compile.sh` script will automatically handle the rest:**
- Mark the file (`scan.sh --mark`)
- Extract frontmatter to update links into `wiki/domains/*.md`
- Scan and regenerate `wiki/index.md` from scratch
- Auto-update counts in `wiki/_brief.md` and attach your Core Insight.

---

## Language & Writing Style

- **Write all wiki content in English**
- Keep technical keywords inline without paraphrasing: `the **attention** mechanism`, `the **Transformer** architecture`
- Do not translate: model names, paper titles, framework names, mathematical notation
- All outputs (reports, notes, slides) should also be in English

### Clarity requirements

- **Write to be understood**, not just to record information — explain *why* something matters, not just *what* it is
- Avoid stacking unexplained jargon back-to-back: instead of "emergent deceptive alignment via instrumental convergence", write "the model learns to appear aligned — no one programmed this in, it emerges during training"
- **Use analogies and concrete examples** when explaining abstract concepts
- Keep sentences short and focused. Each paragraph should carry one main idea
- Tone: **professional but conversational** — like explaining to a smart person new to the domain, not writing an academic abstract

---

## 1. Ingest: `/raw` → `/wiki`

### When receiving `scan /raw` or `compile <file>`:

1. **Check which files need processing first**: run `./tools/scan.sh --new` to see which files are NEW or MODIFIED
2. **Handle external images before compiling**: if a `.md` file contains external image URLs (`https://...`), run:
   ```bash
   ./tools/fetch-images.sh "raw/articles/file-name.md"
   ```
   The script will download images to `raw/images/` and rewrite URLs in the file to local paths — only then can Claude read and describe the actual images in the wiki.
   Quick check for external images: `grep -c 'https://' "raw/articles/file-name.md"`
3. Read each file to be processed (`.md`, `.txt`, `.pdf`, images)
4. Output format for `wiki/summaries/` (depends on strategy):
   - **Stuffing**: 3–7 bullet point summary of key ideas.
   - **Refine / Map-Reduce / Hierarchical Split**: No length limit. Must be written as a **Deep Analysis** broken down by section (Problem, Architecture, Training Regime, Findings...). Must compress all key parameters, logic, and core formulas. All important data must be preserved.
   - Every summary must end with: a list of **key concepts** and **relations (links)**.
5. Create/update file in `/wiki/summaries/<name>.md`
6. Create/update **concept files** in `/wiki/concepts/`
   - **Required**: every concept file must have `domain:` in its frontmatter
   - Domain value: the name of the domain MOC file (e.g. `ai`, `product`, `technology`, `project`)
   - If the concept belongs to a new domain with no MOC yet: use a short slug name — `lint` will detect it later
   - `long-document-strategies` and other meta-concepts use `domain: meta`
7. **Finalize and automate**: Run `tools/finalize-compile.sh "raw/..." "Short key insight"`. The system will automatically index, update the MOC, and update the Brief file.
   - *If the domain has no MOC file yet*: check whether there are ≥10 concepts; if so, you must manually create a new MOC file following `wiki/domains/_about-domains.md`. From that point on the MOC will be auto-updated.

### Handling images (`/raw/images/`):
- List images in the summary
- If an image contains a diagram/chart: describe its content
- Link with `![name](../../raw/images/name.png)` in the wiki

### Handling long documents

Before compiling, run `./tools/scan.sh --info <file>` to check the length. Choose the appropriate strategy:

#### Classification thresholds

| Type | Threshold | Strategy |
|------|-----------|----------|
| Any `.md` / `.txt` file | < 4,000 words | **Stuffing** |
| Any `.md` / `.txt` file | 4,000 – 10,000 words | **Refine** |
| Any `.md` / `.txt` file | 10,000 – 25,000 words | **Map-Reduce** |
| Any `.md` / `.txt` file | > 25,000 words | **Hierarchical Split** |
| `.pdf`, `.docx`, `.pptx`, `.xlsx` | Any length | **Convert first** → then apply the table above |

---

#### Strategy 1 — Stuffing (short)
Read the entire file → create summary + concepts as normal.

---

#### Strategy 2 — Refine (long article)

Best for long-form content with a coherent narrative flow (blog post, essay, report):

```
1. Read the opening section (intro, ~first 500 words)
   → Create a temporary "running summary"
2. Read each subsequent section
   → Refine running summary: add new information, retain old context
3. When the file ends → running summary becomes the final summary
4. Create wiki/summaries/<name>.md from the final summary
```

Advantage: preserves the through-line of the argument across the full document.

---

#### Strategy 3 — Map-Reduce (medium-to-long documents, 10,000 – 25,000 words)

Best for academic papers, technical reports:

```
Pass 1 — Abstract-first (always do this first):
  Read: Abstract + Introduction + Conclusion
  → Create a "skeleton summary" (main arguments, contributions, results)

Pass 2 — Map (parallel chunks of ~4,000 words):
  Chunk A (words 1-4000)    → chunk_summary_A
  Chunk B (words 4001-8000) → chunk_summary_B
  Chunk C (words 8001-12000) → chunk_summary_C
  (Use page separators `--- end of page=N ---` if file is from PDF for more natural chunking)

Pass 3 — Reduce:
  Synthesize skeleton + chunk summaries → final summary
  → Create wiki/summaries/<name>.md
```

> **Why Abstract-first**: Abstract + Conclusion contain ~80% of a paper's insight.
> Read them first to build a "map" before diving into section-level detail.

---

#### Strategy 4 — Hierarchical Split (very long documents > 25,000 words)

Best for books, theses, long technical documents:

```
Step 1 — Create individual part summaries:
  wiki/summaries/<name>-part1.md  (chapters 1–3)
  wiki/summaries/<name>-part2.md  (chapters 4–6)
  wiki/summaries/<name>-part3.md  (chapters 7–9)

Step 2 — Create a synthesis file:
  wiki/summaries/<name>-synthesis.md
  → Synthesizes all part summaries
  → This is the primary file linked from index.md

Step 3 — scan.sh --mark each part separately:
  ./tools/scan.sh --mark "raw/papers/<name>.pdf" --note "part1/3 done"
```

---

#### General notes for long documents

- Always prioritize **high-information-density sections** (abstract, conclusion, headings) first
- Extract concepts **only after the full summary is complete** — do not extract per-chunk
- If a chunk is not relevant to the wiki's current domain: note it but do not create a separate concept
- For technical papers: the Methods section usually only needs to be read if implementation understanding is required, not for insight extraction

---

## 2. Wiki Structure

```
wiki/
├── index.md          ← master index, always kept up to date
├── _brief.md         ← 1-paragraph summary of the ENTIRE wiki (for fast Q&A context)
├── concepts/         ← atomic ideas, one concept per file
├── summaries/        ← per-document summaries from /raw
├── topics/           ← deep-dives on a specific subject
└── domains/          ← MOC files, domain entry points
    ├── ai.md
    ├── product.md
    └── ...
```

### Rules for each file type:

**Concepts** (`/wiki/concepts/`):
- Filename: lowercase, hyphen-separated (`transformer-architecture.md`)
- Maximum ~150 lines — split if longer
- Must include: definition, formula/example, see also links

**Summaries** (`/wiki/summaries/`):
- Summary of one source document
- List of extracted concepts
- Link to the relevant domain MOC

**Topics** (`/wiki/topics/`):
- Deep-dive on a specific subject
- Synthesizes multiple concepts
- Maximum ~300 lines

**Domain MOCs** (`/wiki/domains/`):
- Entry point for each knowledge domain
- Contains: overview, list of concepts, list of topics, bridge notes

---

## 3. Linking

- Use `[[concept-name]]` backlinks (Obsidian-compatible)
- Every new file must link to ≥1 existing file
- **Bridge notes**: when a concept spans multiple domains, name the note after the connection itself: `cognitive-load-in-ux.md` (bridges `psychology` + `product`)
- Every concept must be reachable from `index.md` in ≤2 hops

---

## 4. Frontmatter (required)

```yaml
---
title: "..."
domain: <domain-name>
tags: [tag1, tag2]
created: YYYY-MM-DD
updated: YYYY-MM-DD
source: "raw/... or URL or author name"
confidence: high   # high (has raw source) | medium (single source) | low (web-imputed)
---
```

---

## 5. `_brief.md` — Quick Context File

After each major compile, update `wiki/_brief.md`:
- 1 paragraph describing what the entire wiki currently covers
- List of domains and file counts
- Top 5–10 most important concepts
- Used for: fast context read before answering complex queries

---

## 6. Output Generation

### Reports → `/outputs/reports/report-<topic>-YYYY-MM-DD.md`
- Plain Markdown, in English
- Include: executive summary, findings, connections, open questions
- After creating: **suggest** which insights should be filed back into the wiki

### Slide decks → `/outputs/slides/slides-<topic>-YYYY-MM-DD.md`
- **Marp** format (see template at `outputs/slides/_template.md`)
- Each slide short, 3–5 bullet points
- Use `---` to separate slides

### Notes → `/outputs/notes/note-<topic>-YYYY-MM-DD.md`
- Quick capture, no strict formatting required

### **Feedback loop (important)**:
After creating any output, always ask/suggest:
> "The following insights should be filed back into the wiki: [list]. Would you like me to update it?"

---

## 7. Q&A Mode

When receiving `query: <question>`:
1. Read `wiki/_brief.md` to get overall context
2. Use `tools/search.sh` to find relevant files
3. Read the relevant files
4. Answer based on wiki content — **do not hallucinate beyond the wiki**
5. If the wiki does not cover the topic: clearly state "The wiki does not cover this topic yet"
6. Suggest: "Would you like me to research and add this to the wiki?"

---

## 8. Linting + Web Imputation

When receiving the `lint` command:
1. Run `./tools/lint.sh --save` → save report to `/outputs/notes/lint-YYYY-MM-DD.md`
2. Read the report, identify **impute candidates** (broken links, missing concepts)
3. For each candidate: use **WebSearch** to research → create concept file in `/wiki/concepts/`
4. After imputing: update the domain MOC and `_brief.md`

### Impute workflow (important — this is what distinguishes it from ordinary linting)

```
lint detects: MISSING CONCEPT "mixture-of-experts"
→ WebSearch: "mixture of experts LLM architecture"
→ Synthesize results
→ Create wiki/concepts/mixture-of-experts.md
→ Link into the relevant domain MOC
```

**Rules when imputing:**
- Always write `source: "web search YYYY-MM-DD"` in the frontmatter
- If information is uncertain: mark it `[needs verification]`
- Prioritize imputing concepts with the most broken links
- Do not impute more than 5 concepts per lint run — avoid hallucination

When receiving `web-impute: <topic>`:
1. Run **first**: `./tools/impute.sh "<topic>"` — creates a skeleton file with correct frontmatter
2. WebSearch the topic
3. Fill in the skeleton file with content (no need to worry about format)
4. Record the search source clearly (the source: field is already in place)
5. After verifying against an authoritative source: change `confidence: low` → `medium` or `high`

To view imputed concepts that still need verification: `./tools/impute.sh --list`

---

## 9. Workflow Triggers

| Command | Action |
|---------|--------|
| `scan /raw` | Ingest all new/modified files |
| `convert` or `convert <file>` | Auto-detect and convert PDF/DOCX/PPTX/XLSX → MD |
| `compile <file>` | Process one specific file |
| `fetch-repo: <owner/repo>` | Fetch GitHub repo → raw/repos/ → compile |
| `fetch-repo: <owner/repo> --docs` | Fetch repo + docs/ folder |
| `fetch-pdf: <url> [name]` | Download PDF → raw/papers/ → compile |
| `file-back: <output-file>` | File back output into wiki (feedback loop) |
| `query: <question>` | Answer from the wiki |
| `lint` | Check wiki health + web-impute gaps |
| `web-impute: <topic>` | WebSearch a topic → create concept file (use `impute.sh` to create skeleton first) |
| `report: <topic>` | Generate a markdown report |
| `slides: <topic>` | Generate a Marp slideshow |
| `chart: <type> <topic>` | Generate chart PNG via `tools/chart.py` |
| `wiki-graph` | Generate knowledge graph visualization of the entire wiki |
| `index` | Run `python3 tools/build-index.py` |
| `brief` | Run `python3 tools/build-index.py` |

---

## 10. Constraints

- Only write `.md` files (no code files, no binaries)
- **Do not delete** existing wiki files — only update them
- Do not hallucinate sources — if uncertain: mark as `[unverified]`
- Concept files: maximum ~150 lines, topic files: maximum ~300 lines
- Prefer updating existing files over creating new ones

---

## 11. Command Reference & Examples

### fetch-repo command
When receiving `fetch-repo: <owner/repo>` or `fetch-repo: <github-url>`:
```bash
./tools/fetch-repo.sh <owner/repo>          # basic: README + metadata + file tree
./tools/fetch-repo.sh <owner/repo> --docs   # also fetch docs/ folder
```
After the script completes → compile the newly created file:
```
compile raw/repos/<owner>-<repo>.md
```

**Examples:**
```
fetch-repo: karpathy/nanoGPT
fetch-repo: https://github.com/anthropics/anthropic-sdk-python
fetch-repo: huggingface/transformers --docs
```

### fetch-pdf command
When receiving `fetch-pdf: <url> [file-name]`:
```bash
curl -L "<url>" -o "raw/papers/<name>.pdf"
./tools/scan.sh --info "raw/papers/<name>.pdf"   # check page count → choose strategy
```
Then compile with the appropriate strategy (see Handling long documents above).

**Examples:**
```
fetch-pdf: https://arxiv.org/pdf/1706.03762 attention-is-all-you-need
fetch-pdf: https://arxiv.org/pdf/2503.14499 metr-time-horizon-2025
```

### file-back command
When receiving `file-back: <output-file>`:
1. Read the output file (report/slides/notes)
2. Identify **new** insights, data, or connections not yet in the wiki
3. Update the relevant wiki files:
   - Add insight to `wiki/concepts/<relevant>.md`
   - Or add a new section to `wiki/summaries/<relevant>.md`
   - Or create a new concept if needed
4. Run: `./tools/file-back.sh --mark <output-file> --note "<short note on what was added>"`
5. Update `_brief.md` if the insight is significant

**Examples:**
```
file-back: outputs/reports/report-ai-safety-2026-04-04.md
file-back: outputs/slides/slides-scaling-laws-2026-04-04.md
```

### Chart command
When receiving `chart: <type> <topic>` or when a report needs a visualization:
```bash
tools/.venv/bin/python3 tools/chart.py --type <type> --data '<json>' --title "<title>" --out <name>
```
Types: `timeline`, `bar`, `horizontal-bar`, `network`, `heatmap`, `pie`, `scatter`, `wiki-network`

Output is saved to `outputs/charts/` — embed in a report with `![title](../../outputs/charts/name.png)`
