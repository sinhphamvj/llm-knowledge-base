#!/usr/bin/env python3
"""Convert PDF, Office, HTML, Images to Markdown using IBM Docling."""
import os
import sys
import shutil
import argparse
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


def _extract_pictures(doc, source_filename, pdf_path=None):
    """Extract pictures from Docling document to raw/images/.

    Strategy: Docling provides bounding boxes for pictures but get_image()
    often returns None. We use PyMuPDF (fitz) to crop images directly
    from the PDF using those bounding boxes.
    """
    ensure_dir(IMAGES_DIR)
    slug = os.path.splitext(source_filename)[0].replace(' ', '-')
    replacements = []

    if not doc.pictures:
        return replacements

    # Try PyMuPDF-based extraction for PDFs
    if pdf_path and pdf_path.lower().endswith('.pdf'):
        try:
            import fitz
            pdf = fitz.open(pdf_path)
            for i, pic in enumerate(doc.pictures):
                if not pic.prov:
                    continue
                try:
                    prov = pic.prov[0]
                    page_no = prov.page_no - 1  # Docling is 1-indexed, fitz is 0-indexed
                    if page_no < 0 or page_no >= len(pdf):
                        continue
                    bbox = prov.bbox
                    page = pdf[page_no]
                    page_height = page.rect.height
                    # Convert BOTTOMLEFT to TOPLEFT coordinates
                    rect = fitz.Rect(bbox.l, page_height - bbox.t, bbox.r, page_height - bbox.b)
                    clip = rect & page.rect
                    if clip.is_empty or clip.width < 10 or clip.height < 10:
                        continue
                    pix = page.get_pixmap(clip=clip, matrix=fitz.Matrix(3, 3))
                    img_filename = f"{slug}-img-{i}.png"
                    img_path = os.path.join(IMAGES_DIR, img_filename)
                    pix.save(img_path)
                    rel_path = f"../../raw/images/{img_filename}"
                    replacements.append((i, rel_path))
                    print(f"   🖼️  Extracted: {img_filename} ({pix.width}x{pix.height})")
                except Exception as e:
                    print(f"   ⚠️  Picture {i}: {e}")
            pdf.close()
            return replacements
        except ImportError:
            pass  # fitz not available, fall through

    # Fallback: try Docling's get_image()
    for i, pic in enumerate(doc.pictures):
        try:
            img = pic.get_image(doc)
            if img is None:
                continue
            img_filename = f"{slug}-img-{i}.png"
            img_path = os.path.join(IMAGES_DIR, img_filename)
            img.save(img_path)
            rel_path = f"../../raw/images/{img_filename}"
            replacements.append((i, rel_path))
            print(f"   🖼️  Extracted: {img_filename} ({img.size[0]}x{img.size[1]})")
        except Exception as e:
            print(f"   ⚠️  Picture {i}: {e}")

    return replacements


def _inject_images_into_markdown(content, replacements):
    """Replace <!-- image --> placeholders with actual image links.

    Docling outputs '<!-- image -->' for each picture. We replace them
    in order with the extracted image paths.
    """
    if not replacements:
        return content

    placeholder = "<!-- image -->"
    parts = content.split(placeholder)
    result = parts[0]
    for idx, part in enumerate(parts[1:], 1):
        # Find matching replacement by index (1-based since split gives parts after each placeholder)
        rep = next((r for r in replacements if r[0] == idx - 1), None)
        if rep:
            result += f"![image]({rep[1]})"
        else:
            result += placeholder
        result += part

    return result


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
        # For PDFs: configure pipeline options
        if ext == 'pdf' and PdfPipelineOptions is not None:
            pipeline_opts = PdfPipelineOptions(
                do_ocr=not no_ocr,
            )
            converter = DocumentConverter(
                format_options={".pdf": PdfFormatOption(pipeline_options=pipeline_opts)}
            )
        else:
            converter = DocumentConverter()
        result = converter.convert(filepath)

        doc = result.document
        content = doc.export_to_markdown()

        # Extract pictures from document and inject into markdown
        replacements = _extract_pictures(doc, filename, pdf_path=filepath)
        if replacements:
            content = _inject_images_into_markdown(content, replacements)

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
