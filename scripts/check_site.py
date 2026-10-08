"""Validate built PDF outputs and the static portfolio index."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import fitz
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "docs"


def main() -> None:
    manifest = json.loads((SITE / "manifest.json").read_text())
    if len(manifest) != 16:
        raise RuntimeError(f"Expected 16 publications, found {len(manifest)}")
    soup = BeautifulSoup((SITE / "index.html").read_text(), "html.parser")
    cards = soup.select("#work-grid article.work-card")
    if len(cards) != len(manifest):
        raise RuntimeError("Index and manifest publication counts differ")
    if not soup.select_one('a[href="https://meditationsbyd.substack.com/"]'):
        raise RuntimeError("Substack link is missing")
    total_bytes = 0
    for item in manifest:
        path = SITE / item["pdf"]
        if not path.is_file() or path.read_bytes()[:5] != b"%PDF-":
            raise RuntimeError(f"Missing or invalid PDF: {path}")
        if not soup.select_one(f"#work-{item['slug']} a.primary-link[href='{item['pdf']}']"):
            raise RuntimeError(f"PDF has no library link: {path}")
        with fitz.open(path) as pdf:
            if len(pdf) != item["pages"]:
                raise RuntimeError(f"Manifest page count mismatch: {path}")
            if not pdf[0].get_links():
                raise RuntimeError(f"Cover has no canonical-source link: {path}")
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
    performance = json.loads((SITE / "performance.json").read_text())
    if len(performance["items"]) != 11:
        raise RuntimeError("Expected performance records for 11 theses and memos")
    as_of = date.fromisoformat(performance["as_of_utc"])
    for item in manifest:
        if item["kind"] not in {"theses", "memos"}:
            continue
        record = performance["items"][item["slug"]]
        if date.fromisoformat(record["published"]) != datetime.strptime(item["published"], "%B %d, %Y").date():
            raise RuntimeError(f"Publication date mismatch: {item['slug']}")
        if not soup.select_one(f"#work-{item['slug']} .performance"):
            raise RuntimeError(f"Performance display missing: {item['slug']}")
        if record["status"] != "verified":
            if item["slug"] != "polymarket":
                raise RuntimeError(f"Unexpected unavailable return: {item['slug']}")
            continue
        for name, end in (("first_30_days", date.fromisoformat(record["published"]) + timedelta(days=31)), ("since_publication", as_of + timedelta(days=1))):
            period = record[name]
            start = date.fromisoformat(period["start_utc"])
            if start != date.fromisoformat(record["published"]) + timedelta(days=1) or date.fromisoformat(period["end_utc"]) != end:
                raise RuntimeError(f"Incorrect holding window: {item['slug']} {name}")
            if period["holding_days"] != (end - start).days:
                raise RuntimeError(f"Incorrect holding period: {item['slug']} {name}")
            for prefix in ("token", "btc"):
                for suffix, day in (("start", start), ("end", end)):
                    point = period[f"{prefix}_{suffix}"]
                    observed = datetime.fromisoformat(point["observed_at_utc"])
                    target = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
                    if abs((observed - target).total_seconds()) > 7200 or point["usd"] <= 0 or not point["source"].startswith("https://coins.llama.fi/prices/historical/"):
                        raise RuntimeError(f"Invalid price evidence: {item['slug']} {name}")
            token_return = 100 * (period["token_end"]["usd"] / period["token_start"]["usd"] - 1)
            btc_return = 100 * (period["btc_end"]["usd"] / period["btc_start"]["usd"] - 1)
            if any(abs(a-b) > 1e-9 for a, b in ((token_return, period["token_return_pct"]), (btc_return, period["btc_return_pct"]), (token_return - btc_return, period["relative_to_btc_pp"]))):
                raise RuntimeError(f"Return calculation failed: {item['slug']} {name}")
    print(f"PASS: {len(manifest)} linked PDFs, all pages nonblank, source links present; {total_bytes / 1024 / 1024:.1f} MiB total")


if __name__ == "__main__":
    main()
