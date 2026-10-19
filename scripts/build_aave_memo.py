"""Build a portfolio PDF from the author's complete Aave memo source."""

from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path

import fitz
import markdown2
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from build_articles import CHROME, CSS


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source-pdfs" / "aave-memo.md"
OUTPUT = ROOT / "docs" / "pdfs" / "aave.pdf"
METADATA = ROOT / "docs" / "author_memos.json"
SOURCE_URL = "https://alearesearch.io/reports/memos/aave"
SOURCE_SHA256 = "2e71bcbef97d27a7ffb670f68686c540370d3ba8cc1aa739e1aaa8967fc297b3"


def main() -> None:
    source_bytes = SOURCE.read_bytes()
    if hashlib.sha256(source_bytes).hexdigest() != SOURCE_SHA256:
        raise RuntimeError("Aave memo source differs from the reviewed author file")

    markdown_source = source_bytes.decode("utf-8").replace("\\~", "~").replace("\\.", ".")
    article_html = markdown2.markdown(markdown_source, extras=["tables"])
    article = BeautifulSoup(article_html, "html.parser")
    if len(article.select("img")) != 11 or len(article.select("a[href]")) < 25:
        raise RuntimeError("Aave memo images or citations are missing")
    for paragraph in article.find_all("p"):
        image = paragraph.find("img")
        if image and not paragraph.get_text(strip=True):
            figure = article.new_tag("figure")
            figure.append(image.extract())
            paragraph.replace_with(figure)
    article_text = article.get_text(" ", strip=True)
    if not article_text.startswith("Aave remains DeFi") or "Cut below $85" not in article_text:
        raise RuntimeError("Aave memo text appears incomplete")

    source_url = html.escape(SOURCE_URL, quote=True)
    page_html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
      <title>AAVE — Portfolio edition</title><style>{CSS}
      article img {{ display: block; max-width: 100%; width: auto; height: auto; max-height: 205mm; object-fit: contain; margin: 6mm auto; break-inside: avoid; }}
      </style></head><body>
      <section class="cover">
        <div class="cover-top"><span class="monogram">DP</span><span>SELECTED RESEARCH / MEMO</span></div>
        <div class="cover-center">
          <p class="eyebrow">DIMITRIS PECHLIVANIDIS</p>
          <h1>AAVE</h1>
          <p class="subtitle">Governance, tokenholder economics, and the investment case</p>
          <div class="cover-rule"></div>
          <p class="cover-meta">Work for Alea Research<br>February 26, 2026</p>
        </div>
        <div class="cover-bottom">
          <p>Portfolio edition · Reformatted from the author's memo source.<br>
             Original publisher, figures, and source links are retained.</p>
          <a href="{source_url}">Read the original publication ↗</a>
        </div>
      </section>
      <div class="article-kicker">ALEA RESEARCH / MEMO / FEBRUARY 26, 2026</div>
      <article>{article}</article>
      </body></html>"""

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=CHROME)
        try:
            page = browser.new_page(viewport={"width": 1100, "height": 900}, device_scale_factor=1)
            page.set_content(page_html, wait_until="load", timeout=120000)
            if not page.evaluate("Array.from(document.images).every(image => image.complete && image.naturalWidth > 0)"):
                raise RuntimeError("Aave memo has a broken figure")
            overwide = page.evaluate("Array.from(document.querySelectorAll('article img')).map((image, index) => ({index, width: image.getBoundingClientRect().width, column: image.closest('article').getBoundingClientRect().width, parent: image.parentElement.tagName})).filter(item => item.width > item.column + 1)")
            if overwide:
                raise RuntimeError(f"Aave memo has charts wider than the article column: {overwide}")
            page.pdf(path=str(OUTPUT), format="A4", print_background=True, prefer_css_page_size=True)
        finally:
            browser.close()

    with fitz.open(OUTPUT) as pdf:
        body_text = " ".join(page.get_text() for page in list(pdf)[1:])
        link_count = sum(len(page.get_links()) for page in pdf)
        image_count = sum(len(page.get_images()) for page in pdf)
        if len(pdf) < 4 or "Cut below $85" not in body_text or link_count < 26 or image_count < 11:
            raise RuntimeError("Published Aave PDF lost text, sources, or figures")
        pages = len(pdf)

    item = {
        "kind": "memos",
        "slug": "aave",
        "title": "AAVE",
        "subtitle": "Governance, tokenholder economics, and the investment case",
        "published": "February 26, 2026",
        "source": SOURCE_URL,
        "pdf": "pdfs/aave.pdf",
        "pages": pages,
        "figures": 11,
        "bytes": OUTPUT.stat().st_size,
        "provenance": "alea",
    }
    METADATA.write_text(json.dumps([item], indent=2) + "\n")
    print(f"Published {OUTPUT} ({pages} pages, {link_count} links, {image_count} image objects)")


if __name__ == "__main__":
    main()
