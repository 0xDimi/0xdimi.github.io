"""Publish the author-supplied Q3 prediction markets report without altering it."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source-pdfs" / "prediction-markets-q3-2026-original.pdf"
OUTPUT = ROOT / "docs" / "pdfs" / "prediction-markets-q3-2026.pdf"
METADATA = ROOT / "docs" / "author_exports.json"
SHA256 = "f346ff4ae93110557ed7f9a2dd9d55851439c22742a936a6b29abd7248c6139f"
SLUG = "prediction-markets-q3-2026"


def main() -> None:
    source_bytes = SOURCE.read_bytes()
    if hashlib.sha256(source_bytes).hexdigest() != SHA256:
        raise RuntimeError("Prediction markets PDF differs from the reviewed author-supplied file")

    with fitz.open(stream=source_bytes, filetype="pdf") as pdf:
        if len(pdf) != 14 or sum(len(page.get_links()) for page in pdf) != 57:
            raise RuntimeError("Prediction markets PDF page count or source links changed")
        cover = pdf[0].get_text()
        if "Prediction markets in Q3 2026" not in cover or "@demetriusweb3" not in cover:
            raise RuntimeError("Prediction markets report title or attribution is missing")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SOURCE, OUTPUT)
    record = {
        "kind": "quarterly_reports",
        "slug": SLUG,
        "title": "State of Prediction Markets: Q3 2026",
        "subtitle": "Kalshi, Polymarket, fee retention, and broker distribution",
        "published": None,
        "date_label": "Q3 2026",
        "sort_date": "October 17, 2026",
        "source": None,
        "pdf": "pdfs/prediction-markets-q3-2026.pdf",
        "pages": 14,
        "bytes": len(source_bytes),
        "provenance": "personal",
    }
    existing = json.loads(METADATA.read_text())
    updated = [item for item in existing if item["slug"] != SLUG]
    updated.append(record)
    METADATA.write_text(json.dumps(updated, indent=2) + "\n")
    print(f"Published {OUTPUT} ({len(source_bytes)} bytes)")


if __name__ == "__main__":
    main()
