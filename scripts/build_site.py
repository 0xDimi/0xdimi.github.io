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
    "derive-q3-2026": "Q3 review of options volume, the V3 migration, fee economics, and DRV buybacks.",
    "tokenized-stocks-ecosystem-2026": "Personal sector research on market size, product rights, platform activity, DeFi use, and execution costs.",
    "stacks-q3-2026": "Q3 review of Bitcoin Staking, sBTC, DeFi balances, fees, and STX valuation. Commissioned Alea Research work.",
    "crypto-etfs-q3-2026": "Q3 review of U.S. crypto ETF assets, fund flows, issuer economics, and product structure.",
    "robinhood-chain-q3-2026": "Robinhood Chain's first public quarter: network activity, DeFi balances, stock tokens, and fee economics.",
    "prediction-markets-q3-2026": "Q3 review of Kalshi, Polymarket, fee retention, combo contracts, and broker distribution.",
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
    "aave": "Aave governance, tokenholder economics, buybacks, and the V4 transition.",
    "steakhouse-financial": "A public vault business performance review for Q2 2026.",
    "re-protocol": "An investor relations deck on Re Protocol.",
    "theo": "An investor relations deck on Theo.",
    "usdai": "An investor relations deck on USD.AI.",
    "circle-financial-model": "A scenario model connecting USDC circulation, reserve yield, retained income, and cash flow to Circle equity value.",
}

LABELS = {"collaboration": "Collaboration", "sector_reports": "Sector Wide Report", "quarterly_reports": "Quarterly Report", "strategies": "Strategy", "theses": "Investment thesis", "memos": "Investment memo", "blueprints": "IR deck", "financial_models": "Financial model", "data_rooms": "Data room"}
ORDER = {"collaboration": 0, "sector_reports": 1, "quarterly_reports": 2, "strategies": 3, "theses": 4, "memos": 5, "blueprints": 6, "financial_models": 7, "data_rooms": 8}
CATEGORY_DESCRIPTIONS = {
    "all": "Selected research, investor materials, and live data products.",
    "collaboration": "Research written with partners, with my contributions clearly credited.",
    "sector_reports": "Sector-wide reports cover emerging narratives and shifts in market structure.",
    "quarterly_reports": "Quarterly reports track markets and protocols through operating data.",
    "strategies": "Strategies explain how an investment product works and where its risks sit.",
    "theses": "Investment theses weigh a protocol's upside against its risks and valuation.",
    "memos": "Investment memos give a short view on an asset and its key assumptions.",
    "blueprints": "IR decks present a business case and its operating record to investors.",
    "financial_models": "Financial models connect operating assumptions to forecasts and valuation.",
    "data_rooms": "Data Rooms pair protocol research with the data behind it.",
}
FEATURED = ["tokenized-stocks-ecosystem-2026", "prediction-markets-q3-2026", "pendle-one-venue-all-of-fixed-income", "derive"]
STOCKLENS = {
    "slug": "stocklens",
    "title": "Stocklens",
    "app": "https://stocklens-osft.onrender.com/?stock=US67066G1040&amount=1000&chain=all&view=products",
    "code": "https://github.com/0xDimi/stocklens/tree/main",
}
FEATURED_COVERS = {
    "stocklens": {
        "number": "1", "category": "LIVE PRODUCT", "lines": ("Stocklens",),
        "subtitle": "One stock. Compare its tokens.", "credit": "PERSONAL PROJECT",
        "art": "stocklens",
    },
    "tokenized-stocks-ecosystem-2026": {
        "number": "2", "category": "SECTOR WIDE REPORT", "lines": ("Tokenized", "Stocks"),
        "subtitle": "An Ecosystem & Platform Overview", "credit": "PERSONAL RESEARCH",
        "art": "stocks",
    },
    "prediction-markets-q3-2026": {
        "number": "3", "category": "QUARTERLY REPORT", "lines": ("Prediction", "Markets"),
        "subtitle": "State of the Market · Q3 2026", "credit": "PERSONAL RESEARCH",
        "art": "prediction",
    },
    "pendle-one-venue-all-of-fixed-income": {
        "number": "4", "category": "INVESTMENT THESIS", "lines": ("Pendle",),
        "subtitle": "One Venue, All of Fixed Income", "credit": "WORK FOR ALEA RESEARCH",
        "art": "pendle",
    },
    "derive": {
        "number": "5", "category": "INVESTMENT THESIS", "lines": ("Derive",),
        "subtitle": "Onchain Options", "credit": "WORK FOR ALEA RESEARCH",
        "art": "derive",
    },
}
DISPLAY_TITLES = {"hyperliquid": "Hyperliquid: Exchange Thesis", "hyperliquid-2": "Hyperliquid: HIP-4", "etherfi-q1-2026": "Ether.fi: Q1 2026", "threshold-q1-26": "Threshold: Q1 2026", "stacks-q3-2026": "Stacks: Q3 2026"}
REPORT_LOGOS = {
    "derive-q3-2026": "derive",
    "tokenized-stocks-ecosystem-2026": "dimi",
    "stacks-q3-2026": "stacks",
    "crypto-etfs-q3-2026": "dimi",
    "robinhood-chain-q3-2026": "robinhood-chain",
    "prediction-markets-q3-2026": "dimi",
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
    "aave": "aave",
    "steakhouse-financial": "steakhouse",
    "re-protocol": "re",
    "theo": "theo",
    "usdai": "usdai",
    "circle-financial-model": "circle",
}


def load_items() -> list[dict]:
    articles = json.loads((SITE / "articles.json").read_text())
    decks = json.loads((SITE / "decks.json").read_text())
    personal = json.loads((SITE / "personal.json").read_text())
    author_exports = json.loads((SITE / "author_exports.json").read_text())
    author_memos = json.loads((SITE / "author_memos.json").read_text())
    financial_models = json.loads((SITE / "financial_models.json").read_text())
    linked_reports = json.loads((SITE / "linked_reports.json").read_text())
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
    items = [collaboration, *articles, *linked_reports, *decks, *personal, *author_exports, *author_memos, *financial_models, *data_rooms]
    if len(items) != 37:
        raise RuntimeError(f"Expected 37 portfolio samples, found {len(items)}")
    for item in items:
        if item.get("pdf"):
            path = SITE / item["pdf"]
            if not path.is_file():
                raise FileNotFoundError(path)
            with fitz.open(path) as pdf:
                item["pages"] = len(pdf)
        if item["kind"] != "data_rooms":
            item["summary"] = SUMMARIES[item["slug"]]
        logo_key = item["logo_key"] if item["kind"] == "data_rooms" else REPORT_LOGOS[item["slug"]]
        item["logo"] = f"logos/{logos[logo_key]['file']}"
        if not (SITE / item["logo"]).is_file():
            raise FileNotFoundError(SITE / item["logo"])
    for index, room in enumerate(data_rooms):
        room["sort_order"] = index
    items.sort(key=lambda item: (ORDER[item["kind"]], item["sort_order"] if item["kind"] == "data_rooms" else -datetime.strptime(item.get("sort_date") or item["published"], "%B %d, %Y").timestamp()))
    return items


def cover_art(kind: str) -> str:
    """Topic-specific editorial motifs; these illustrate concepts, not market data."""
    if kind == "stocklens":
        return '''<g transform="translate(760 122)">
          <circle cx="202" cy="192" r="158" fill="none" stroke="#527d72" stroke-width="2"/>
          <circle cx="202" cy="192" r="124" fill="none" stroke="#78a58f" stroke-opacity=".65" stroke-width="2"/>
          <path d="M313 304l86 86" stroke="#d9b37c" stroke-width="19" stroke-linecap="round"/>
          <rect x="45" y="93" width="246" height="87" rx="6" fill="#1b4950" stroke="#7ca495" stroke-width="2"/>
          <rect x="80" y="194" width="246" height="87" rx="6" fill="#1b4950" stroke="#d9b37c" stroke-width="2"/>
          <circle cx="80" cy="136" r="18" fill="#a6c8ae"/><circle cx="115" cy="237" r="18" fill="#d9b37c"/>
          <path d="M119 129h113 M119 145h80 M154 230h113 M154 246h80" stroke="#d2e0d1" stroke-width="5" stroke-linecap="round"/>
          <path d="M45 321h221" stroke="#81a89a" stroke-width="2" stroke-dasharray="7 10"/>
        </g>'''
    if kind == "stocks":
        return '''<g transform="translate(772 114) rotate(-14 160 150)">
          <rect x="0" y="24" width="314" height="370" rx="10" fill="#1a4248" stroke="#547d79" stroke-width="2"/>
          <rect x="36" y="0" width="314" height="370" rx="10" fill="#204e52" stroke="#77a29a" stroke-width="2"/>
          <rect x="72" y="-24" width="314" height="370" rx="10" fill="#123840" stroke="#d0a36a" stroke-width="2"/>
          <path d="M72 93h314 M72 244h314 M182 -24v370 M287 -24v370" stroke="#6f9690" stroke-opacity=".55"/>
          <circle cx="127" cy="40" r="19" fill="none" stroke="#d6b27f" stroke-width="3"/>
          <path d="M116 40h22 M127 29v22" stroke="#d6b27f" stroke-width="2"/>
          <path d="M228 42h61 M228 57h91 M98 141h69 M98 158h110 M203 141h57 M203 158h74 M310 141h47 M310 158h28" stroke="#aac6b9" stroke-width="4" stroke-linecap="round" opacity=".8"/>
          <path d="M98 294h53 M203 294h53 M310 294h45" stroke="#d4aa75" stroke-width="5" stroke-linecap="round"/>
        </g>'''
    if kind == "prediction":
        return '''<g transform="translate(735 110)">
          <path d="M0 57h405 M0 159h405 M0 261h405 M0 363h405 M36 0v405 M138 0v405 M240 0v405 M342 0v405" stroke="#4a7270" stroke-width="1" opacity=".5"/>
          <path d="M0 300 C62 285 73 198 137 207 S228 300 289 173 S370 119 405 58" fill="none" stroke="#d6ad75" stroke-width="6" stroke-linecap="round"/>
          <path d="M0 107 C73 103 81 170 142 161 S228 114 284 235 S356 294 405 340" fill="none" stroke="#a0c4b5" stroke-width="4" stroke-linecap="round"/>
          <circle cx="289" cy="173" r="12" fill="#d6ad75"/><circle cx="284" cy="235" r="9" fill="#a0c4b5"/>
          <circle cx="289" cy="173" r="26" fill="none" stroke="#d6ad75" opacity=".45"/>
        </g>'''
    if kind == "pendle":
        return '''<g transform="translate(747 137)">
          <path d="M5 270h415" stroke="#668d86" stroke-width="2"/>
          <path d="M5 270 C89 270 120 242 166 183 S262 79 420 48" fill="none" stroke="#d9b37c" stroke-width="6" stroke-linecap="round"/>
          <path d="M5 270 C92 270 131 230 190 213 S301 193 420 192" fill="none" stroke="#9fc3b5" stroke-width="4" stroke-linecap="round"/>
          <path d="M5 270 C88 270 135 274 198 292 S319 329 420 338" fill="none" stroke="#527c78" stroke-width="4" stroke-linecap="round"/>
          <circle cx="5" cy="270" r="16" fill="#d9b37c"/>
          <circle cx="420" cy="48" r="9" fill="#d9b37c"/><circle cx="420" cy="192" r="9" fill="#9fc3b5"/><circle cx="420" cy="338" r="9" fill="#527c78"/>
        </g>'''
    if kind == "derive":
        return '''<g transform="translate(738 106)">
          <path d="M0 50h425 M0 155h425 M0 260h425 M0 365h425 M42 0v410 M148 0v410 M254 0v410 M360 0v410" stroke="#527974" stroke-width="1" opacity=".45"/>
          <path d="M0 306h155l106-205 96 205h68" fill="none" stroke="#d9b37c" stroke-width="6" stroke-linejoin="round"/>
          <path d="M0 306h112l94-107h82l94 107h43" fill="none" stroke="#9fc3b5" stroke-width="4" stroke-linejoin="round"/>
          <circle cx="261" cy="101" r="13" fill="#d9b37c"/>
          <circle cx="206" cy="199" r="9" fill="#9fc3b5"/>
        </g>'''
    raise ValueError(f"Unknown cover art: {kind}")


def make_featured_cover(item: dict) -> None:
    if item["slug"] not in FEATURED_COVERS:
        return
    output = SITE / "thumbs" / f"{item['slug']}.svg"
    output.parent.mkdir(parents=True, exist_ok=True)
    spec = FEATURED_COVERS[item["slug"]]
    title = "".join(f'<text x="58" y="{289 + 83 * index}" class="title">{html.escape(line)}</text>' for index, line in enumerate(spec["lines"]))
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="600" viewBox="0 0 1200 600" role="img" aria-labelledby="title description">
      <title id="title">{html.escape(item['title'])}</title>
      <desc id="description">Editorial portfolio cover with a conceptual illustration.</desc>
      <defs><linearGradient id="background" x2="1" y2="1"><stop stop-color="#102d35"/><stop offset="1" stop-color="#173b42"/></linearGradient></defs>
      <style>
        .label{{font:700 15px 'Avenir Next',Avenir,Arial,sans-serif;letter-spacing:3px;fill:#d5ad75}}
        .small{{font:600 16px 'Avenir Next',Avenir,Arial,sans-serif;letter-spacing:1.2px;fill:#b7cbc5}}
        .title{{font:normal 77px 'Iowan Old Style',Baskerville,Georgia,serif;letter-spacing:-2px;fill:#f8f4e9}}
        .subtitle{{font:normal 22px 'Avenir Next',Avenir,Arial,sans-serif;fill:#e5d4b9}}
      </style>
      <rect width="1200" height="600" fill="url(#background)"/>
      <path d="M0 108h1200 M0 506h1200" stroke="#77918d" stroke-opacity=".45"/>
      <rect x="58" y="38" width="43" height="43" fill="none" stroke="#cba168"/>
      <text x="65" y="68" style="font:normal 24px Georgia,serif;fill:#d6ae77">DP</text>
      <text x="124" y="66" class="label">SELECTED WORK / {spec['number']}</text>
      <text x="58" y="184" class="label">{spec['category']}</text>
      {title}
      <text x="61" y="{397 if len(spec['lines']) == 1 else 447}" class="subtitle">{html.escape(spec['subtitle'])}</text>
      <text x="58" y="552" class="small">DIMITRIS PECHLIVANIDIS</text>
      <text x="1143" y="552" text-anchor="end" class="small">{spec['credit']}</text>
      {cover_art(spec['art'])}
    </svg>'''
    output.write_text(svg)


def card(item: dict, featured: bool = False) -> str:
    e = lambda value: html.escape(str(value), quote=True)
    slug = e(item["slug"])
    image = f'<div class="feature-image"><img src="thumbs/{slug}.svg" alt="Cover for {e(item["title"])}" loading="lazy" decoding="async" width="1200" height="600"></div>' if featured else ""
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
    if not item.get("pdf"):
        return f"""
      <article class="{class_name}" data-kind="{e(item['kind'])}" id="work-{slug}">
        <div class="card-content">
          <div class="card-meta"><span>{e(LABELS[item['kind']])}</span><span>{e(item['published'])}</span></div>
          <div class="card-title-row"><span class="protocol-logo" aria-hidden="true"><img src="{e(item['logo'])}" alt="" width="58" height="58" loading="lazy" decoding="async"></span><h3>{e(item['title'])}</h3></div>
          <p>{e(item['summary'])}</p>
          <div class="card-bottom"><span>{e(item['access'])}</span><div class="card-links">
            <a class="primary-link" href="{e(item['source'])}" target="_blank" rel="noopener">Open report <span aria-hidden="true">↗</span></a>
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
            {source_link}
          </div></div>
        </div>
      </article>"""


def stocklens_card() -> str:
    app = html.escape(STOCKLENS["app"], quote=True)
    code = html.escape(STOCKLENS["code"], quote=True)
    return f"""
      <article class="work-card featured-card featured-product" id="work-stocklens">
        <div class="feature-image"><img src="thumbs/stocklens.svg" alt="Stocklens cover: tokenized stock versions under a lens" loading="lazy" decoding="async" width="1200" height="600"></div>
        <div class="card-content">
          <div class="card-meta"><span>Live product</span><span>Personal project</span></div>
          <div class="card-title-row"><span class="protocol-logo" aria-hidden="true"><img src="logos/stocklens.svg" alt="" width="58" height="58" loading="lazy" decoding="async"></span><h3>Stocklens</h3></div>
          <p>Compare tokenized versions of the same stock by issuer, network, price, liquidity, and product terms.</p>
          <div class="card-bottom"><span>Live app</span><div class="card-links">
            <a class="primary-link" href="{app}" target="_blank" rel="noopener">Open app <span aria-hidden="true">↗</span></a>
            <a href="{code}" target="_blank" rel="noopener">View code <span aria-hidden="true">↗</span></a>
          </div></div>
        </div>
      </article>"""


def main() -> None:
    items = load_items()
    for item in items:
        make_featured_cover(item)
    make_featured_cover(STOCKLENS)
    featured = stocklens_card() + "\n" + "\n".join(card(next(item for item in items if item["slug"] == slug), featured=True) for slug in FEATURED)
    library = "\n".join(card(item) for item in items)
    counts = {kind: sum(item["kind"] == kind for item in items) for kind in LABELS}
    doc = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#102c34">
  <meta name="description" content="Selected sector and quarterly reports, strategies, investment theses, memos, IR decks, financial models, data rooms, and tools by Dimitris Pechlivanidis.">
  <meta property="og:title" content="Dimitris Pechlivanidis — Research & Data">
  <meta property="og:description" content="Sector and quarterly reports, strategies, investment theses, memos, financial models, data rooms, and analytical tools.">
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
          <h1 id="hero-title">Dimitris<br><em>Pechlivanidis.</em></h1>
          <div class="hero-actions"><a class="button button-light" href="#selected">Explore the work <span aria-hidden="true">↓</span></a><a class="text-link" href="https://github.com/0xDimi" target="_blank" rel="noopener">GitHub profile <span aria-hidden="true">↗</span></a></div>
        </div>
        <div class="hero-aside" aria-label="Portfolio sections">
          <div class="aside-label">INDEX / 2025—2026</div>
          <a href="#library" data-jump-filter="sector_reports"><span>1</span><strong>Sector Wide Reports</strong><span aria-hidden="true">↗</span></a>
          <a href="#library" data-jump-filter="quarterly_reports"><span>2</span><strong>Quarterly Reports</strong><span aria-hidden="true">↗</span></a>
          <a href="#library" data-jump-filter="theses"><span>3</span><strong>Investment theses</strong><span aria-hidden="true">↗</span></a>
          <a href="#library" data-jump-filter="memos"><span>4</span><strong>Investment memos</strong><span aria-hidden="true">↗</span></a>
          <a href="#library" data-jump-filter="blueprints"><span>5</span><strong>IR decks</strong><span aria-hidden="true">↗</span></a>
          <a href="#library" data-jump-filter="financial_models"><span>6</span><strong>Financial Models</strong><span aria-hidden="true">↗</span></a>
          <a href="#library" data-jump-filter="data_rooms"><span>7</span><strong>Data Rooms</strong><span aria-hidden="true">↗</span></a>
          <a href="#tools"><span>8</span><strong>Data tools</strong><span aria-hidden="true">↗</span></a>
        </div>
      </div>
    </section>

    <section class="section selected-section" id="selected" aria-labelledby="selected-title">
      <div class="container">
        <div class="section-heading"><div><p class="section-no">1 / START HERE</p><h2 id="selected-title">Selected work</h2></div></div>
        <div class="featured-grid">{featured}</div>
      </div>
    </section>

    <section class="section library-section" id="library" aria-labelledby="library-title">
      <div class="container">
        <div class="section-heading"><div><p class="section-no">2 / FULL LIBRARY</p><h2 id="library-title">Work Samples</h2></div><p class="sample-note">A small selection from more than 50 reports I've produced across Alea Research and Revelo.</p></div>
        <div class="filter-bar" role="group" aria-label="Filter research by type">
          <button class="filter active" type="button" data-filter="all" data-description="{html.escape(CATEGORY_DESCRIPTIONS['all'], quote=True)}" aria-pressed="true">All <span>{len(items)}</span></button>
          <button class="filter" type="button" data-filter="collaboration" data-description="{html.escape(CATEGORY_DESCRIPTIONS['collaboration'], quote=True)}" aria-pressed="false">Collaboration <span>{counts['collaboration']}</span></button>
          <button class="filter" type="button" data-filter="sector_reports" data-description="{html.escape(CATEGORY_DESCRIPTIONS['sector_reports'], quote=True)}" aria-pressed="false">Sector Wide Reports <span>{counts['sector_reports']}</span></button>
          <button class="filter" type="button" data-filter="quarterly_reports" data-description="{html.escape(CATEGORY_DESCRIPTIONS['quarterly_reports'], quote=True)}" aria-pressed="false">Quarterly Reports <span>{counts['quarterly_reports']}</span></button>
          <button class="filter" type="button" data-filter="strategies" data-description="{html.escape(CATEGORY_DESCRIPTIONS['strategies'], quote=True)}" aria-pressed="false">Strategies <span>{counts['strategies']}</span></button>
          <button class="filter" type="button" data-filter="theses" data-description="{html.escape(CATEGORY_DESCRIPTIONS['theses'], quote=True)}" aria-pressed="false">Theses <span>{counts['theses']}</span></button>
          <button class="filter" type="button" data-filter="memos" data-description="{html.escape(CATEGORY_DESCRIPTIONS['memos'], quote=True)}" aria-pressed="false">Memos <span>{counts['memos']}</span></button>
          <button class="filter" type="button" data-filter="blueprints" data-description="{html.escape(CATEGORY_DESCRIPTIONS['blueprints'], quote=True)}" aria-pressed="false">IR decks <span>{counts['blueprints']}</span></button>
          <button class="filter" type="button" data-filter="financial_models" data-description="{html.escape(CATEGORY_DESCRIPTIONS['financial_models'], quote=True)}" aria-pressed="false">Financial Models <span>{counts['financial_models']}</span></button>
          <button class="filter" type="button" data-filter="data_rooms" data-description="{html.escape(CATEGORY_DESCRIPTIONS['data_rooms'], quote=True)}" aria-pressed="false">Data Rooms <span>{counts['data_rooms']}</span></button>
        </div>
        <p class="category-description" id="category-description" aria-live="polite">{html.escape(CATEGORY_DESCRIPTIONS['all'])}</p>
        <div class="library-grid" id="work-grid">{library}</div>
        <p class="library-note">Reports link to published originals where available. The Stacks benchmark retains its commissioned-research disclosure, and the personal report shows its data cutoff. Market views reflect the dates shown.</p>
      </div>
    </section>

    <section class="section tools-section" id="tools" aria-labelledby="tools-title">
      <div class="container">
        <div class="section-heading"><div><p class="section-no">3 / BUILT WORK</p><h2 id="tools-title">Data & product tools</h2></div><p>Tools to compare markets, build charts, and test product ideas.</p></div>
        <article class="tool-feature" aria-labelledby="stocklens-tool-title">
          <div class="tool-feature-copy">
            <span class="tool-index">A / TOKENIZED EQUITIES</span>
            <h3 id="stocklens-tool-title">Stocklens</h3>
            <p class="tool-feature-lead">One stock. Compare its tokens.</p>
            <p>Find tokenized versions across issuers and networks, inspect their prices, liquidity, and terms, then open a venue to check its current quote.</p>
            <div class="tool-links"><a href="{html.escape(STOCKLENS['app'], quote=True)}" target="_blank" rel="noopener">Open live app ↗</a><a href="{html.escape(STOCKLENS['code'], quote=True)}" target="_blank" rel="noopener">View code ↗</a></div>
          </div>
          <figure class="tool-feature-image"><img src="images/stocklens-interface.webp" alt="Stocklens app comparing tokenized versions of NVIDIA across issuers and networks" loading="lazy" decoding="async" width="1200" height="768"><figcaption>Interface captured October 19, 2026 · Open the app for current data.</figcaption></figure>
        </article>
        <div class="tool-grid">
          <article class="tool-card"><span class="tool-index">B / DATA VISUALIZATION</span><h3>Atlas Chart Builder</h3><p>A CSV chart builder for research data, with chart export and configurable data sources.</p><div class="tool-links"><a href="https://github.com/0xDimi/atlas-chart-builder" target="_blank" rel="noopener">View code ↗</a></div></article>
          <article class="tool-card"><span class="tool-index">C / MARKET SCREENING</span><h3>Alea Signal</h3><p>A Polymarket researchability screener for crypto, finance, and economy markets.</p><p class="tool-status">Currently inactive</p><div class="tool-links"><a href="https://alea-signal.vercel.app/" target="_blank" rel="noopener">Open preview ↗</a><a href="https://github.com/0xDimi/alea-signal" target="_blank" rel="noopener">View code ↗</a></div></article>
          <article class="tool-card"><span class="tool-index">D / PRODUCT PROTOTYPE</span><h3>MANTIS</h3><p>A Greek-first prediction-market product prototype. Demo only; no real-money trading.</p><p class="tool-status">Currently inactive</p><div class="tool-links"><a href="https://mantis-demo.xyz/" target="_blank" rel="noopener">Open demo ↗</a><a href="https://github.com/0xDimi/MANTIS" target="_blank" rel="noopener">View code ↗</a></div></article>
        </div>
      </div>
    </section>
    <section class="section about-section" id="about" aria-labelledby="about-title">
      <div class="container about-grid">
        <div class="about-heading"><p class="section-no">4 / THE PERSON BEHIND THE WORK</p><h2 id="about-title">About</h2><div class="about-rule" aria-hidden="true"></div></div>
        <div class="about-copy">
          <p class="about-lead">Give a damn and you'll be great.</p>
          <p>I've evaluated more than 60 businesses and protocols, sourced at least 20 blockchain startups, and invested to some of them. I've also invested in robotics and AI companies. Skin in the game matters to me. I put my conviction up for judgment, test the assumptions behind it, and change my thesis when the evidence calls for it.</p>
          <p>During my first role at Revelo Intel, I helped raise $1.3 million in syndicate capital across three early-stage investments.</p>
          <p>Client work matters just as much at the same time. At Alea, I've sourced and closed four client engagements, building relationships from the first conversation through to a signed deal. I've also helped teams raise money, shape GTM strategies and business models, plan incentive campaigns, and prepare investor materials.</p>
          <p>Before research, I spent twelve years in competitive football and five years in sales in Greece. Both taught me to care about the result. A match ends. A client buys or walks away. I bring that same drive and accountability to investing and every client relationship.</p>
          <p class="about-thesis"><span>University thesis</span> · <a href="https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4708467" target="_blank" rel="noopener">The Case of Venture DAOs and the Future of Decentralized Venture Capital <span aria-hidden="true">↗</span></a></p>
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
