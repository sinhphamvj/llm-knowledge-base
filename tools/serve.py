#!/usr/bin/env python3
"""
serve.py — Local server for the Search Web UI
Reads wiki/ and serves the index over HTTP for search-ui.html

Usage:
  python3 tools/serve.py          # http://localhost:7337
  python3 tools/serve.py --port 8080
"""

import argparse
import json
import os
import re
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).parent.parent
WIKI = ROOT / "wiki"
UI_FILE = ROOT / "tools" / "search-ui.html"
PORT = 7337

def build_index() -> list:
    """Read all wiki .md files, extract title/tags/content"""
    index = []
    frontmatter_re = re.compile(r'^---\n(.*?)\n---\n', re.DOTALL)
    tag_re = re.compile(r'^tags:\s*\[([^\]]+)\]|^tags:\n((?:  - .+\n)+)', re.MULTILINE)

    for md_file in sorted(WIKI.rglob("*.md")):
        rel = str(md_file.relative_to(ROOT))
        text = md_file.read_text(errors="ignore")

        # Extract frontmatter
        title = md_file.stem.replace("-", " ").title()
        tags = []
        fm_match = frontmatter_re.match(text)
        if fm_match:
            fm = fm_match.group(1)
            t = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', fm, re.MULTILINE)
            if t:
                title = t.group(1).strip('"\'')
            tg_inline = re.search(r'^tags:\s*\[([^\]]+)\]', fm, re.MULTILINE)
            tg_block = re.search(r'^tags:\n((?:  - .+\n?)+)', fm, re.MULTILINE)
            if tg_inline:
                tags = [x.strip().strip('"\'') for x in tg_inline.group(1).split(',')]
            elif tg_block:
                tags = [x.strip().lstrip('- ').strip('"\'') for x in tg_block.group(1).strip().split('\n')]

        # Strip frontmatter from content
        content = frontmatter_re.sub('', text).strip()
        # Remove markdown syntax for snippet
        content_plain = re.sub(r'[#*`\[\]]+', '', content)[:2000]

        index.append({
            "path": rel,
            "title": title,
            "tags": [t for t in tags if t],
            "content": content_plain,
        })

    return index

class WikiHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/" or parsed.path == "/search":
            # Serve the search UI
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(UI_FILE.read_bytes())

        elif parsed.path == "/api/index":
            # Serve wiki index as JSON
            index = build_index()
            data = json.dumps(index, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        elif parsed.path.startswith("/outputs/charts/"):
            # Serve chart images
            img_path = ROOT / parsed.path.lstrip("/")
            if img_path.exists():
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.end_headers()
                self.wfile.write(img_path.read_bytes())
            else:
                self.send_error(404)

        else:
            self.send_error(404, "Not found")

    def log_message(self, format, *args):
        # Suppress default access log noise
        if "/api/index" not in args[0]:
            print(f"  {args[0]}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=PORT)
    args = parser.parse_args()

    print(f"🔍 Wiki Search UI")
    print(f"   http://localhost:{args.port}")
    print(f"   Wiki: {WIKI}")
    print(f"   Files indexed: {len(list(WIKI.rglob('*.md')))}")
    print(f"   Ctrl+C to stop\n")

    server = HTTPServer(("localhost", args.port), WikiHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")

if __name__ == "__main__":
    main()
