"""Add portfolio covers to author-supplied quarterly Google Docs exports.

Keep the source exports in ignored ``source-pdfs/``. The public editions retain
the report pages and their clickable citations without changing the research.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "source-pdfs"
PDF_DIR = ROOT / "docs" / "pdfs"
METADATA = ROOT / "docs" / "author_exports.json"


@dataclass(frozen=True)
class Report:
    slug: str
    title: str
    cover_lines: tuple[str, str]
    subtitle: str
    source_sha256: str
    source_pages: int
    source_links: int


REPORTS = (
    Report(
        slug="crypto-etfs-q3-2026",
        title="State of Crypto ETFs: Q3 2026",
        cover_lines=("State of Crypto ETFs", "Q3 2026"),
        subtitle="U.S. fund assets, flows, issuers, and returns",
        source_sha256="e77a3d7b65775871b3b19447a5218bc27d03659c77143a5b31990ef61427af54",
        source_pages=18,
        source_links=56,
    ),
    Report(
        slug="robinhood-chain-q3-2026",
        title="Robinhood Chain: Q3 2026",
        cover_lines=("Robinhood Chain", "Q3 2026"),
        subtitle="Network activity, DeFi, stock tokens, and fees",
        source_sha256="3f6ed64bdd278d1ebd29a7419dd24d6caf48f50bd428991e825a7de0d628d816",
        source_pages=49,
        source_links=21,
    ),
)


def add_cover(pdf: fitz.Document, report: Report, page_rect: fitz.Rect) -> None:
    page = pdf.new_page(width=page_rect.width, height=page_rect.height)
    width, height = page_rect.width, page_rect.height
    portrait = height > width
    dark = (0.063, 0.173, 0.204)
    cream = (0.965, 0.957, 0.929)
    gold = (0.84, 0.69, 0.46)
    muted = (0.73, 0.82, 0.83)
    page.draw_rect(page.rect, color=dark, fill=dark)
    page.draw_rect(fitz.Rect(55, 49, 96, 90), color=gold, width=0.8)
    page.insert_text((63, 77), "DP", fontname="tiro", fontsize=19, color=gold)
    label = "SELECTED RESEARCH / QUARTERLY REPORT"
    label_width = fitz.get_text_length(label, fontname="helv", fontsize=9)
    page.insert_text((width - 55 - label_width, 74), label, fontname="helv", fontsize=9, color=muted)

    name_y = 225 if portrait else 205
    title_y = 306 if portrait else 286
    second_y = 363 if portrait else 343
    period_y = 413 if portrait else 387
    page.insert_text((55, name_y), "DIMITRIS PECHLIVANIDIS", fontname="helv", fontsize=11, color=gold)
    for text, y, max_size in ((report.cover_lines[0], title_y, 60), (report.cover_lines[1], second_y, 43)):
        size = min(max_size, max_size * (width - 110) / fitz.get_text_length(text, fontname="tiro", fontsize=max_size))
        page.insert_text((55, y), text, fontname="tiro", fontsize=size, color=cream)
    page.insert_text((56, period_y), "July 1 to September 30, 2026", fontname="helv", fontsize=15, color=muted)
    rule_y = 453 if portrait else 420
    page.draw_line((55, rule_y), (185, rule_y), color=gold, width=1)
    page.insert_text((55, rule_y + 30), "Research by Dimitris Pechlivanidis", fontname="helv", fontsize=12, color=cream)
    footer_y = height - 76
    page.draw_line((55, footer_y), (width - 55, footer_y), color=(0.31, 0.44, 0.47), width=0.8)
    page.insert_text((55, footer_y + 24), report.subtitle, fontname="helv", fontsize=9, color=muted)


def build(report: Report) -> dict:
    source_path = SOURCE_DIR / f"{report.slug}-export.pdf"
    output_path = PDF_DIR / f"{report.slug}.pdf"
    if not source_path.is_file():
        raise FileNotFoundError(f"Missing local Google Docs export: {source_path}")
    digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
    if digest != report.source_sha256:
        raise ValueError(f"Source PDF changed for {report.slug}; inspect it before rebuilding")

    with fitz.open(source_path) as source:
        links = sum(len(page.get_links()) for page in source)
        if len(source) != report.source_pages or links != report.source_links:
            raise ValueError(f"Unexpected page or citation count in {source_path}")
        if report.title not in source[0].get_text():
            raise ValueError(f"Unexpected report title in {source_path}")
        with fitz.open() as portfolio:
            add_cover(portfolio, report, source[0].rect)
            portfolio.insert_pdf(source, links=True, annots=True)
            portfolio.set_metadata({
                "title": f"{report.title} - Portfolio edition",
                "author": "Dimitris Pechlivanidis",
                "subject": "Quarterly research sample",
            })
            PDF_DIR.mkdir(parents=True, exist_ok=True)
            portfolio.save(output_path, garbage=4, deflate=True, no_new_id=True)

    with fitz.open(output_path) as result:
        if len(result) != report.source_pages + 1 or sum(len(page.get_links()) for page in result) != report.source_links:
            raise RuntimeError(f"Portfolio PDF lost pages or source links: {output_path}")
        if report.title not in result[1].get_text():
            raise RuntimeError(f"Portfolio PDF lost its report opening: {output_path}")

    return {
        "kind": "quarterly_reports",
        "slug": report.slug,
        "title": report.title,
        "subtitle": report.subtitle,
        "published": None,
        "date_label": "Q3 2026",
        "sort_date": "October 14, 2026",
        "source": None,
        "pdf": f"pdfs/{report.slug}.pdf",
        "pages": report.source_pages + 1,
        "bytes": output_path.stat().st_size,
        "provenance": "author_supplied",
    }


def main() -> None:
    existing = json.loads(METADATA.read_text())
    slugs = {report.slug for report in REPORTS}
    if any(item["slug"] in slugs for item in existing):
        existing = [item for item in existing if item["slug"] not in slugs]
    records = [build(report) for report in REPORTS]
    METADATA.write_text(json.dumps([*existing, *records], indent=2) + "\n")
    for record in records:
        print(f"Built {record['pdf']} ({record['pages']} pages, {record['bytes']} bytes)")


if __name__ == "__main__":
    main()
