# Docling Integration Design

> Replace pymupdf4llm + markitdown with IBM Docling as the document conversion backend.

## Context

The knowledge base currently uses two lightweight libraries for document conversion:
- `pymupdf4llm` for PDF → Markdown
- `markitdown` for DOCX/PPTX/XLSX → Markdown

Both have significant limitations:
- No OCR support for scanned PDFs
- No table structure extraction from PDFs
- No image extraction from PDFs
- Limited format support (4 formats only)

Docling (IBM Research, v2.88.0) already exists at `/home/sinh/Documents/docling` and provides all of these plus many more formats via a unified Python API.

## Decision

- **Approach**: Rewrite `convert-docs.py` using Docling Python API (not CLI)
- **Scope**: Full pipeline update — convert layer + scan + AGENTS.md
- **Installation**: Install into existing `tools/.venv`
- **Pipeline**: Standard pipeline only (no VLM)

## Format Support

### Before (4 formats)

| Extension | Backend |
|-----------|---------|
| `.pdf` | pymupdf4llm |
| `.docx` | markitdown |
| `.pptx` | markitdown |
| `.xlsx` | markitdown |

### After (10+ formats)

| Extension | Docling Backend | Notes |
|-----------|----------------|-------|
| `.pdf` | StandardPdfPipeline | OCR + tables + image extraction |
| `.docx`, `.dotx`, `.docm` | MsWordDocumentBackend | |
| `.pptx`, `.potx`, `.ppsx` | MsPowerpointDocumentBackend | |
| `.xlsx`, `.xlsm` | MsExcelDocumentBackend | |
| `.html`, `.htm` | HTMLDocumentBackend | NEW |
| `.jpg`, `.jpeg`, `.png`, `.tif`, `.tiff`, `.webp` | ImageDocumentBackend + OCR | NEW |
| `.csv` | CsvDocumentBackend | NEW |

## Architecture

```
convert.sh (wrapper, minimal changes)
    └── convert-docs.py (rewritten, ~200 lines)
            │
            ├── DocumentConverter (docling API)
            │     ├── StandardPdfPipeline (PDF + images with OCR/tables)
            │     └── SimplePipeline (everything else)
            │
            ├── Image extraction → raw/images/
            └── Output: .md file alongside original
```

## Changes by File

### 1. `tools/convert-docs.py` — Full rewrite

**Entry point**: `DocumentConverter` from docling.

**Core logic** (`process_file`):
1. Detect file extension → map to docling `InputFormat`
2. For PDF: configure `PdfPipelineOptions` with:
   - `do_ocr = True` (enable OCR for scanned docs)
   - Table structure extraction enabled
   - Image extraction mode = referenced
3. Call `converter.convert(filepath)`
4. Export to Markdown: `result.document.export_to_markdown()`
5. Extract images from the conversion result → save to `raw/images/`
6. Rewrite image paths in the Markdown to `../../raw/images/<name>.png`
7. Write `.md` file with metadata header
8. Archive original to `raw/archived/` (unless `--keep`)

**CLI arguments** (unchanged interface):
- Positional `file` — convert a specific file
- `--scan` — batch convert all files in `raw/`
- `--dry-run` — preview without converting
- `--keep` — don't archive original
- NEW: `--no-ocr` — disable OCR for faster PDF conversion

### 2. `tools/convert.sh` — Minimal update

- Update install hint from `pip install pymupdf4llm markitdown` to `pip install docling`
- No structural changes

### 3. `tools/scan.sh` — Update `_all_raw()`

Add new extensions to the search pattern:
```bash
# Before: *.md *.txt *.pdf *.docx *.pptx *.xlsx
# After:  *.md *.txt *.pdf *.docx *.pptx *.xlsx *.html *.htm *.jpg *.jpeg *.png *.tif *.tiff *.webp *.csv
```

### 4. `requirements.txt` — Replace dependencies

```
Remove: pymupdf4llm>=0.0.17, markitdown>=0.0.1
Add:    docling>=2.0.0
```

Keep all other dependencies unchanged (matplotlib, networkx, tiktoken).

### 5. `AGENTS.md` — Update documentation

- Section "Handling long documents": add HTML/IMG/CSV to conversion table
- Section "Step 2: Convert": note docling as backend, mention OCR capability
- Section "Handling images": update to reflect docling's image extraction from PDFs
- Compile checklist Step 2: mention new supported formats

### 6. `CLAUDE.md` — Update CLI reference

- Update the `convert` command description to mention new formats

## Image Extraction Design

Docling's `DoclingDocument` contains picture elements with image data. Flow:

1. After conversion, iterate `result.document.pictures`
2. For each picture, save to `raw/images/<doc-slug>-img-<N>.png`
3. In the exported Markdown, images will be referenced — rewrite paths to `../../raw/images/<name>.png`

If docling does not expose extracted images via the API, fall back to generating page-level images only for pages that contain pictures.

## Error Handling

- **Per-file failure**: catch exceptions, log warning, continue to next file (batch mode)
- **Missing docling**: detect ImportError, print install instructions
- **Timeout**: configure `document_timeout` in PdfPipelineOptions (default 300s)
- **Unsupported format**: skip with warning (not error)

## Migration

1. Install docling into `tools/.venv`: `pip install docling`
2. Replace `convert-docs.py` with new version
3. Update `convert.sh`, `scan.sh`, `requirements.txt`
4. Update `AGENTS.md`, `CLAUDE.md`
5. Test with existing files in `raw/`

No migration needed for already-converted files — the `.md` outputs and `raw/archived/` structure remain identical.

## Risks

- **Size**: docling + torch is ~2GB. User has accepted this.
- **First-run latency**: docling downloads ML models on first use (~500MB). This is a one-time cost.
- **Memory**: PDF conversion with OCR uses more RAM than pymupdf4llm. Acceptable for a desktop tool.
- **Compatibility**: docling requires Python >=3.10. The venv should already satisfy this.
