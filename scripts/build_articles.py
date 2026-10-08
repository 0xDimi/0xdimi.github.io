"""Build readable portfolio PDFs from public Alea article pages.

The article body, figures, captions, and outbound citations come from the
canonical publication. This script changes layout and adds an attribution
cover; it does not revise investment claims.
"""

from __future__ import annotations

import argparse
import html
import os
import re
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

import requests
import fitz
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = ROOT / "docs" / "pdfs"
DEFAULT_CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
CHROME = os.environ.get("PORTFOLIO_CHROME") or (str(DEFAULT_CHROME) if DEFAULT_CHROME.exists() else None)
AS_OF = "8 October 2026"

ARTICLES = [
    ("theses", "hyperliquid", "hyperliquid-2025"),
    ("theses", "ethena", "ethena"),
    ("theses", "derive", "derive"),
    ("theses", "ether-fi", "ether-fi"),
    ("theses", "hyperliquid-2", "hyperliquid-2026"),
    ("theses", "polymarket", "polymarket"),
    ("memos", "lit", "lit"),
    ("memos", "morpho", "morpho"),
    ("memos", "vvv", "vvv"),
    ("memos", "near", "near"),
    ("memos", "zro", "zro"),
]

SUBTITLES = {
    "derive": "Onchain options investment thesis",
    "ether-fi": "The full-stack neobank thesis",
    "hyperliquid-2": "HIP-4: Outcome Markets",
    "polymarket": "$POLY token launch thesis",
}


def source_image_url(src: str, base_url: str) -> str:
    absolute = urljoin(base_url, src)
    parsed = urlparse(absolute)
    if parsed.path == "/_next/image":
        source = parse_qs(parsed.query).get("url", [None])[0]
        if source:
            return source
    return absolute


def clean_article(article, base_url: str) -> str:
    for unwanted in article.select("script, style, button, audio, iframe"):
        unwanted.decompose()

    for figure in article.select("figure"):
        image = figure.find("img")
        if image:
            source = source_image_url(image.get("src", ""), base_url)
            alt = image.get("alt", "")
            caption = figure.find("figcaption")
            caption_html = str(caption) if caption else ""
            figure.clear()
            new_image = BeautifulSoup("", "html.parser").new_tag("img", src=source)
            new_image["alt"] = alt
            figure.append(new_image)
            if caption_html:
                figure.append(BeautifulSoup(caption_html, "html.parser"))

    for node in article.find_all(True):
        if node.name == "a" and node.get("href"):
            node["href"] = urljoin(base_url, node["href"])
        for attribute in ("class", "style", "srcset", "sizes", "loading", "decoding", "data-nimg"):
            node.attrs.pop(attribute, None)

    for paragraph in article.find_all("p"):
        if not paragraph.get_text(" ", strip=True) and not paragraph.find("img"):
            paragraph.decompose()
    return str(article)


def cover_html(title: str, subtitle: str, kind: str, published: str, source: str, publisher: str = "Alea Research", note: str = "Original publisher, figures, captions, and source links are retained.") -> str:
    safe = lambda value: html.escape(value, quote=True)
    return f"""
      <section class="cover">
        <div class="cover-top"><span class="monogram">DP</span><span>SELECTED RESEARCH / {safe(kind.upper())}</span></div>
        <div class="cover-center">
          <p class="eyebrow">DIMITRIS PECHLIVANIDIS</p>
          <h1>{safe(title)}</h1>
          <p class="subtitle">{safe(subtitle)}</p>
          <div class="cover-rule"></div>
          <p class="cover-meta">Originally published by {safe(publisher)}<br>{safe(published)}</p>
        </div>
        <div class="cover-bottom">
          <p>Portfolio edition · Reformatted from the public article on {AS_OF}.<br>
             {safe(note)}</p>
          <a href="{safe(source)}">Read the original publication ↗</a>
        </div>
      </section>
    """


CSS = """
@page { size: A4; margin: 16mm 17mm 18mm; }
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body { color: #18202b; font: 10.5pt/1.53 Georgia, 'Times New Roman', serif; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
a { color: #24586b; text-decoration: underline; text-underline-offset: 2px; }
.cover { height: 262mm; page-break-after: always; display: flex; flex-direction: column; justify-content: space-between; background: #102c34; color: #f5f1e8; padding: 15mm 11mm; margin: 0; }
.cover-top { display: flex; align-items: center; justify-content: space-between; gap: 10mm; font: 8pt/1.2 Arial, sans-serif; letter-spacing: .18em; color: #b7cbd0; }
.monogram { display: grid; place-items: center; width: 14mm; height: 14mm; border: 1px solid #c89b54; color: #d9b477; font: 14pt Georgia, serif; letter-spacing: -.08em; }
.cover-center { padding: 10mm 0 17mm; }
.eyebrow { color: #d8ad6e; font: 9pt Arial, sans-serif; letter-spacing: .22em; margin: 0 0 12mm; }
.cover h1 { font: normal 35pt/1.02 Georgia, serif; letter-spacing: -.04em; margin: 0; max-width: 155mm; }
.subtitle { font: 15pt/1.28 Georgia, serif; color: #c7d7d8; margin: 8mm 0 0; max-width: 142mm; }
.cover-rule { width: 28mm; height: 1px; background: #c89b54; margin: 13mm 0 8mm; }
.cover-meta { font: 10pt/1.55 Arial, sans-serif; color: #cbd9d9; }
.cover-bottom { display: flex; align-items: flex-end; justify-content: space-between; gap: 10mm; border-top: 1px solid #577078; padding-top: 7mm; font: 8pt/1.45 Arial, sans-serif; color: #afc2c6; }
.cover-bottom p { margin: 0; max-width: 105mm; }
.cover-bottom a { color: #f2c88f; white-space: nowrap; text-decoration: none; }
.article-kicker { font: 8pt Arial, sans-serif; color: #6e8990; text-transform: uppercase; letter-spacing: .15em; border-bottom: 1px solid #c9d6d8; padding-bottom: 3mm; margin-bottom: 9mm; }
article { max-width: 100%; overflow-wrap: anywhere; }
article h2, article h3, article h4 { font-family: Georgia, serif; color: #102c34; break-after: avoid; page-break-after: avoid; }
article h2 { font-size: 20pt; line-height: 1.16; margin: 11mm 0 4mm; letter-spacing: -.025em; }
article h3 { font-size: 14pt; line-height: 1.2; margin: 8mm 0 3mm; }
article h4 { font-size: 11pt; line-height: 1.25; margin: 6mm 0 2mm; }
article p { margin: 0 0 4mm; orphans: 3; widows: 3; }
article ul, article ol { padding-left: 6mm; margin: 0 0 4mm; }
article li { margin-bottom: 2mm; }
article strong { color: #102c34; }
article blockquote { border-left: 2px solid #bd955d; margin: 6mm 0; padding: 1mm 0 1mm 5mm; color: #435861; }
article figure { margin: 7mm 0 8mm; break-inside: avoid; page-break-inside: avoid; }
article figure img { display: block; width: 100%; height: auto; max-height: 205mm; object-fit: contain; margin: 0 auto; }
article figcaption { font: 7.5pt/1.45 Arial, sans-serif; color: #647680; text-align: center; margin: 2.5mm auto 0; max-width: 90%; }
article table { width: 100%; border-collapse: collapse; font: 7.5pt/1.35 Arial, sans-serif; margin: 5mm 0; page-break-inside: auto; }
article th, article td { border: 1px solid #cbd5d7; padding: 2.2mm; vertical-align: top; }
article th { background: #e8eeec; color: #15333d; }
article tr { break-inside: avoid; }
article pre, article code { white-space: pre-wrap; overflow-wrap: anywhere; font-size: 8pt; }
"""


def build_one(browser, kind: str, slug: str, filename: str) -> dict:
    source = f"https://alearesearch.io/reports/{kind}/{slug}"
    response = requests.get(source, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    main = soup.select_one("main")
    article = soup.select_one("article.prose")
    if not main or not article:
        raise ValueError(f"No complete article found at {source}")
    title_node = main.find("h1")
    title = title_node.get_text(" ", strip=True) if title_node else slug.replace("-", " ").title()
    subtitle_node = article.find(["h2", "h3"])
    if slug in SUBTITLES:
        subtitle = SUBTITLES[slug]
    elif subtitle_node:
        subtitle = subtitle_node.get_text(" ", strip=True)
    else:
        first_paragraph = article.find("p")
        opening = first_paragraph.get_text(" ", strip=True) if first_paragraph else ""
        subtitle = re.split(r"(?<=[.!?])\s+", opening, maxsplit=1)[0][:160] or "Investment research"
    date_match = re.search(r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}, 20\d{2}\b", main.get_text(" ", strip=True))
    published = date_match.group(0) if date_match else "Publication date not shown"
    figure_count = len(article.select("figure"))
    clean = clean_article(article, source)
    doc = f"""<!doctype html><html><head><meta charset="utf-8"><title>{html.escape(title)}</title><style>{CSS}</style></head><body>
      {cover_html(title, subtitle, "Thesis" if kind == "theses" else "Memo", published, source)}
      <div class="article-kicker">ALEA RESEARCH / {kind.upper()} / {html.escape(published)}</div>
      {clean}
      </body></html>"""
    page = browser.new_page(viewport={"width": 1100, "height": 900}, device_scale_factor=1)
    failed_images = []
    page.on("response", lambda r: failed_images.append(f"{r.status} {r.url}") if r.request.resource_type == "image" and r.status >= 400 else None)
    page.set_content(doc, wait_until="load", timeout=60000)
    page.wait_for_function("Array.from(document.images).every(img => img.complete)", timeout=60000)
    image_status = page.evaluate("Array.from(document.images).map(i => ({ok:i.naturalWidth>0,src:i.src}))")
    missing = [item["src"] for item in image_status if not item["ok"]]
    if missing or failed_images:
        page.close()
        raise RuntimeError(f"Image failures in {source}: {missing[:4]} {failed_images[:4]}")
    output = PDF_DIR / f"{filename}.pdf"
    page.pdf(path=str(output), format="A4", print_background=True, prefer_css_page_size=True, display_header_footer=False)
    page.close()
    reader = fitz.open(str(output))
    if len(reader) < 2:
        raise RuntimeError(f"PDF appears incomplete: {output}")
    body_text = " ".join(p.get_text() for p in list(reader)[1:])
    if len(body_text) < 0.85 * len(article.get_text(" ", strip=True)):
        raise RuntimeError(f"Text dropped during PDF render: {output}")
    return {"kind": kind, "slug": slug, "title": title, "subtitle": subtitle, "published": published, "source": source, "pdf": f"pdfs/{filename}.pdf", "pages": len(reader), "figures": figure_count, "bytes": output.stat().st_size}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", help="Build just one output slug for inspection")
    args = parser.parse_args()
    selected = [item for item in ARTICLES if not args.only or item[2] == args.only]
    if not selected:
        raise SystemExit(f"Unknown slug: {args.only}")
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=CHROME)
        try:
            for item in selected:
                result = build_one(browser, *item)
                print(result, flush=True)
                results.append(result)
        finally:
            browser.close()
    if not args.only:
        import json
        (ROOT / "docs" / "articles.json").write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    main()
