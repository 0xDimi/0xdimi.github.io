"""Validate built PDF outputs and the static portfolio index."""

from __future__ import annotations

import json
from pathlib import Path

import fitz
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "docs"


def main() -> None:
    manifest = json.loads((SITE / "manifest.json").read_text())
    if len(manifest) != 17:
        raise RuntimeError(f"Expected 17 publications, found {len(manifest)}")
    soup = BeautifulSoup((SITE / "index.html").read_text(), "html.parser")
    cards = soup.select("#work-grid article.work-card")
    if len(cards) != len(manifest):
        raise RuntimeError("Index and manifest publication counts differ")
    if not soup.select_one('a[href="https://meditationsbyd.substack.com/"]'):
        raise RuntimeError("Substack link is missing")
    total_bytes = 0
    for item in manifest:
        path = SITE / item["pdf"]
        if not path.is_file() or path.read_bytes()[:5] != b"%PDF-":
            raise RuntimeError(f"Missing or invalid PDF: {path}")
        if not soup.select_one(f"#work-{item['slug']} a.primary-link[href='{item['pdf']}']"):
            raise RuntimeError(f"PDF has no library link: {path}")
        with fitz.open(path) as pdf:
            if len(pdf) != item["pages"]:
                raise RuntimeError(f"Manifest page count mismatch: {path}")
            if not pdf[0].get_links():
                raise RuntimeError(f"Cover has no canonical-source link: {path}")
            for number, page in enumerate(pdf, 1):
                if not page.get_text().strip() and not page.get_images():
                    raise RuntimeError(f"Blank page in {path}: page {number}")
            if item["kind"] == "collaboration":
                text = " ".join(page.get_text() for page in pdf)
                if any(f"Chapter {number}" not in text for number in (2, 3, 8)):
                    raise RuntimeError("RedStone PDF is missing a credited chapter")
        total_bytes += path.stat().st_size
    for thumbnail in SITE.glob("thumbs/*.jpg"):
        if thumbnail.stat().st_size < 10_000:
            raise RuntimeError(f"Thumbnail appears broken: {thumbnail}")
    if soup.select(".performance, .performance-method"):
        raise RuntimeError("Performance section was not fully removed")
    print(f"PASS: {len(manifest)} linked PDFs, all pages nonblank, source links present; {total_bytes / 1024 / 1024:.1f} MiB total")


if __name__ == "__main__":
    main()
