"""Build the portfolio copy of the author-supplied Stacks Q3 benchmark.

The local Google Docs PDF export is kept out of Git. This script adds a
portfolio cover and leaves every report page, source link, and disclosure
unchanged.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source-pdfs" / "stacks-q3-2026-export.pdf"
OUTPUT = ROOT / "docs" / "pdfs" / "stacks-q3-2026.pdf"
METADATA = ROOT / "docs" / "author_exports.json"
SOURCE_SHA256 = "32560214f212d53af752397bd24a016959134decfa90a62b6b4b68cbd4f07c01"


def add_cover(pdf: fitz.Document, width: float, height: float) -> None:
    page = pdf.new_page(width=width, height=height)
    dark = (0.063, 0.173, 0.204)
    cream = (0.965, 0.957, 0.929)
    gold = (0.84, 0.69, 0.46)
    muted = (0.73, 0.82, 0.83)
    page.draw_rect(page.rect, color=dark, fill=dark)
    page.draw_rect(fitz.Rect(55, 49, 96, 90), color=gold, width=0.8)
    page.insert_text((63, 77), "DP", fontname="tiro", fontsize=19, color=gold)
    page.insert_text((515, 74), "SELECTED RESEARCH / QUARTERLY REPORT", fontname="helv", fontsize=9, color=muted)

    page.insert_text((55, 205), "DIMITRIS PECHLIVANIDIS", fontname="helv", fontsize=11, color=gold)
    page.insert_text((55, 286), "Stacks", fontname="tiro", fontsize=63, color=cream)
    page.insert_text((55, 343), "Q3 2026 Benchmark", fontname="tiro", fontsize=43, color=cream)
    page.insert_text((56, 387), "July 1 to September 30, 2026", fontname="helv", fontsize=16, color=muted)
    page.draw_line((55, 420), (185, 420), color=gold, width=1)
    page.insert_text((55, 450), "Work for Alea Research", fontname="helv", fontsize=12, color=cream)

    page.draw_line((55, 510), (width - 55, 510), color=(0.31, 0.44, 0.47), width=0.8)
    page.insert_text((55, 532), "Alea Research was commissioned by Stacks for this report.", fontname="helv", fontsize=9, color=muted)
    page.insert_text((55, 548), "The report pages, source links, and disclosure are preserved.", fontname="helv", fontsize=9, color=muted)


def main() -> None:
    if not SOURCE.is_file():
        raise FileNotFoundError(f"Missing local Google Docs export: {SOURCE}")
    if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError("Stacks source PDF changed; inspect it before rebuilding")

    with fitz.open(SOURCE) as source:
        if len(source) != 50:
            raise ValueError(f"Expected 50 source pages, found {len(source)}")
        source_links = sum(len(page.get_links()) for page in source)
        if "Alea Research is engaged in a commercial relationship with Stacks" not in source[-1].get_text():
            raise ValueError("Commissioned-research disclosure is missing from source")

        with fitz.open() as portfolio:
            add_cover(portfolio, source[0].rect.width, source[0].rect.height)
            portfolio.insert_pdf(source, links=True, annots=True)
            portfolio.set_metadata({
                "title": "Stacks Q3 2026 Benchmark - Portfolio edition",
                "author": "Dimitris Pechlivanidis",
                "subject": "Work for Alea Research; commissioned by Stacks",
            })
            OUTPUT.parent.mkdir(parents=True, exist_ok=True)
            portfolio.save(OUTPUT, garbage=4, deflate=True)

    with fitz.open(OUTPUT) as result:
        if len(result) != 51 or sum(len(page.get_links()) for page in result) != source_links:
            raise RuntimeError("Stacks portfolio copy lost pages or source links")
        if "Alea Research is engaged in a commercial relationship with Stacks" not in result[-1].get_text():
            raise RuntimeError("Stacks portfolio copy lost its disclosure")

    record = {
        "kind": "quarterly_reports",
        "slug": "stacks-q3-2026",
        "title": "Stacks Q3 2026 Benchmark",
        "subtitle": "Bitcoin Staking, DeFi balances, network fees, and STX",
        "published": None,
        "date_label": "Q3 2026",
        "sort_date": "October 14, 2026",
        "source": None,
        "pdf": "pdfs/stacks-q3-2026.pdf",
        "pages": 51,
        "bytes": OUTPUT.stat().st_size,
        "provenance": "alea_commissioned",
        "client": "Stacks",
    }
    METADATA.write_text(json.dumps([record], indent=2) + "\n")
    print(f"Built {OUTPUT} ({record['pages']} pages, {record['bytes']} bytes)")


if __name__ == "__main__":
    main()
