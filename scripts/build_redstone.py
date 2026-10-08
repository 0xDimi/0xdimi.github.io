"""Build a portfolio PDF of Dimitris's three credited RedStone chapters."""

from __future__ import annotations

import html
from pathlib import Path
from urllib.parse import urljoin

import fitz
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from build_articles import CHROME, CSS, PDF_DIR, ROOT, cover_html


SOURCE = "https://www.redstone.finance/research/tokenized-stocks-2026"
BASE = SOURCE.split("#", 1)[0]
OUTPUT = PDF_DIR / "tokenized-stocks-chapters-2-3-8.pdf"
CHAPTERS = [
    (2, "what-you-are-buying", "What You Are Buying"),
    (3, "ecosystem-key-players", "Tokenized Stock Ecosystem: Overview Of Key Players"),
    (8, "defi-overview", "DeFi Overview"),
]


def build_body(section, number: int, title: str) -> tuple[str, int]:
    parts = [f'<article class="redstone-chapter"><h2>Chapter {number} · {html.escape(title)}</h2><p class="chapter-credit">By Dimitris Pechlivanidis · Senior Analyst, Alea Research</p>']
    figures = 0
    for child in section.find_all(recursive=False):
        if child.select_one(".byline"):
            continue
        if child.name == "h3":
            parts.append(f"<h3>{html.escape(child.get_text(' ', strip=True))}</h3>")
            continue
        table = child.find("table")
        if table:
            for link in table.find_all("a", href=True):
                link["href"] = urljoin(BASE, link["href"])
            for node in table.find_all(True):
                node.attrs.pop("style", None)
                node.attrs.pop("class", None)
            table.attrs.clear()
            parts.append(str(table))
            continue
        figure = child.find("figure")
        if figure:
            meta = figure.find("meta", attrs={"itemprop": "contentUrl"})
            image = figure.find("img")
            src = meta.get("content") if meta else (image.get("src") if image else None)
            if not src:
                quote = figure.get_text(" ", strip=True)
                if quote:
                    parts.append(f"<blockquote>{html.escape(quote)}</blockquote>")
                continue
            caption = figure.find("figcaption")
            caption_text = caption.get_text(" ", strip=True) if caption else ""
            alt = image.get("alt", "") if image else ""
            parts.append(f'<figure><img src="{html.escape(urljoin(BASE, src), quote=True)}" alt="{html.escape(alt, quote=True)}"><figcaption>{html.escape(caption_text)}</figcaption></figure>')
            figures += 1
            continue
        for paragraph in child.find_all("p"):
            for link in paragraph.find_all("a", href=True):
                link["href"] = urljoin(BASE, link["href"])
            for node in paragraph.find_all(True):
                node.attrs.pop("style", None)
                node.attrs.pop("class", None)
            paragraph.attrs.clear()
            parts.append(str(paragraph))
    parts.append("</article>")
    return "\n".join(parts), figures


def main() -> None:
    response = requests.get(BASE, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    bodies = []
    figures = 0
    for number, anchor, title in CHAPTERS:
        heading = soup.find(id=anchor)
        if not heading or heading.get_text(" ", strip=True) != title:
            raise RuntimeError(f"RedStone chapter {number} heading was not found")
        section = heading.parent.parent.parent.find_next_sibling("section")
        if not section or "By Dimitris Pechlivanidis" not in section.get_text(" ", strip=True)[:250]:
            raise RuntimeError(f"Dimitris's byline is missing from chapter {number}")
        body, count = build_body(section, number, title)
        bodies.append(body)
        figures += count
    document = f"""<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>
      {cover_html('Tokenized Stocks', 'Chapters 2, 3, and 8 from Tokenized Stocks: Stats, Market Trends, and DeFi Gap', 'Co-authored research', 'October 6, 2026', SOURCE, publisher='RedStone, with Four Pillars and Alea Research', note='These three chapters are credited to Dimitris in the original report. The full report credits all contributors.')}
      <div class="article-kicker">REDSTONE / TOKENIZED STOCKS 2026 / CHAPTERS 2, 3, 8</div>
      {''.join(bodies)}
      </body></html>"""
    document = document.replace("</style>", "article.redstone-chapter { break-before: page; } article.redstone-chapter:first-of-type { break-before: auto; } .chapter-credit { font: 8.5pt Arial,sans-serif; color: #607680; margin-bottom: 8mm; } </style>")
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=CHROME)
        page = browser.new_page(viewport={"width": 1100, "height": 900})
        page.set_content(document, wait_until="load", timeout=60000)
        page.wait_for_function("Array.from(document.images).every(img => img.complete)", timeout=60000)
        missing = page.evaluate("Array.from(document.images).filter(i => !i.naturalWidth).map(i => i.src)")
        if missing:
            raise RuntimeError(f"Figures failed to load: {missing}")
        page.pdf(path=str(OUTPUT), format="A4", print_background=True, prefer_css_page_size=True)
        browser.close()
    pdf = fitz.open(str(OUTPUT))
    extracted = " ".join(page.get_text() for page in list(pdf)[1:])
    if len(pdf) < 10 or len(extracted) < 14000 or any(f"Chapter {n}" not in extracted for n, _, _ in CHAPTERS):
        raise RuntimeError("RedStone PDF output appears incomplete")
    print({"kind": "collaboration", "slug": "tokenized-stocks-chapters-2-3-8", "title": "Tokenized Stocks: Chapters 2, 3, and 8", "published": "October 6, 2026", "source": SOURCE, "pdf": "pdfs/tokenized-stocks-chapters-2-3-8.pdf", "pages": len(pdf), "figures": figures, "bytes": OUTPUT.stat().st_size})


if __name__ == "__main__":
    main()
