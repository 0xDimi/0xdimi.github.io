"""Capture public Alea Figma slide decks as portfolio PDFs.

The public audience view is captured slide by slide so charts and layout stay
faithful to the published deck. A selectable-text cover supplies attribution.
"""

from __future__ import annotations

import argparse
import json
import re
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from PIL import Image
from playwright.sync_api import sync_playwright
from pypdf import PdfReader
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from build_articles import CHROME


ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = ROOT / "docs" / "pdfs"
TEMP_DIR = ROOT / "tmp" / "decks"
DECKS = [
    ("cross-asset-markets", "Cross-Asset Markets", "October 7, 2026"),
    ("steakhouse-financial", "Steakhouse Financial", "September 2, 2026"),
    ("re-protocol", "Re Protocol", "August 3, 2026"),
    ("theo", "Theo", "April 23, 2026"),
    ("usdai", "USD.AI", "March 2, 2026"),
]
SECTOR_DECKS = {"cross-asset-markets"}


def figma_embed_url(source: str) -> str:
    response = requests.get(source, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    frame = soup.select_one("main iframe[src*='figma.com']")
    if frame:
        return frame["src"]
    link = soup.select_one("main a[href^='https://www.figma.com/deck/']")
    if not link:
        raise RuntimeError(f"No public Figma deck at {source}")
    path = urlparse(link["href"]).path
    return f"https://embed.figma.com{path}?embed-host=share&footer=false&theme=dark"


def counter(page) -> tuple[int, int]:
    text = page.locator("body").inner_text()
    match = re.search(r"\b(\d+)\s*/\s*(\d+)\b", text)
    if not match:
        raise RuntimeError(f"Slide counter unavailable: {page.url}")
    return int(match.group(1)), int(match.group(2))


def capture_deck(browser, source: str, slug: str) -> list[Path]:
    page = browser.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=1.5)
    page.goto(figma_embed_url(source), wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(6500)
    try:
        page.get_by_role("button", name="Do not allow cookies").click(timeout=1500)
    except Exception:
        pass
    current, total = counter(page)
    if current != 1:
        page.keyboard.press("r")
        page.wait_for_timeout(900)
        current, total = counter(page)
    if current != 1 or total < 5:
        raise RuntimeError(f"Unexpected first slide: {current}/{total} at {source}")
    target_dir = TEMP_DIR / slug
    target_dir.mkdir(parents=True, exist_ok=True)
    images = []
    hashes = set()
    for slide_number in range(1, total + 1):
        page.wait_for_timeout(1050 if slide_number > 1 else 600)
        image_path = target_dir / f"{slide_number:03}.jpg"
        page.screenshot(path=str(image_path), type="jpeg", quality=90)
        digest = sha256(image_path.read_bytes()).hexdigest()
        if digest in hashes:
            raise RuntimeError(f"Duplicate slide capture: {slug} slide {slide_number}")
        hashes.add(digest)
        with Image.open(image_path) as image:
            if image.width != 2880 or image.height != 1620:
                raise RuntimeError(f"Wrong screenshot geometry: {image_path}")
        images.append(image_path)
        if slide_number < total:
            page.keyboard.press("ArrowRight")
            page.wait_for_function(
                "expected => /\\b(\\d+)\\s*\\/\\s*(\\d+)\\b/.test(document.body.innerText) && Number(document.body.innerText.match(/\\b(\\d+)\\s*\\/\\s*(\\d+)\\b/)[1]) === expected",
                arg=slide_number + 1,
                timeout=15000,
            )
    page.close()
    return images


def write_pdf(images: list[Path], title: str, published: str, source: str, target: Path, sector_report: bool = False) -> None:
    width, height = 960, 540
    pdf = canvas.Canvas(str(target), pagesize=(width, height), pageCompression=1)
    pdf.setTitle(f"{title} — Portfolio edition")
    pdf.setAuthor("Dimitris Pechlivanidis")
    pdf.setSubject("Selected Alea Research sector report" if sector_report else "Selected Alea Research deck")
    pdf.setFillColorRGB(0.063, 0.173, 0.204)
    pdf.rect(0, 0, width, height, stroke=0, fill=1)
    pdf.setStrokeColorRGB(0.80, 0.61, 0.33)
    pdf.rect(52, 452, 42, 42, stroke=1, fill=0)
    pdf.setFillColorRGB(0.85, 0.70, 0.46)
    pdf.setFont("Times-Roman", 18)
    pdf.drawString(59, 463, "DP")
    pdf.setFont("Helvetica", 9)
    pdf.drawRightString(908, 470, "SELECTED RESEARCH  /  SECTOR REPORT" if sector_report else "SELECTED RESEARCH  /  IR DECK")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(52, 335, "DIMITRIS PECHLIVANIDIS")
    pdf.setFillColorRGB(0.97, 0.96, 0.92)
    pdf.setFont("Times-Roman", 42)
    pdf.drawString(52, 260, title)
    pdf.setFont("Helvetica", 17)
    pdf.setFillColorRGB(0.72, 0.82, 0.83)
    pdf.drawString(52, 218, "Crypto, rates, and cross-asset market pricing" if sector_report else "Investor relations and business performance")
    pdf.setStrokeColorRGB(0.80, 0.61, 0.33)
    pdf.line(52, 188, 190, 188)
    pdf.setFont("Helvetica", 11)
    pdf.drawString(52, 158, f"Originally published by Alea Research  ·  {published}")
    pdf.setFont("Helvetica", 8)
    pdf.setFillColorRGB(0.72, 0.82, 0.83)
    pdf.drawString(52, 52, "Portfolio edition. Original slide design and Alea credit are preserved.")
    pdf.setFillColorRGB(0.95, 0.79, 0.56)
    pdf.drawRightString(908, 52, "Open original deck")
    pdf.linkURL(source, (800, 42, 910, 68), relative=0)
    pdf.showPage()
    for image_path in images:
        pdf.drawImage(ImageReader(str(image_path)), 0, 0, width=width, height=height, preserveAspectRatio=True, anchor="c")
        pdf.showPage()
    pdf.save()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", help="Build one deck by slug")
    args = parser.parse_args()
    selected = [deck for deck in DECKS if not args.only or deck[0] == args.only]
    if not selected:
        raise SystemExit(f"Unknown deck slug: {args.only}")
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=CHROME)
        try:
            for slug, title, published in selected:
                source = f"https://alearesearch.io/reports/blueprints/{slug}"
                images = capture_deck(browser, source, slug)
                target = PDF_DIR / f"{slug}.pdf"
                sector_report = slug in SECTOR_DECKS
                write_pdf(images, title, published, source, target, sector_report=sector_report)
                pages = len(PdfReader(str(target)).pages)
                if pages != len(images) + 1:
                    raise RuntimeError(f"PDF page count mismatch: {target}")
                result = {"kind": "sector_reports" if sector_report else "blueprints", "slug": slug, "title": title, "subtitle": "Crypto, rates, and cross-asset markets" if sector_report else "Investor relations deck", "published": published, "source": source, "pdf": f"pdfs/{slug}.pdf", "pages": pages, "figures": len(images), "bytes": target.stat().st_size}
                print(result, flush=True)
                results.append(result)
        finally:
            browser.close()
    metadata = ROOT / "docs" / "decks.json"
    if args.only and metadata.exists():
        known = {item["slug"]: item for item in json.loads(metadata.read_text())}
        known.update({item["slug"]: item for item in results})
        results = [known[slug] for slug, _, _ in DECKS if slug in known]
    metadata.write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    main()
