"""Generate the static, PDF-first portfolio index from verified output files."""

from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "docs"

SUMMARIES = {
    "tokenized-stocks-ecosystem": "A credited chapter on tokenized stock platforms, distribution, and DeFi use.",
    "hyperliquid": "Exchange and chain economics, holder base, and the case for HYPE.",
    "ethena": "Stablecoin issuance, Converge, and the economics of ENA.",
    "derive": "The investment case for an onchain options venue.",
    "ether-fi": "How staking, vaults, and payments fit into ether.fi's business model.",
    "hyperliquid-2": "HIP-4 outcome markets, user overlap, fee scenarios, and invalidation points.",
    "polymarket": "Market structure and the investment case around a potential POLY token.",
    "lit": "Lighter's valuation and the Robinhood distribution route.",
    "morpho": "A memo on Morpho's fee opportunity and the timing risk to holders.",
    "vvv": "Private AI inference and the economics of the VVV token.",
    "near": "NEAR's pivots, current positioning, and token valuation.",
    "zro": "LayerZero's Zero network and the ZRO value-capture case.",
    "steakhouse-financial": "A public vault business performance review for Q2 2026.",
    "re-protocol": "An investor relations deck on Re Protocol.",
    "theo": "An investor relations deck on Theo.",
    "usdai": "An investor relations deck on USD.AI.",
}

LABELS = {"collaboration": "Collaboration", "theses": "Investment thesis", "memos": "Investment memo", "blueprints": "IR deck"}
ORDER = {"collaboration": 0, "theses": 1, "memos": 2, "blueprints": 3}
FEATURED = ["tokenized-stocks-ecosystem", "hyperliquid-2", "morpho", "steakhouse-financial"]
DISPLAY_TITLES = {"hyperliquid": "Hyperliquid: Exchange Thesis", "hyperliquid-2": "Hyperliquid: HIP-4"}


def load_items() -> list[dict]:
    articles = json.loads((SITE / "articles.json").read_text())
    decks = json.loads((SITE / "decks.json").read_text())
    collaboration = {
        "kind": "collaboration",
        "slug": "tokenized-stocks-ecosystem",
        "title": "Tokenized Stock Ecosystem",
        "subtitle": "Credited chapter in Tokenized Stocks 2026",
        "published": "October 6, 2026",
        "source": "https://www.redstone.finance/research/tokenized-stocks-2026#ecosystem-key-players",
        "pdf": "pdfs/tokenized-stocks-ecosystem.pdf",
    }
    items = [collaboration, *articles, *decks]
    if len(items) != 16:
        raise RuntimeError(f"Expected 16 source publications, found {len(items)}")
    for item in items:
        path = SITE / item["pdf"]
        if not path.is_file():
            raise FileNotFoundError(path)
        with fitz.open(path) as pdf:
            item["pages"] = len(pdf)
        item["summary"] = SUMMARIES[item["slug"]]
    items.sort(key=lambda item: (ORDER[item["kind"]], -datetime.strptime(item["published"], "%B %d, %Y").timestamp()))
    return items


def make_thumbnail(item: dict) -> None:
    if item["slug"] not in FEATURED:
        return
    output = SITE / "thumbs" / f"{item['slug']}.jpg"
    output.parent.mkdir(parents=True, exist_ok=True)
    with fitz.open(SITE / item["pdf"]) as pdf:
        page_number = 1 if len(pdf) > 1 else 0
        pix = pdf[page_number].get_pixmap(matrix=fitz.Matrix(1.2, 1.2), alpha=False)
        from PIL import Image

        image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        image.thumbnail((900, 900))
        image.save(output, "JPEG", quality=86, optimize=True)


def card(item: dict, featured: bool = False) -> str:
    e = lambda value: html.escape(str(value), quote=True)
    slug = e(item["slug"])
    image = f'<div class="feature-image"><img src="thumbs/{slug}.jpg" alt="Page from {e(item["title"])}" loading="lazy"></div>' if featured else ""
    class_name = "work-card featured-card" if featured else "work-card"
    return f"""
      <article class="{class_name}" data-kind="{e(item['kind'])}" id="work-{slug}">
        {image}
        <div class="card-content">
          <div class="card-meta"><span>{e(LABELS[item['kind']])}</span><span>{e(item['published'])}</span></div>
          <h3>{e(DISPLAY_TITLES.get(item['slug'], item['title']))}</h3>
          <p>{e(item['summary'])}</p>
          <div class="card-bottom"><span>{item['pages']} pages · PDF</span><div class="card-links">
            <a class="primary-link" href="{e(item['pdf'])}" target="_blank" rel="noopener">Read PDF <span aria-hidden="true">↗</span></a>
            <a href="{e(item['pdf'])}" download>Download</a>
            <a href="{e(item['source'])}" target="_blank" rel="noopener">Original</a>
          </div></div>
        </div>
      </article>"""


def main() -> None:
    items = load_items()
    for item in items:
        make_thumbnail(item)
    featured = "\n".join(card(next(item for item in items if item["slug"] == slug), featured=True) for slug in FEATURED)
    library = "\n".join(card(item) for item in items)
    doc = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#102c34">
  <meta name="description" content="Selected investment research, memos, investor relations decks, and data tools by Dimitris Pechlivanidis.">
  <meta property="og:title" content="Dimitris Pechlivanidis — Research & Data">
  <meta property="og:description" content="Investment theses, memos, IR decks, and analytical tools.">
  <meta property="og:type" content="website">
  <title>Dimitris Pechlivanidis · Research & Data</title>
  <link rel="icon" href="favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <a class="skip-link" href="#main">Skip to content</a>
  <header class="site-header">
    <div class="container header-inner">
      <a class="brand" href="#top" aria-label="Dimitris Pechlivanidis, back to top"><span class="brand-mark">DP</span><span>Dimitris Pechlivanidis</span></a>
      <nav aria-label="Main navigation"><a href="#selected">Selected work</a><a href="#library">Library</a><a href="#tools">Tools</a><a class="nav-contact" href="https://www.linkedin.com/in/dimitris-pechlivanidis-a6ab38195/" target="_blank" rel="noopener">LinkedIn <span aria-hidden="true">↗</span></a></nav>
    </div>
  </header>
  <main id="main">
    <section class="hero" id="top" aria-labelledby="hero-title">
      <div class="container hero-grid">
        <div class="hero-copy">
          <p class="eyebrow"><span class="eyebrow-line"></span> INVESTMENT RESEARCH / DATA</p>
          <h1 id="hero-title">Dimitris<br><em>Pechlivanidis.</em></h1>
          <p class="hero-intro">I research crypto markets and build tools that make the evidence easier to inspect. This portfolio collects selected Alea Research publications, a credited RedStone collaboration, investor decks, and public projects. Each report opens as a readable PDF.</p>
          <div class="hero-actions"><a class="button button-light" href="#selected">Explore the work <span aria-hidden="true">↓</span></a><a class="text-link" href="https://github.com/0xDimi" target="_blank" rel="noopener">GitHub profile <span aria-hidden="true">↗</span></a></div>
        </div>
        <div class="hero-aside" aria-label="Portfolio sections">
          <div class="aside-label">INDEX / 2025—2026</div>
          <a href="#library" data-jump-filter="theses"><span>01</span><strong>Investment theses</strong><span aria-hidden="true">↗</span></a>
          <a href="#library" data-jump-filter="memos"><span>02</span><strong>Investment memos</strong><span aria-hidden="true">↗</span></a>
          <a href="#library" data-jump-filter="blueprints"><span>03</span><strong>IR decks</strong><span aria-hidden="true">↗</span></a>
          <a href="#tools"><span>04</span><strong>Data tools</strong><span aria-hidden="true">↗</span></a>
          <div class="aside-note">Alea Research publications and a credited RedStone collaboration. The original work remains linked beside every PDF.</div>
        </div>
      </div>
    </section>

    <section class="section selected-section" id="selected" aria-labelledby="selected-title">
      <div class="container">
        <div class="section-heading"><div><p class="section-no">01 / START HERE</p><h2 id="selected-title">Selected work</h2></div><p>Four samples across research, collaboration, memos, and investor communication.</p></div>
        <div class="featured-grid">{featured}</div>
      </div>
    </section>

    <section class="section library-section" id="library" aria-labelledby="library-title">
      <div class="container">
        <div class="section-heading"><div><p class="section-no">02 / FULL LIBRARY</p><h2 id="library-title">Research library</h2></div><p>Open the PDF for a clean reading copy. The original publication is linked on each card.</p></div>
        <div class="filter-bar" role="group" aria-label="Filter research by type">
          <button class="filter active" type="button" data-filter="all" aria-pressed="true">All <span>16</span></button>
          <button class="filter" type="button" data-filter="collaboration" aria-pressed="false">Collaboration <span>1</span></button>
          <button class="filter" type="button" data-filter="theses" aria-pressed="false">Theses <span>6</span></button>
          <button class="filter" type="button" data-filter="memos" aria-pressed="false">Memos <span>5</span></button>
          <button class="filter" type="button" data-filter="blueprints" aria-pressed="false">IR decks <span>4</span></button>
        </div>
        <div class="library-grid" id="work-grid">{library}</div>
        <p class="library-note">PDF editions preserve original publication credit and link back to the source. Market views reflect their publication dates.</p>
      </div>
    </section>

    <section class="section tools-section" id="tools" aria-labelledby="tools-title">
      <div class="container">
        <div class="section-heading"><div><p class="section-no">03 / BUILT WORK</p><h2 id="tools-title">Data & product tools</h2></div><p>Public projects with code or live previews.</p></div>
        <div class="tool-grid">
          <article class="tool-card"><span class="tool-index">A / DATA VISUALIZATION</span><h3>Atlas Chart Builder</h3><p>A CSV chart builder for research data, with chart export and configurable data sources.</p><div class="tool-links"><a href="https://github.com/0xDimi/atlas-chart-builder" target="_blank" rel="noopener">View code ↗</a></div></article>
          <article class="tool-card"><span class="tool-index">B / MARKET SCREENING</span><h3>Alea Signal</h3><p>A Polymarket researchability screener for crypto, finance, and economy markets. Public preview.</p><div class="tool-links"><a href="https://alea-signal.vercel.app/" target="_blank" rel="noopener">Open preview ↗</a><a href="https://github.com/0xDimi/alea-signal" target="_blank" rel="noopener">View code ↗</a></div></article>
          <article class="tool-card"><span class="tool-index">C / PRODUCT PROTOTYPE</span><h3>MANTIS</h3><p>A Greek-first prediction-market product prototype. Demo only; no real-money trading.</p><div class="tool-links"><a href="https://mantis-demo.xyz/" target="_blank" rel="noopener">Open demo ↗</a><a href="https://github.com/0xDimi/MANTIS" target="_blank" rel="noopener">View code ↗</a></div></article>
        </div>
      </div>
    </section>
  </main>
  <footer class="site-footer"><div class="container footer-inner"><div><span class="footer-mark">DP</span><p>Dimitris Pechlivanidis<br><span>Research & data</span></p></div><div class="footer-links"><a href="https://www.linkedin.com/in/dimitris-pechlivanidis-a6ab38195/" target="_blank" rel="noopener">LinkedIn ↗</a><a href="https://github.com/0xDimi" target="_blank" rel="noopener">GitHub ↗</a><a href="#top">Back to top ↑</a></div></div></footer>
  <script src="script.js" defer></script>
</body>
</html>"""
    (SITE / "index.html").write_text(doc)
    (SITE / ".nojekyll").touch()
    (SITE / "manifest.json").write_text(json.dumps(items, indent=2) + "\n")
    print(f"Generated {SITE / 'index.html'} with {len(items)} publications")


if __name__ == "__main__":
    main()
