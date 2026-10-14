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
    "tokenized-stocks-ecosystem-2026": "Personal sector research on market size, product rights, platform activity, DeFi use, and execution costs.",
    "stacks-q3-2026": "Q3 review of Bitcoin Staking, sBTC, DeFi balances, fees, and STX valuation. Commissioned Alea Research work.",
    "crypto-etfs-q3-2026": "Q3 review of U.S. crypto ETF assets, fund flows, issuer economics, and product structure.",
    "robinhood-chain-q3-2026": "Robinhood Chain's first public quarter: network activity, DeFi balances, stock tokens, and fee economics.",
    "etherfi-q1-2026": "Quarter-to-date review of Cash, Stake, Liquid, revenue, and ETHFI; data through February 9.",
    "threshold-q1-26": "Q1 review of tBTC supply, DeFi use, fees, and T valuation; data through March 31.",
    "rwa-perpetuals": "Where RWA perps find demand: overnight markets, weekend risk, and pre-IPO price discovery.",
    "when-agents-pay": "Who authorizes an agent's payment, verifies delivery, and captures the economics.",
    "cross-asset-markets": "A cross-asset deck on crypto, rates, and market pricing around the 2026 Fed hike.",
    "axil-prime-credit-3m": "A public perspective on a three-month tokenized consumer-credit vault: how it works, its safeguards, and its risks.",
    "tokenized-stocks-chapters-2-3-8": "My credited chapters on investor rights, the tokenized stock ecosystem, and DeFi use.",
    "hyperliquid": "Exchange and chain economics, holder base, and the case for HYPE.",
    "ethena": "Stablecoin issuance, Converge, and the economics of ENA.",
    "derive": "The investment case for an onchain options venue.",
    "ether-fi": "How staking, vaults, and payments fit into ether.fi's business model.",
    "hyperliquid-2": "HIP-4 outcome markets, user overlap, fee scenarios, and invalidation points.",
    "polymarket": "Market structure and the investment case around a potential POLY token.",
    "pendle-one-venue-all-of-fixed-income": "Pendle's yield-trading position, Boros, and the case for a broader fixed-income venue.",
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

LABELS = {"collaboration": "Collaboration", "sector_reports": "Sector Wide Report", "quarterly_reports": "Quarterly Report", "strategies": "Strategy", "theses": "Investment thesis", "memos": "Investment memo", "blueprints": "IR deck", "data_rooms": "Data room"}
ORDER = {"collaboration": 0, "sector_reports": 1, "quarterly_reports": 2, "strategies": 3, "theses": 4, "memos": 5, "blueprints": 6, "data_rooms": 7}
FEATURED = ["tokenized-stocks-chapters-2-3-8", "hyperliquid-2", "morpho", "steakhouse-financial"]
DISPLAY_TITLES = {"hyperliquid": "Hyperliquid: Exchange Thesis", "hyperliquid-2": "Hyperliquid: HIP-4", "etherfi-q1-2026": "Ether.fi: Q1 2026", "threshold-q1-26": "Threshold: Q1 2026", "stacks-q3-2026": "Stacks: Q3 2026"}
REPORT_LOGOS = {
    "tokenized-stocks-ecosystem-2026": "dimi",
    "stacks-q3-2026": "stacks",
    "crypto-etfs-q3-2026": "dimi",
    "robinhood-chain-q3-2026": "robinhood-chain",
    "etherfi-q1-2026": "ether-fi",
    "threshold-q1-26": "threshold",
    "rwa-perpetuals": "alea",
    "when-agents-pay": "alea",
    "cross-asset-markets": "alea",
    "axil-prime-credit-3m": "axil",
    "tokenized-stocks-chapters-2-3-8": "redstone",
    "hyperliquid": "hyperliquid",
    "hyperliquid-2": "hyperliquid",
    "polymarket": "polymarket",
    "pendle-one-venue-all-of-fixed-income": "pendle",
    "ether-fi": "ether-fi",
    "derive": "derive",
    "ethena": "ethena",
    "lit": "lighter",
    "morpho": "morpho",
    "vvv": "venice",
    "near": "near",
    "zro": "layerzero",
    "steakhouse-financial": "steakhouse",
    "re-protocol": "re",
    "theo": "theo",
    "usdai": "usdai",
}


def load_items() -> list[dict]:
    articles = json.loads((SITE / "articles.json").read_text())
    decks = json.loads((SITE / "decks.json").read_text())
    personal = json.loads((SITE / "personal.json").read_text())
    author_exports = json.loads((SITE / "author_exports.json").read_text())
    data_rooms = json.loads((SITE / "data_rooms.json").read_text())
    logos = json.loads((SITE / "logos" / "sources.json").read_text())
    collaboration = {
        "kind": "collaboration",
        "slug": "tokenized-stocks-chapters-2-3-8",
        "title": "Tokenized Stocks: Chapters 2, 3, and 8",
        "subtitle": "My credited chapters in Tokenized Stocks 2026",
        "published": "October 6, 2026",
        "source": "https://www.redstone.finance/research/tokenized-stocks-2026",
        "pdf": "pdfs/tokenized-stocks-chapters-2-3-8.pdf",
    }
    items = [collaboration, *articles, *decks, *personal, *author_exports, *data_rooms]
    if len(items) != 33:
        raise RuntimeError(f"Expected 33 portfolio samples, found {len(items)}")
    for item in items:
        if item["kind"] != "data_rooms":
            path = SITE / item["pdf"]
            if not path.is_file():
                raise FileNotFoundError(path)
            with fitz.open(path) as pdf:
                item["pages"] = len(pdf)
            item["summary"] = SUMMARIES[item["slug"]]
        logo_key = item["logo_key"] if item["kind"] == "data_rooms" else REPORT_LOGOS[item["slug"]]
        item["logo"] = f"logos/{logos[logo_key]['file']}"
        if not (SITE / item["logo"]).is_file():
            raise FileNotFoundError(SITE / item["logo"])
    for index, room in enumerate(data_rooms):
        room["sort_order"] = index
    items.sort(key=lambda item: (ORDER[item["kind"]], item["sort_order"] if item["kind"] == "data_rooms" else -datetime.strptime(item.get("sort_date") or item["published"], "%B %d, %Y").timestamp()))
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
    if item["kind"] == "data_rooms":
        return f"""
      <article class="{class_name}" data-kind="data_rooms" id="work-{slug}">
        <div class="card-content">
          <div class="card-meta"><span>Data room</span><span>Live site</span></div>
          <div class="card-title-row"><span class="protocol-logo" aria-hidden="true"><img src="{e(item['logo'])}" alt="" width="58" height="58" loading="lazy" decoding="async"></span><h3>{e(item['title'])}</h3></div>
          <p>{e(item['summary'])}</p>
          <div class="card-bottom"><span>{e(item['access'])}</span><div class="card-links">
            <a class="primary-link" href="{e(item['url'])}" target="_blank" rel="noopener">Open data room <span aria-hidden="true">↗</span></a>
          </div></div>
        </div>
      </article>"""
    source_link = f'<a href="{e(item["source"])}" target="_blank" rel="noopener">Original</a>' if item.get("source") else ""
    date_label = item.get("date_label") or item["published"]
    return f"""
      <article class="{class_name}" data-kind="{e(item['kind'])}" id="work-{slug}">
        {image}
        <div class="card-content">
          <div class="card-meta"><span>{e(LABELS[item['kind']])}</span><span>{e(date_label)}</span></div>
          <div class="card-title-row"><span class="protocol-logo" aria-hidden="true"><img src="{e(item['logo'])}" alt="" width="58" height="58" loading="lazy" decoding="async"></span><h3>{e(DISPLAY_TITLES.get(item['slug'], item['title']))}</h3></div>
          <p>{e(item['summary'])}</p>
          <div class="card-bottom"><span>{item['pages']} pages · PDF</span><div class="card-links">
            <a class="primary-link" href="{e(item['pdf'])}" target="_blank" rel="noopener">Read PDF <span aria-hidden="true">↗</span></a>
            <a href="{e(item['pdf'])}" download>Download</a>
            {source_link}
          </div></div>
        </div>
      </article>"""


def main() -> None:
    items = load_items()
    for item in items:
        make_thumbnail(item)
    featured = "\n".join(card(next(item for item in items if item["slug"] == slug), featured=True) for slug in FEATURED)
    library = "\n".join(card(item) for item in items)
    counts = {kind: sum(item["kind"] == kind for item in items) for kind in LABELS}
    doc = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#102c34">
  <meta name="description" content="Selected sector and quarterly reports, strategies, investment theses, memos, IR decks, data rooms, and tools by Dimitris Pechlivanidis.">
  <meta property="og:title" content="Dimitris Pechlivanidis — Research & Data">
  <meta property="og:description" content="Sector and quarterly reports, strategies, investment theses, memos, data rooms, and analytical tools.">
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
      <nav aria-label="Main navigation"><a href="#selected">Selected work</a><a href="#library">Library</a><a href="#tools">Tools</a><a href="#about">About</a><a class="nav-contact" href="https://www.linkedin.com/in/dimitris-pechlivanidis-a6ab38195/" target="_blank" rel="noopener">LinkedIn <span aria-hidden="true">↗</span></a></nav>
    </div>
  </header>
  <main id="main">
    <section class="hero" id="top" aria-labelledby="hero-title">
      <div class="container hero-grid">
        <div class="hero-copy">
          <p class="eyebrow"><span class="eyebrow-line"></span> INVESTMENT RESEARCH / DATA</p>
          <h1 id="hero-title">Dimitris<br><em>Pechlivanidis.</em></h1>
          <div class="hero-actions"><a class="button button-light" href="#selected">Explore the work <span aria-hidden="true">↓</span></a><a class="text-link" href="https://github.com/0xDimi" target="_blank" rel="noopener">GitHub profile <span aria-hidden="true">↗</span></a></div>
        </div>
        <div class="hero-aside" aria-label="Portfolio sections">
          <div class="aside-label">INDEX / 2025—2026</div>
          <a href="#library" data-jump-filter="sector_reports"><span>01</span><strong>Sector Wide Reports</strong><span aria-hidden="true">↗</span></a>
          <a href="#library" data-jump-filter="quarterly_reports"><span>02</span><strong>Quarterly Reports</strong><span aria-hidden="true">↗</span></a>
          <a href="#library" data-jump-filter="theses"><span>03</span><strong>Investment theses</strong><span aria-hidden="true">↗</span></a>
          <a href="#library" data-jump-filter="memos"><span>04</span><strong>Investment memos</strong><span aria-hidden="true">↗</span></a>
          <a href="#library" data-jump-filter="blueprints"><span>05</span><strong>IR decks</strong><span aria-hidden="true">↗</span></a>
          <a href="#library" data-jump-filter="data_rooms"><span>06</span><strong>Data Rooms</strong><span aria-hidden="true">↗</span></a>
          <a href="#tools"><span>07</span><strong>Data tools</strong><span aria-hidden="true">↗</span></a>
        </div>
      </div>
    </section>

    <section class="section selected-section" id="selected" aria-labelledby="selected-title">
      <div class="container">
        <div class="section-heading"><div><p class="section-no">01 / START HERE</p><h2 id="selected-title">Selected work</h2></div></div>
        <div class="featured-grid">{featured}</div>
      </div>
    </section>

    <section class="section library-section" id="library" aria-labelledby="library-title">
      <div class="container">
        <div class="section-heading"><div><p class="section-no">02 / FULL LIBRARY</p><h2 id="library-title">Work Samples</h2></div><p class="sample-note">A small selection from more than 50 reports I've produced across Alea Research and Revelo.</p></div>
        <div class="filter-bar" role="group" aria-label="Filter research by type">
          <button class="filter active" type="button" data-filter="all" aria-pressed="true">All <span>{len(items)}</span></button>
          <button class="filter" type="button" data-filter="collaboration" aria-pressed="false">Collaboration <span>{counts['collaboration']}</span></button>
          <button class="filter" type="button" data-filter="sector_reports" aria-pressed="false">Sector Wide Reports <span>{counts['sector_reports']}</span></button>
          <button class="filter" type="button" data-filter="quarterly_reports" aria-pressed="false">Quarterly Reports <span>{counts['quarterly_reports']}</span></button>
          <button class="filter" type="button" data-filter="strategies" aria-pressed="false">Strategies <span>{counts['strategies']}</span></button>
          <button class="filter" type="button" data-filter="theses" aria-pressed="false">Theses <span>{counts['theses']}</span></button>
          <button class="filter" type="button" data-filter="memos" aria-pressed="false">Memos <span>{counts['memos']}</span></button>
          <button class="filter" type="button" data-filter="blueprints" aria-pressed="false">IR decks <span>{counts['blueprints']}</span></button>
          <button class="filter" type="button" data-filter="data_rooms" aria-pressed="false">Data Rooms <span>{counts['data_rooms']}</span></button>
        </div>
        <div class="library-grid" id="work-grid">{library}</div>
        <p class="library-note">Reports link to published originals where available. The Stacks benchmark retains its commissioned-research disclosure, and the personal report shows its data cutoff. Market views reflect the dates shown.</p>
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
    <section class="section about-section" id="about" aria-labelledby="about-title">
      <div class="container about-grid">
        <div class="about-heading"><p class="section-no">04 / THE PERSON BEHIND THE WORK</p><h2 id="about-title">About</h2><div class="about-rule" aria-hidden="true"></div></div>
        <div class="about-copy">
          <p class="about-lead">Give a damn and you'll be great.</p>
          <p>I've evaluated more than 50 businesses and protocols, sourced at least 20 blockchain startups, and invested in many of them. I've also invested in robotics and AI companies. Skin in the game matters to me. I put my conviction up for judgment, test the assumptions behind it, and change my mind when the evidence calls for it.</p>
          <p>Client work matters just as much. At Alea Research, I've helped teams raise money, shape go-to-market strategies and business models, plan incentive campaigns, and prepare investor materials. The work goes beyond a report: I stay involved with the decisions teams have to make.</p>
          <p>Before research, I spent twelve years in competitive football and five years in sales in Greece. Both taught me to care about the result. A match ends. A client buys or walks away. I bring the same attitude to research and investing.</p>
          <a class="about-link" href="https://meditationsbyd.substack.com/" target="_blank" rel="noopener">Read more of my writing on Substack <span aria-hidden="true">↗</span></a>
        </div>
      </div>
    </section>
  </main>
  <footer class="site-footer"><div class="container footer-inner"><div><span class="footer-mark">DP</span><p>Dimitris Pechlivanidis<br><span>Research & data</span></p></div><div class="footer-links"><a href="https://meditationsbyd.substack.com/" target="_blank" rel="noopener">Substack ↗</a><a href="https://www.linkedin.com/in/dimitris-pechlivanidis-a6ab38195/" target="_blank" rel="noopener">LinkedIn ↗</a><a href="https://github.com/0xDimi" target="_blank" rel="noopener">GitHub ↗</a><a href="#top">Back to top ↑</a></div></div></footer>
  <script src="script.js" defer></script>
</body>
</html>"""
    (SITE / "index.html").write_text("\n".join(line.rstrip() for line in doc.splitlines()) + "\n")
    (SITE / ".nojekyll").touch()
    (SITE / "manifest.json").write_text(json.dumps(items, indent=2) + "\n")
    print(f"Generated {SITE / 'index.html'} with {len(items)} work samples")


if __name__ == "__main__":
    main()
