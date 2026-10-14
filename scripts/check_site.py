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
    if len(manifest) != 27:
        raise RuntimeError(f"Expected 27 publications, found {len(manifest)}")
    quarterly_sources = {
        "etherfi-q1-2026": "https://alearesearch.io/reports/benchmark/etherfi-q1-2026",
        "threshold-q1-26": "https://alearesearch.io/reports/benchmark/threshold-q1-26",
        "stacks-q3-2026": None,
        "crypto-etfs-q3-2026": None,
        "robinhood-chain-q3-2026": None,
    }
    quarterly_items = {item["slug"]: item for item in manifest if item["kind"] == "quarterly_reports"}
    if set(quarterly_items) != set(quarterly_sources):
        raise RuntimeError("Quarterly Reports category is incomplete")
    if any(quarterly_items[slug]["source"] != source for slug, source in quarterly_sources.items()):
        raise RuntimeError("Quarterly report source URL mismatch")
    stacks = quarterly_items["stacks-q3-2026"]
    if stacks.get("provenance") != "alea_commissioned" or stacks.get("client") != "Stacks" or stacks["published"] is not None or stacks.get("date_label") != "Q3 2026":
        raise RuntimeError("Stacks attribution or reporting date is incorrect")
    for slug in ("crypto-etfs-q3-2026", "robinhood-chain-q3-2026"):
        item = quarterly_items[slug]
        if item.get("provenance") != "author_supplied" or item["published"] is not None or item.get("date_label") != "Q3 2026":
            raise RuntimeError(f"Author-supplied report attribution or period is incorrect: {slug}")
    sector_sources = {
        "tokenized-stocks-ecosystem-2026": None,
        "rwa-perpetuals": "https://alearesearch.io/reports/perspectives/rwa-perpetuals",
        "when-agents-pay": "https://alearesearch.io/reports/perspectives/when-agents-pay",
        "cross-asset-markets": "https://alearesearch.io/reports/blueprints/cross-asset-markets",
    }
    sector_items = {item["slug"]: item for item in manifest if item["kind"] == "sector_reports"}
    if set(sector_items) != set(sector_sources):
        raise RuntimeError("Sector Wide Reports category is incomplete")
    if any(sector_items[slug]["source"] != source for slug, source in sector_sources.items()):
        raise RuntimeError("Sector report source URL mismatch")
    personal = sector_items["tokenized-stocks-ecosystem-2026"]
    if personal.get("provenance") != "personal" or personal["published"] is not None:
        raise RuntimeError("Personal sector report attribution or date is incorrect")
    axil = next((item for item in manifest if item["slug"] == "axil-prime-credit-3m"), None)
    if not axil or axil["kind"] != "strategies" or axil["source"] != "https://alearesearch.io/reports/perspectives/axil-prime-credit-3m":
        raise RuntimeError("Axil public strategy is missing or misclassified")
    soup = BeautifulSoup((SITE / "index.html").read_text(), "html.parser")
    cards = soup.select("#work-grid article.work-card")
    if len(cards) != len(manifest):
        raise RuntimeError("Index and manifest publication counts differ")
    if soup.select_one('[data-filter="perspectives"]') or not soup.select_one('[data-filter="strategies"]'):
        raise RuntimeError("Perspectives filter was not renamed Strategies")
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
            if item.get("source") and not pdf[0].get_links():
                raise RuntimeError(f"Cover has no canonical-source link: {path}")
            if item["slug"] == "tokenized-stocks-ecosystem-2026":
                if soup.select_one(f"#work-{item['slug']} a:not(.primary-link):not([download])"):
                    raise RuntimeError("Personal report incorrectly has an Original link")
                handles = [page.get_text().count("@demetriusweb3") for page in pdf]
                if any(count < 1 for count in handles) or sum(count == 2 for count in handles) != item["watermarked_charts"]:
                    raise RuntimeError("Personal handle or chart watermarks are missing")
                for number in (17, 26):
                    old_mark_area = fitz.Rect(1825, 1005, 1888, 1055)
                    pixels = pdf[number - 1].get_pixmap(clip=old_mark_area, alpha=False)
                    if min(pixels.samples) < 250:
                        raise RuntimeError(f"Legacy Alea chart mark remains visible on page {number}")
            if item["slug"] == "stacks-q3-2026":
                if len(pdf) != 51 or "Work for Alea Research" not in pdf[0].get_text():
                    raise RuntimeError("Stacks cover or page count is incorrect")
                if "Alea Research is engaged in a commercial relationship with Stacks" not in pdf[-1].get_text():
                    raise RuntimeError("Stacks commissioned-research disclosure is missing")
                if soup.select_one(f"#work-{item['slug']} a:not(.primary-link):not([download])"):
                    raise RuntimeError("Stacks card links to a private source")
            if item["slug"] in ("crypto-etfs-q3-2026", "robinhood-chain-q3-2026"):
                if "Research by Dimitris Pechlivanidis" not in pdf[0].get_text():
                    raise RuntimeError(f"Author cover is missing: {item['slug']}")
                if soup.select_one(f"#work-{item['slug']} a:not(.primary-link):not([download])"):
                    raise RuntimeError(f"Private Google Doc is linked publicly: {item['slug']}")
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
    print(f"PASS: {len(manifest)} linked PDFs, all pages nonblank, source links present where applicable; {total_bytes / 1024 / 1024:.1f} MiB total")


if __name__ == "__main__":
    main()
