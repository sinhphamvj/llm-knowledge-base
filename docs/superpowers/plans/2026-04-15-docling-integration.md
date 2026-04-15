# Docling Integration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace pymupdf4llm + markitdown with IBM Docling as the unified document conversion backend.

**Architecture:** Rewrite `convert-docs.py` to use Docling's Python API (`DocumentConverter`). Docling handles all format detection, OCR, table extraction, and image extraction internally. The rest of the pipeline (convert.sh wrapper, scan.sh tracking, finalize-compile.sh) stays the same — only format support lists are extended.

**Tech Stack:** Python 3.10+, docling >=2.0.0, PyTorch (CPU)

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `tools/convert-docs.py` | **Rewrite** | Core conversion engine using Docling API |
| `tools/convert.sh` | **Edit** | Update install hint |
| `tools/scan.sh` | **Edit** | Extend `_all_raw()` with new extensions |
| `requirements.txt` | **Edit** | Replace old deps with docling |
| `AGENTS.md` | **Edit** | Update format lists, convert step docs |
| `CLAUDE.md` | **Edit** | Update CLI quick reference |

---

### Task 1: Update requirements.txt

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Replace conversion dependencies**

Replace lines 4-5:

```diff
- # Used by tools/convert-docs.py (converting PDF, Office to Markdown)
- pymupdf4llm>=0.0.17
- markitdown>=0.0.1
+ # Used by tools/convert-docs.py (converting PDF, Office, HTML, Images to Markdown)
+ docling>=2.0.0
```

- [ ] **Step 2: Install docling into venv**

```bash
source tools/.venv/bin/activate && pip install docling
```

Expected: docling + torch (CPU) installed. First run downloads ML models (~500MB).

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "chore: replace pymupdf4llm/markitdown with docling in requirements"
```

---

### Task 2: Rewrite convert-docs.py

**Files:**
- Rewrite: `tools/convert-docs.py`

- [ ] **Step 1: Write the new convert-docs.py**

Replace the entire file with:

```python
#!/usr/bin/env python3
"""Convert PDF, Office, HTML, Images to Markdown using IBM Docling."""
import os
import sys
import shutil
import argparse
import re
from datetime import datetime

try:
    from docling.document_converter import DocumentConverter
except ImportError:
    DocumentConverter = None

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
RAW_DIR = os.path.join(ROOT, 'raw')
IMAGES_DIR = os.path.join(RAW_DIR, 'images')
ARCHIVED_DIR = os.path.join(RAW_DIR, 'archived')

# All formats Docling supports that we want to convert
SUPPORTED_EXTENSIONS = {
    # PDF
    'pdf',
    # Word
    'docx', 'dotx', 'docm',
    # PowerPoint
    'pptx', 'potx', 'ppsx',
    # Excel
    'xlsx', 'xlsm',
    # HTML
    'html', 'htm',
    # Images (OCR)
    'jpg', 'jpeg', 'png', 'tif', 'tiff', 'webp',
    # CSV
    'csv',
}


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def move_to_archive(filepath):
    ensure_dir(ARCHIVED_DIR)
    rel_path = os.path.relpath(filepath, RAW_DIR)
    dest_path = os.path.join(ARCHIVED_DIR, rel_path)

    dest_dir = os.path.dirname(dest_path)
    if dest_dir:
        ensure_dir(dest_dir)

    if os.path.exists(dest_path):
        base, ext = os.path.splitext(dest_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest_path = f"{base}_{timestamp}{ext}"

    shutil.move(filepath, dest_path)
    return dest_path


def process_file(filepath, dry_run=False, keep=False, no_ocr=False):
    if DocumentConverter is None:
        print("❌ docling is not installed. Run: pip install docling")
        return False

    if not os.path.isfile(filepath):
        print(f"❌ File not found: {filepath}")
        return False

    ext = os.path.splitext(filepath)[1].lstrip('.').lower()
    if ext not in SUPPORTED_EXTENSIONS:
        print(f"⏭️  Skipping {os.path.basename(filepath)} (unsupported format: .{ext})")
        return False

    filename = os.path.basename(filepath)
    md_filepath = os.path.splitext(filepath)[0] + '.md'

    if os.path.exists(md_filepath):
        print(f"⚠️  Markdown already exists for {filename}, skipping.")
        return False

    print(f"⏳ Converting {filename}...")
    if dry_run:
        print(f"   [DRY-RUN] Would convert to {md_filepath}")
        if not keep:
            print(f"   [DRY-RUN] Would move {filename} to archive")
        return True

    try:
        converter = DocumentConverter()
        result = converter.convert(filepath)

        # Export to markdown
        content = result.document.export_to_markdown()

        # Handle extracted images from PDFs
        # Docling embeds images as base64 in markdown; extract them to raw/images/
        content = _extract_embedded_images(content, filename)

        # Add metadata header
        date_str = datetime.now().strftime("%Y-%m-%d")
        header = f"<!-- Converted from: {filename} | Date: {date_str} | Backend: docling -->\n\n"
        final_content = header + content

        with open(md_filepath, 'w', encoding='utf-8') as f:
            f.write(final_content)

        print(f"✅ Created: {os.path.basename(md_filepath)}")

        if not keep:
            archive_path = move_to_archive(filepath)
            print(f"📦 Archived: {os.path.relpath(archive_path, ROOT)}")

        return True

    except Exception as e:
        print(f"❌ Error converting {filename}: {e}")
        return False


def _extract_embedded_images(content, source_filename):
    """Extract base64-encoded images from docling markdown output to raw/images/."""
    import base64

    ensure_dir(IMAGES_DIR)

    # Match ![alt](data:image/png;base64,...) patterns
    pattern = r'!\[([^\]]*)\]\(data:image/([^;]+);base64,([^)]+)\)'

    def replace_match(match):
        nonlocal_idx = getattr(replace_match, '_counter', 0) + 1
        setattr(replace_match, '_counter', nonlocal_idx)
        alt_text = match.group(1) or "image"
        img_format = match.group(2)  # png, jpeg, etc.
        b64_data = match.group(3)

        slug = os.path.splitext(source_filename)[0].replace(' ', '-')
        img_filename = f"{slug}-img-{nonlocal_idx}.{img_format}"
        img_path = os.path.join(IMAGES_DIR, img_filename)

        try:
            img_bytes = base64.b64decode(b64_data)
            with open(img_path, 'wb') as f:
                f.write(img_bytes)
            # Relative path from the .md file location to raw/images/
            return f'![{alt_text}](../../raw/images/{img_filename})'
        except Exception:
            return match.group(0)  # Keep original if extraction fails

    # Reset counter
    setattr(replace_match, '_counter', 0)
    return re.sub(pattern, replace_match, content)


def scan_and_convert(dry_run=False, keep=False, no_ocr=False):
    found_any = False
    for root_dir, dirs, files in os.walk(RAW_DIR):
        if ARCHIVED_DIR in root_dir:
            continue

        for file in files:
            ext = os.path.splitext(file)[1].lstrip('.').lower()
            if ext in SUPPORTED_EXTENSIONS:
                found_any = True
                process_file(
                    os.path.join(root_dir, file),
                    dry_run=dry_run, keep=keep, no_ocr=no_ocr
                )

    if not found_any:
        print("No supported files found in raw/ to convert.")


def main():
    parser = argparse.ArgumentParser(
        description="Convert documents to Markdown using Docling"
    )
    parser.add_argument("file", nargs="?", help="Specific file to convert")
    parser.add_argument("--scan", action="store_true", help="Scan raw/ and convert all")
    parser.add_argument("--dry-run", action="store_true", help="Preview without converting")
    parser.add_argument("--keep", action="store_true", help="Keep original file (don't archive)")
    parser.add_argument("--no-ocr", action="store_true", help="Disable OCR (faster for text PDFs)")

    args = parser.parse_args()

    if args.file:
        full_path = os.path.abspath(args.file)
        if full_path.startswith(RAW_DIR) and ARCHIVED_DIR in full_path:
            print("⚠️  Warning: Processing a file inside archived/ directory.")
        process_file(full_path, dry_run=args.dry_run, keep=args.keep, no_ocr=args.no_ocr)
    elif args.scan:
        scan_and_convert(dry_run=args.dry_run, keep=args.keep, no_ocr=args.no_ocr)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Make it executable**

```bash
chmod +x tools/convert-docs.py
```

- [ ] **Step 3: Test with a dry-run**

```bash
./tools/convert.sh --dry-run
```

Expected: Lists files that would be converted, no errors about missing pymupdf4llm.

- [ ] **Step 4: Commit**

```bash
git add tools/convert-docs.py
git commit -m "feat: rewrite convert-docs.py to use docling as backend

Replaces pymupdf4llm + markitdown with IBM Docling for document
conversion. Adds support for HTML, images (OCR), and CSV formats.
Extracts embedded images from PDFs to raw/images/."
```

---

### Task 3: Update convert.sh

**Files:**
- Modify: `tools/convert.sh:19`

- [ ] **Step 1: Update install hint and flag forwarding**

Edit `tools/convert.sh` — change the venv check error message and add `--no-ocr` to flag list:

```diff
- echo "   Please run: python3 -m venv tools/.venv && source tools/.venv/bin/activate && pip install pymupdf4llm markitdown"
+ echo "   Please run: python3 -m venv tools/.venv && source tools/.venv/bin/activate && pip install docling"
```

```diff
- if [[ "$1" == "--dry-run" || "$1" == "--keep" || "$1" == "--scan" ]]; then
+ if [[ "$1" == "--dry-run" || "$1" == "--keep" || "$1" == "--scan" || "$1" == "--no-ocr" ]]; then
```

Also update the comment header:

```diff
- #   ./tools/convert.sh                        # scan entire raw/ for pdf/docx/pptx/xlsx and convert
+ #   ./tools/convert.sh                        # scan entire raw/ and convert all supported formats
```

- [ ] **Step 2: Commit**

```bash
git add tools/convert.sh
git commit -m "chore: update convert.sh for docling backend"
```

---

### Task 4: Update scan.sh

**Files:**
- Modify: `tools/scan.sh:28-29` — `_all_raw()` function
- Modify: `tools/scan.sh:60-61` — `--new` section binary format warning
- Modify: `tools/scan.sh:68-69` — `--new` section binary format warning (modified)
- Modify: `tools/scan.sh:244-249` — `--info` section format case

- [ ] **Step 1: Extend _all_raw() to find new formats**

Replace line 28-29:

```diff
- find "$RAW" -type f \( -name "*.md" -o -name "*.txt" -o -name "*.pdf" -o -name "*.docx" -o -name "*.pptx" -o -name "*.xlsx" \) \
+ find "$RAW" -type f \( -name "*.md" -o -name "*.txt" -o -name "*.pdf" \
+   -o -name "*.docx" -o -name "*.pptx" -o -name "*.xlsx" \
+   -o -name "*.html" -o -name "*.htm" \
+   -o -name "*.jpg" -o -name "*.jpeg" -o -name "*.png" -o -name "*.tif" -o -name "*.tiff" -o -name "*.webp" \
+   -o -name "*.csv" \) \
```

- [ ] **Step 2: Update binary format warnings in --new section**

Replace the regex on lines 60 and 68:

```diff
- if [[ "$rel" =~ \.(pdf|docx|pptx|xlsx)$ ]]; then
+ if [[ "$rel" =~ \.(pdf|docx|pptx|xlsx|html|htm|jpg|jpeg|png|tif|tiff|webp|csv)$ ]]; then
```

(Do this replacement for both occurrences — lines 60 and 68.)

- [ ] **Step 3: Update --info format detection**

Replace lines 244-249:

```diff
  case "$ext_lower" in
-   pdf|docx|pptx|xlsx)
-     echo "Type       : $ext_lower (Binary/Office Format)"
+   pdf|docx|dotx|docm|pptx|potx|ppsx|xlsx|xlsm)
+     echo "Type       : $ext_lower (Binary/Office Format)"
+     echo "Strategy   : ⚠️ CONVERT FIRST (run: ./tools/convert.sh)"
+     echo "  → After converting to .md, use AI to read using the Text/Markdown file thresholds."
+     ;;
+   html|htm)
+     echo "Type       : $ext_lower (HTML)"
+     echo "Strategy   : ⚠️ CONVERT FIRST (run: ./tools/convert.sh)"
+     echo "  → After converting to .md, use AI to read using the Text/Markdown file thresholds."
+     ;;
+   jpg|jpeg|png|tif|tiff|webp)
+     echo "Type       : $ext_lower (Image — will run OCR)"
+     echo "Strategy   : ⚠️ CONVERT FIRST (run: ./tools/convert.sh)"
+     echo "  → After converting to .md, use AI to read using the Text/Markdown file thresholds."
+     ;;
+   csv)
+     echo "Type       : $ext_lower (CSV)"
      echo "Strategy   : ⚠️ CONVERT FIRST (run: ./tools/convert.sh)"
      echo "  → After converting to .md, use AI to read using the Text/Markdown file thresholds."
```

- [ ] **Step 4: Commit**

```bash
git add tools/scan.sh
git commit -m "feat: extend scan.sh to recognize HTML, images, CSV formats"
```

---

### Task 5: Update AGENTS.md

**Files:**
- Modify: `AGENTS.md`

- [ ] **Step 1: Update compile checklist Step 2**

Find the line with `convert.sh` in the compile checklist and update the note:

```diff
  [ ] 2. Convert (if needed): If the file is .pdf, .docx, .pptx, .xlsx → run `./tools/convert.sh "raw/..."`
+ → Now also supports: .html, .htm, .jpg, .png, .tif, .webp, .csv
+ Uses IBM Docling backend with OCR support for scanned PDFs and images.
```

- [ ] **Step 2: Update the conversion table in "Handling long documents"**

Replace the last row of the classification table:

```diff
- | `.pdf`, `.docx`, `.pptx`, `.xlsx` | Any length | **Convert first** → then apply the table above |
+ | `.pdf`, `.docx`, `.pptx`, `.xlsx`, `.html`, `.jpg`, `.png`, `.csv` | Any length | **Convert first** → then apply the table above |
```

- [ ] **Step 3: Update the "Handling images" section**

Add note about docling's built-in image extraction:

After the existing "Handling images" section, add:

```markdown
> **Note**: Docling automatically extracts embedded images from PDFs and saves them to `raw/images/`.
> The conversion script handles this — no manual `fetch-images.sh` needed for PDF-internal images.
> `fetch-images.sh` is still needed for external image URLs in `.md` files.
```

- [ ] **Step 4: Commit**

```bash
git add AGENTS.md
git commit -m "docs: update AGENTS.md for docling backend with new formats"
```

---

### Task 6: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md:48-50`

- [ ] **Step 1: Update the Convert section in CLI quick reference**

```diff
- # Convert
- ./tools/convert.sh                           # auto-convert all PDF/DOCX/PPTX/XLSX in raw/
- ./tools/convert.sh raw/papers/foo.pdf        # convert a specific file
- ./tools/convert.sh --dry-run                 # preview, no conversion
+ # Convert (Docling backend: PDF, Office, HTML, Images, CSV)
+ ./tools/convert.sh                           # auto-convert all supported formats in raw/
+ ./tools/convert.sh raw/papers/foo.pdf        # convert a specific file
+ ./tools/convert.sh --dry-run                 # preview, no conversion
+ ./tools/convert.sh --no-ocr                  # convert without OCR (faster)
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md convert section for docling"
```

---

### Task 7: Smoke test

**Files:** None — verification only.

- [ ] **Step 1: Verify scan.sh detects new formats**

```bash
# Create a dummy test file
touch raw/articles/test-sample.html
./tools/scan.sh --new | grep test-sample
```

Expected: Shows `[NEW] raw/articles/test-sample.html`

Cleanup: `rm raw/articles/test-sample.html`

- [ ] **Step 2: Verify convert.sh --dry-run works**

```bash
./tools/convert.sh --dry-run
```

Expected: No import errors, shows what would be converted.

- [ ] **Step 3: Verify convert-docs.py help**

```bash
tools/.venv/bin/python3 tools/convert-docs.py --help
```

Expected: Shows `--no-ocr` flag, docling in description.

- [ ] **Step 4: Final commit (if any fixes needed)**

```bash
git add -A
git commit -m "fix: address smoke test findings"
```
