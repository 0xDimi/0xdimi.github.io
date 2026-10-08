"""Validate built PDF outputs and the static portfolio index."""

from __future__ import annotations

import json
from pathlib import Path

import fitz
from bs4 import BeautifulSoup
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "docs"


def main() -> None:
    manifest = json.loads((SITE / "manifest.json").read_text())
    if len(manifest) != 21:
        raise RuntimeError(f"Expected 21 publications, found {len(manifest)}")
    sector_sources = {
        "rwa-perpetuals": "https://alearesearch.io/reports/perspectives/rwa-perpetuals",
        "when-agents-pay": "https://alearesearch.io/reports/perspectives/when-agents-pay",
        "cross-asset-markets": "https://alearesearch.io/reports/blueprints/cross-asset-markets",
    }
    sector_items = {item["slug"]: item for item in manifest if item["kind"] == "sector_reports"}
    if set(sector_items) != set(sector_sources):
        raise RuntimeError("Sector Wide Reports category is incomplete")
    if any(sector_items[slug]["source"] != source for slug, source in sector_sources.items()):
        raise RuntimeError("Sector report source URL mismatch")
    axil = next((item for item in manifest if item["slug"] == "axil-prime-credit-3m"), None)
    if not axil or axil["kind"] != "perspectives" or axil["source"] != "https://alearesearch.io/reports/perspectives/axil-prime-credit-3m":
        raise RuntimeError("Axil public perspective is missing or misclassified")
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
        logo = SITE / item["logo"]
        if not logo.is_file():
            raise RuntimeError(f"Missing logo: {logo}")
        if logo.suffix != ".svg":
            with Image.open(logo) as image:
                if min(image.size) < 180:
                    raise RuntimeError(f"Logo resolution is too low: {logo} ({image.size})")
        for section in ("#selected", "#work-grid"):
            card = soup.select_one(f"{section} #work-{item['slug']}")
            if card is not None and not card.select_one(f'.protocol-logo img[src="{item["logo"]}"]'):
                raise RuntimeError(f"Card has no matching logo: {item['slug']}")
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
