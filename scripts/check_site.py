"""Validate built PDFs, data room links, and the static portfolio index."""

from __future__ import annotations

import json
import hashlib
from pathlib import Path

import fitz
from bs4 import BeautifulSoup
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "docs"


def main() -> None:
    manifest = json.loads((SITE / "manifest.json").read_text())
    if len(manifest) != 36:
        raise RuntimeError(f"Expected 36 work samples, found {len(manifest)}")
    aave = next((item for item in manifest if item["slug"] == "aave"), None)
    if not aave or aave["kind"] != "memos" or aave["published"] != "February 26, 2026" or aave["source"] != "https://alearesearch.io/reports/memos/aave" or aave.get("provenance") != "alea":
        raise RuntimeError("Aave memo metadata is missing or incorrect")
    models = [item for item in manifest if item["kind"] == "financial_models"]
    if len(models) != 1 or models[0]["slug"] != "circle-financial-model" or models[0]["published"] != "October 14, 2026" or models[0].get("provenance") != "personal":
        raise RuntimeError("Circle financial model metadata is missing or incorrect")
    quarterly_sources = {
        "etherfi-q1-2026": "https://alearesearch.io/reports/benchmark/etherfi-q1-2026",
        "threshold-q1-26": "https://alearesearch.io/reports/benchmark/threshold-q1-26",
        "stacks-q3-2026": None,
        "crypto-etfs-q3-2026": None,
        "robinhood-chain-q3-2026": None,
        "prediction-markets-q3-2026": None,
    }
    quarterly_items = {item["slug"]: item for item in manifest if item["kind"] == "quarterly_reports"}
    if set(quarterly_items) != set(quarterly_sources):
        raise RuntimeError("Quarterly Reports category is incomplete")
    if any(quarterly_items[slug]["source"] != source for slug, source in quarterly_sources.items()):
        raise RuntimeError("Quarterly report source URL mismatch")
    stacks = quarterly_items["stacks-q3-2026"]
    if stacks.get("provenance") != "alea_commissioned" or stacks.get("client") != "Stacks" or stacks["published"] is not None or stacks.get("date_label") != "Q3 2026":
        raise RuntimeError("Stacks attribution or reporting date is incorrect")
    for slug in ("crypto-etfs-q3-2026", "robinhood-chain-q3-2026"):
        item = quarterly_items[slug]
        if item.get("provenance") != "author_supplied" or item["published"] is not None or item.get("date_label") != "Q3 2026":
            raise RuntimeError(f"Author-supplied report attribution or period is incorrect: {slug}")
    prediction_markets = quarterly_items["prediction-markets-q3-2026"]
    if prediction_markets.get("provenance") != "personal" or prediction_markets["published"] is not None or prediction_markets.get("date_label") != "Q3 2026" or prediction_markets["title"] != "State of Prediction Markets: Q3 2026":
        raise RuntimeError("Prediction markets report attribution, title, or reporting period is incorrect")
    sector_sources = {
        "tokenized-stocks-ecosystem-2026": None,
        "rwa-perpetuals": "https://alearesearch.io/reports/perspectives/rwa-perpetuals",
        "when-agents-pay": "https://alearesearch.io/reports/perspectives/when-agents-pay",
        "cross-asset-markets": "https://alearesearch.io/reports/blueprints/cross-asset-markets",
    }
    sector_items = {item["slug"]: item for item in manifest if item["kind"] == "sector_reports"}
    if set(sector_items) != set(sector_sources):
        raise RuntimeError("Sector Wide Reports category is incomplete")
    if any(sector_items[slug]["source"] != source for slug, source in sector_sources.items()):
        raise RuntimeError("Sector report source URL mismatch")
    personal = sector_items["tokenized-stocks-ecosystem-2026"]
    if personal.get("provenance") != "personal" or personal["published"] is not None:
        raise RuntimeError("Personal sector report attribution or date is incorrect")
    axil = next((item for item in manifest if item["slug"] == "axil-prime-credit-3m"), None)
    if not axil or axil["kind"] != "strategies" or axil["source"] != "https://alearesearch.io/reports/perspectives/axil-prime-credit-3m":
        raise RuntimeError("Axil public strategy is missing or misclassified")
    soup = BeautifulSoup((SITE / "index.html").read_text(), "html.parser")
    cards = soup.select("#work-grid article.work-card")
    if len(cards) != len(manifest):
        raise RuntimeError("Index and manifest publication counts differ")
    if soup.select("a[download]") or "Download model" in soup.get_text():
        raise RuntimeError("Portfolio still offers a download link")
    if soup.select_one('[data-filter="perspectives"]') or not soup.select_one('[data-filter="strategies"]'):
        raise RuntimeError("Perspectives filter was not renamed Strategies")
    filters = [button["data-filter"] for button in soup.select(".filter-bar [data-filter]")]
    if filters[-3:] != ["blueprints", "financial_models", "data_rooms"] or "Alea Data Rooms" in soup.get_text():
        raise RuntimeError("Financial Models and Data Rooms are not in category order")
    if any(not button.get("data-description") for button in soup.select(".filter-bar [data-filter]")):
        raise RuntimeError("A portfolio category has no description")
    if not soup.select_one("#category-description"):
        raise RuntimeError("Category description has no display element")
    jump_filters = [link.get("data-jump-filter") for link in soup.select(".hero-aside a")]
    if jump_filters[-3:-1] != ["financial_models", "data_rooms"]:
        raise RuntimeError("Hero index is missing Financial Models or Data Rooms")
    rooms = [item for item in manifest if item["kind"] == "data_rooms"]
    if [item["title"] for item in rooms] != ["Tempo", "Aave", "Hyperliquid", "Morpho", "Polymarket", "Derive"]:
        raise RuntimeError("Data Rooms category is incomplete or out of order")
    if rooms[-1]["url"] != "https://derive.alearesearch.io/analytics?subtab=fees&tab=custom-economics":
        raise RuntimeError("Derive data room does not use the requested URL")
    if not soup.select_one('a[href="https://meditationsbyd.substack.com/"]'):
        raise RuntimeError("Substack link is missing")
    total_bytes = 0
    pdf_count = 0
    for item in manifest:
        logo = SITE / item["logo"]
        if not logo.is_file():
            raise RuntimeError(f"Missing logo: {logo}")
        if logo.suffix != ".svg":
            with Image.open(logo) as image:
                if min(image.size) < 180:
                    raise RuntimeError(f"Logo resolution is too low: {logo} ({image.size})")
        for section in ("#selected", "#work-grid"):
            card = soup.select_one(f"{section} #work-{item['slug']}")
            if card is not None and not card.select_one(f'.protocol-logo img[src="{item["logo"]}"]'):
                raise RuntimeError(f"Card has no matching logo: {item['slug']}")
        if item["kind"] == "data_rooms":
            room_link = soup.select_one(f"#work-{item['slug']} a.primary-link")
            if not room_link or room_link.get("href") != item["url"] or "pdf" in item:
                raise RuntimeError(f"Data room card is not a live-site link: {item['slug']}")
            if item["access"] not in soup.select_one(f"#work-{item['slug']}").get_text():
                raise RuntimeError(f"Data room access label is missing: {item['slug']}")
            continue
        pdf_count += 1
        path = SITE / item["pdf"]
        if not path.is_file() or path.read_bytes()[:5] != b"%PDF-":
            raise RuntimeError(f"Missing or invalid PDF: {path}")
        if not soup.select_one(f"#work-{item['slug']} a.primary-link[href='{item['pdf']}']"):
            raise RuntimeError(f"PDF has no library link: {path}")
        with fitz.open(path) as pdf:
            if len(pdf) != item["pages"]:
                raise RuntimeError(f"Manifest page count mismatch: {path}")
            if item.get("source") and not pdf[0].get_links():
                raise RuntimeError(f"Cover has no canonical-source link: {path}")
            if item["slug"] == "tokenized-stocks-ecosystem-2026":
                if soup.select_one(f"#work-{item['slug']} a:not(.primary-link)"):
                    raise RuntimeError("Personal report incorrectly has an Original link")
                handles = [page.get_text().count("@demetriusweb3") for page in pdf]
                if any(count < 1 for count in handles) or sum(count == 2 for count in handles) != item["watermarked_charts"]:
                    raise RuntimeError("Personal handle or chart watermarks are missing")
                for number in (17, 26):
                    old_mark_area = fitz.Rect(1825, 1005, 1888, 1055)
                    pixels = pdf[number - 1].get_pixmap(clip=old_mark_area, alpha=False)
                    if min(pixels.samples) < 250:
                        raise RuntimeError(f"Legacy Alea chart mark remains visible on page {number}")
            if item["slug"] == "stacks-q3-2026":
                if len(pdf) != 51 or "Work for Alea Research" not in pdf[0].get_text():
                    raise RuntimeError("Stacks cover or page count is incorrect")
                if "Alea Research is engaged in a commercial relationship with Stacks" not in pdf[-1].get_text():
                    raise RuntimeError("Stacks commissioned-research disclosure is missing")
                if soup.select_one(f"#work-{item['slug']} a:not(.primary-link)"):
                    raise RuntimeError("Stacks card links to a private source")
            if item["slug"] in ("crypto-etfs-q3-2026", "robinhood-chain-q3-2026"):
                if "Research by Dimitris Pechlivanidis" not in pdf[0].get_text():
                    raise RuntimeError(f"Author cover is missing: {item['slug']}")
                if soup.select_one(f"#work-{item['slug']} a:not(.primary-link)"):
                    raise RuntimeError(f"Private Google Doc is linked publicly: {item['slug']}")
            if item["slug"] == "prediction-markets-q3-2026":
                if hashlib.sha256(path.read_bytes()).hexdigest() != "f346ff4ae93110557ed7f9a2dd9d55851439c22742a936a6b29abd7248c6139f":
                    raise RuntimeError("Prediction markets PDF does not match the reviewed original")
                if len(pdf) != 14 or sum(len(page.get_links()) for page in pdf) != 57:
                    raise RuntimeError("Prediction markets PDF lost pages or source links")
                if "@demetriusweb3" not in pdf[0].get_text():
                    raise RuntimeError("Prediction markets PDF lacks author attribution")
                if soup.select_one(f"#work-{item['slug']} a:not(.primary-link)"):
                    raise RuntimeError("Prediction markets card links to a private source")
            if item["slug"] == "aave":
                body = " ".join(page.get_text() for page in list(pdf)[1:])
                if "Work for Alea Research" not in pdf[0].get_text() or "Cut below $85" not in body:
                    raise RuntimeError("Aave PDF attribution or ending is missing")
                if sum(len(page.get_links()) for page in pdf) < 26 or sum(len(page.get_images()) for page in pdf) < 11:
                    raise RuntimeError("Aave PDF lost citations or figures")
            if item["slug"] == "circle-financial-model":
                if hashlib.sha256(path.read_bytes()).hexdigest() != "b224e59d858aa36c73ff12c279feb97229d424cca885b95107dc2ab92d7ed052":
                    raise RuntimeError("Circle PDF does not match the reviewed original")
                if pdf.embfile_count() != 1 or pdf.embfile_info(0)["filename"] != "Circle-financial-model.xlsx":
                    raise RuntimeError("Circle embedded workbook is missing")
                if item.get("workbook") or (SITE / "models" / "circle-financial-model.xlsx").exists():
                    raise RuntimeError("Circle workbook is still separately published")
                if soup.select_one(f"#work-{item['slug']} a:not(.primary-link)"):
                    raise RuntimeError("Personal Circle report incorrectly has an Original link")
            for number, page in enumerate(pdf, 1):
                if not page.get_text().strip() and not page.get_images():
                    raise RuntimeError(f"Blank page in {path}: page {number}")
            if item["kind"] == "collaboration":
                text = " ".join(page.get_text() for page in pdf)
                if any(f"Chapter {number}" not in text for number in (2, 3, 8)):
                    raise RuntimeError("RedStone PDF is missing a credited chapter")
        total_bytes += path.stat().st_size
    for thumbnail in SITE.glob("thumbs/*.jpg"):
        if thumbnail.stat().st_size < 10_000:
            raise RuntimeError(f"Thumbnail appears broken: {thumbnail}")
    if soup.select(".performance, .performance-method"):
        raise RuntimeError("Performance section was not fully removed")
    if pdf_count != 30:
        raise RuntimeError(f"Expected 30 linked PDFs, found {pdf_count}")
    print(f"PASS: {pdf_count} linked PDFs and {len(rooms)} data rooms; all PDF pages nonblank; {total_bytes / 1024 / 1024:.1f} MiB total")


if __name__ == "__main__":
    main()
