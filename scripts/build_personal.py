"""Brand the supplied personal Tokenized Stocks slide report for the portfolio.

The source PDF stays local because the public repository should contain only
the attributed edition. Charts, captions, source text, and links are retained.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source-pdfs" / "tokenized-stocks-original.pdf"
OUTPUT = ROOT / "docs" / "pdfs" / "tokenized-stocks-ecosystem-2026.pdf"
METADATA = ROOT / "docs" / "personal.json"
EXPECTED_SOURCE_SHA256 = "4ed440ae7c95783cd8a73921ab25d43f9412b05a48379852623bc53b10d9e316"
HANDLE = "@demetriusweb3"
EXPECTED_PAGES = 37
LEGACY_CHART_MARK_PAGES = {17, 26}


def chart_bounds(page: fitz.Page) -> fitz.Rect | None:
    """Return the large chart image on a slide, excluding the cover."""
    candidates = [
        fitz.Rect(info["bbox"])
        for info in page.get_image_info()
        if info["bbox"][2] - info["bbox"][0] > 900 and info["bbox"][1] > 120
    ]
    return max(candidates, key=lambda rect: rect.width * rect.height) if candidates else None


def brand_page(page: fitz.Page, number: int) -> bool:
    if number in LEGACY_CHART_MARK_PAGES:
        # Two exported charts retained an Alea template mark. This report is
        # personal work, so cover only that footer mark; keep chart and sources.
        page.draw_rect(fitz.Rect(1805, 1005, 1888, 1055), color=None, fill=(1, 1, 1), overlay=True)

    chart = chart_bounds(page)
    if chart is not None:
        size = 48
        text_width = fitz.get_text_length(HANDLE, fontname="helv", fontsize=size)
        page.insert_text(
            (chart.x0 + (chart.width - text_width) / 2, chart.y0 + chart.height / 2),
            HANDLE,
            fontsize=size,
            fontname="helv",
            color=(0.12, 0.26, 0.30),
            fill_opacity=0.08,
            overlay=True,
        )

    size = 17
    right_edge = 1840 if number == 1 else 1824
    text_width = fitz.get_text_length(HANDLE, fontname="helv", fontsize=size)
    page.insert_text(
        (right_edge - text_width, 1058),
        HANDLE,
        fontsize=size,
        fontname="helv",
        color=(1, 1, 1) if number == 1 else (0.30, 0.38, 0.43),
        fill_opacity=0.88,
        overlay=True,
    )
    return chart is not None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=SOURCE, help="Unbranded PDF supplied by Dimitris")
    args = parser.parse_args()
    source = args.source.expanduser().resolve()
    if not source.is_file():
        raise SystemExit(f"Source PDF missing: {source}. Restore the private original or pass --source.")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if digest != EXPECTED_SOURCE_SHA256:
        raise SystemExit("Source PDF differs from the reviewed 37-page version; inspect layout before applying fixed footer masks.")

    with fitz.open(source) as document:
        if len(document) != EXPECTED_PAGES:
            raise RuntimeError(f"Expected {EXPECTED_PAGES} pages; found {len(document)}")
        original_text = [page.get_text() for page in document]
        original_links = [len(page.get_links()) for page in document]
        chart_count = sum(brand_page(page, number) for number, page in enumerate(document, 1))
        document.set_metadata({
            "title": "Tokenized Stocks: An Ecosystem & Platform Overview",
            "author": "Dimitris Pechlivanidis",
            "subject": "Personal sector report; data cutoff September 30, 2026",
            "keywords": "tokenized stocks, sector research, personal work",
        })
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        document.save(OUTPUT, garbage=4, deflate=True)

    with fitz.open(OUTPUT) as result:
        if len(result) != EXPECTED_PAGES:
            raise RuntimeError("Output page count changed")
        for number, page in enumerate(result, 1):
            text = page.get_text()
            if not text.startswith(original_text[number - 1][:50]):
                raise RuntimeError(f"Original text changed on page {number}")
            if text.count(HANDLE) != (2 if chart_bounds(page) else 1):
                raise RuntimeError(f"Handle or chart watermark missing on page {number}")
            if len(page.get_links()) != original_links[number - 1]:
                raise RuntimeError(f"Source links changed on page {number}")

    record = {
        "kind": "sector_reports",
        "slug": "tokenized-stocks-ecosystem-2026",
        "title": "Tokenized Stocks: An Ecosystem & Platform Overview",
        "subtitle": "Personal sector report",
        "published": None,
        "sort_date": "September 30, 2026",
        "date_label": "Data cutoff: Sep 30, 2026",
        "source": None,
        "provenance": "personal",
        "pdf": "pdfs/tokenized-stocks-ecosystem-2026.pdf",
        "pages": EXPECTED_PAGES,
        "watermarked_charts": chart_count,
        "bytes": OUTPUT.stat().st_size,
    }
    METADATA.write_text(json.dumps([record], indent=2) + "\n")
    print(f"Built {OUTPUT}: {EXPECTED_PAGES} pages, {chart_count} chart watermarks, {record['bytes']} bytes")


if __name__ == "__main__":
    main()
