#!/usr/bin/env python3
import os
import sys
import shutil
import argparse
from datetime import datetime

try:
    import pymupdf4llm
except ImportError:
    pymupdf4llm = None
    
try:
    from markitdown import MarkItDown
except ImportError:
    MarkItDown = None

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
RAW_DIR = os.path.join(ROOT, 'raw')
ARCHIVED_DIR = os.path.join(RAW_DIR, 'archived')

SUPPORTED_EXTENSIONS = {
    'pdf': 'pdf',
    'docx': 'markitdown',
    'pptx': 'markitdown',
    'xlsx': 'markitdown'
}

def setup_archived_dir():
    if not os.path.exists(ARCHIVED_DIR):
        os.makedirs(ARCHIVED_DIR, exist_ok=True)

def move_to_archive(filepath):
    setup_archived_dir()
    rel_path = os.path.relpath(filepath, RAW_DIR)
    dest_path = os.path.join(ARCHIVED_DIR, rel_path)
    
    # Create sub-directories in archived/ if needed
    dest_dir = os.path.dirname(dest_path)
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir, exist_ok=True)
    
    # Handle duplicates in archive
    if os.path.exists(dest_path):
        base, ext = os.path.splitext(dest_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest_path = f"{base}_{timestamp}{ext}"
        
    shutil.move(filepath, dest_path)
    return dest_path

def convert_pdf(filepath):
    if pymupdf4llm is None:
        raise Exception("pymupdf4llm is not installed. Run: pip install pymupdf4llm")
    
    # Use page_separators to help Map-Reduce
    md_text = pymupdf4llm.to_markdown(filepath, page_separators=True)
    return md_text

def convert_markitdown(filepath):
    if MarkItDown is None:
        raise Exception("markitdown is not installed. Run: pip install markitdown")
    
    md = MarkItDown()
    result = md.convert(filepath)
    return result.text_content

def process_file(filepath, dry_run=False, keep=False):
    if not os.path.isfile(filepath):
        print(f"❌ File not found: {filepath}")
        return False

    ext = filepath.split('.')[-1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        print(f"⏭️ Skipping {filepath} (unsupported format)")
        return False

    filename = os.path.basename(filepath)
    md_filepath = os.path.splitext(filepath)[0] + '.md'

    if os.path.exists(md_filepath):
        print(f"⚠️ Markdown file already exists for {filename}, skipping.")
        return False

    print(f"⏳ Converting {filename}...")
    if dry_run:
        print(f"   [DRY-RUN] Would convert to {md_filepath}")
        if not keep:
            print(f"   [DRY-RUN] Would move {filename} to archive")
        return True

    try:
        if SUPPORTED_EXTENSIONS[ext] == 'pdf':
            content = convert_pdf(filepath)
        else:
            content = convert_markitdown(filepath)
            
        # Add metadata header
        date_str = datetime.now().strftime("%Y-%m-%d")
        header = f"<!-- Converted from: {filename} | Date: {date_str} -->\n\n"
        final_content = header + content

        with open(md_filepath, 'w', encoding='utf-8') as f:
            f.write(final_content)
            
        print(f"✅ Successfully created: {os.path.basename(md_filepath)}")

        if not keep:
            archive_path = move_to_archive(filepath)
            print(f"📦 Moved original to: {os.path.relpath(archive_path, ROOT)}")
            
        return True
    except Exception as e:
        print(f"❌ Error converting {filename}: {str(e)}")
        return False

def scan_and_convert(dry_run=False, keep=False):
    found_any = False
    for root_dir, dirs, files in os.walk(RAW_DIR):
        # Skip archived dir
        if ARCHIVED_DIR in root_dir:
            continue
            
        for file in files:
            ext = file.split('.')[-1].lower()
            if ext in SUPPORTED_EXTENSIONS:
                found_any = True
                process_file(os.path.join(root_dir, file), dry_run=dry_run, keep=keep)
                
    if not found_any:
        print("No supported files (PDF, DOCX, PPTX, XLSX) found in raw/ to convert.")

def main():
    parser = argparse.ArgumentParser(description="Auto-convert PDF and Office docs to Markdown")
    parser.add_argument("file", nargs="?", help="Specific file to convert")
    parser.add_argument("--scan", action="store_true", help="Scan raw/ folder and convert all supported files")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without actually doing it")
    parser.add_argument("--keep", action="store_true", help="Keep the original file (don't move to archived/)")
    
    args = parser.parse_args()

    if args.file:
        full_path = os.path.abspath(args.file)
        if full_path.startswith(RAW_DIR) and ARCHIVED_DIR in full_path:
             print("⚠️  Warning: Processing a file inside archived/ directory.")
        process_file(full_path, dry_run=args.dry_run, keep=args.keep)
    elif args.scan:
        scan_and_convert(dry_run=args.dry_run, keep=args.keep)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
