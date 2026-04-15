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
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import PdfFormatOption
except ImportError:
    DocumentConverter = None
    PdfPipelineOptions = None
    PdfFormatOption = None

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


def _extract_embedded_images(content, source_filename):
    """Extract base64-encoded images from docling markdown output to raw/images/."""
    import base64

    ensure_dir(IMAGES_DIR)

    # Match ![alt](data:image/png;base64,...) patterns
    pattern = r'!\[([^\]]*)\]\(data:image/([^;]+);base64,([^)]+)\)'
    counter = 0

    def replace_match(match):
        nonlocal counter
        counter += 1
        alt_text = match.group(1) or "image"
        img_format = match.group(2)  # png, jpeg, etc.
        b64_data = match.group(3)

        slug = os.path.splitext(source_filename)[0].replace(' ', '-')
        img_filename = f"{slug}-img-{counter}.{img_format}"
        img_path = os.path.join(IMAGES_DIR, img_filename)

        try:
            img_bytes = base64.b64decode(b64_data)
            with open(img_path, 'wb') as f:
                f.write(img_bytes)
            # Relative path from the .md file location to raw/images/
            return f'![{alt_text}](../../raw/images/{img_filename})'
        except Exception:
            return match.group(0)  # Keep original if extraction fails

    return re.sub(pattern, replace_match, content)


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
        if no_ocr and PdfPipelineOptions is not None:
            pipeline_opts = PdfPipelineOptions(do_ocr=False)
            converter = DocumentConverter(
                format_options={".pdf": PdfFormatOption(pipeline_options=pipeline_opts)}
            )
        else:
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
