"""Build a portfolio PDF of Dimitris's credited RedStone report section."""

from __future__ import annotations

import html
from pathlib import Path
from urllib.parse import urljoin

import fitz
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from build_articles import CHROME, CSS, PDF_DIR, ROOT, cover_html


SOURCE = "https://www.redstone.finance/research/tokenized-stocks-2026#ecosystem-key-players"
BASE = SOURCE.split("#", 1)[0]
OUTPUT = PDF_DIR / "tokenized-stocks-ecosystem.pdf"


def build_body(section) -> tuple[str, int]:
    parts = ["<article><h2>Tokenized Stock Ecosystem: Overview Of Key Players</h2>"]
    figures = 0
    for child in section.find_all(recursive=False):
        if child.select_one(".byline"):
            continue
        figure = child.find("figure")
        if figure:
            meta = figure.find("meta", attrs={"itemprop": "contentUrl"})
            image = figure.find("img")
            src = meta.get("content") if meta else (image.get("src") if image else None)
            if not src:
                raise RuntimeError("A published figure has no image URL")
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
    heading = soup.find(id="ecosystem-key-players")
    if not heading:
        raise RuntimeError("The credited RedStone chapter was not found")
    section = heading.parent.parent.parent.find_next_sibling("section")
    if not section or "By Dimitris Pechlivanidis" not in section.get_text(" ", strip=True)[:250]:
        raise RuntimeError("Dimitris's byline is missing from this chapter")
    body, figures = build_body(section)
    document = f"""<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>
      {cover_html('Tokenized Stock Ecosystem', 'A chapter from Tokenized Stocks: Stats, Market Trends, and DeFi Gap', 'Co-authored research', 'October 6, 2026', SOURCE, publisher='RedStone, with Four Pillars and Alea Research', note='This PDF contains the chapter credited to Dimitris; the full report credits all contributors.')}
      <div class="article-kicker">REDSTONE / TOKENIZED STOCKS 2026 / CREDITED CHAPTER</div>
      {body}
      </body></html>"""
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
    if len(pdf) < 2 or len(" ".join(page.get_text() for page in list(pdf)[1:])) < 3000:
        raise RuntimeError("RedStone PDF output appears incomplete")
    print({"kind": "collaboration", "slug": "tokenized-stocks-ecosystem", "title": "Tokenized Stock Ecosystem", "published": "October 6, 2026", "source": SOURCE, "pdf": "pdfs/tokenized-stocks-ecosystem.pdf", "pages": len(pdf), "figures": figures, "bytes": OUTPUT.stat().st_size})


if __name__ == "__main__":
    main()
