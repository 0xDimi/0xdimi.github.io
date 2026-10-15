"""Publish the author-supplied Circle PDF and its embedded editable workbook."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "docs"
SOURCE = ROOT / "source-pdfs" / "circle-financial-model-original.pdf"
EXPECTED_SHA256 = "b224e59d858aa36c73ff12c279feb97229d424cca885b95107dc2ab92d7ed052"


def main() -> None:
    source_bytes = SOURCE.read_bytes()
    if hashlib.sha256(source_bytes).hexdigest() != EXPECTED_SHA256:
        raise RuntimeError("Circle PDF differs from the reviewed author-supplied file")

    with fitz.open(stream=source_bytes, filetype="pdf") as pdf:
        if len(pdf) != 19 or pdf.embfile_count() != 1:
            raise RuntimeError("Circle PDF page count or embedded workbook changed")
        cover = pdf[0].get_text()
        if "October 14, 2026" not in cover or "@demetriusweb3" not in cover:
            raise RuntimeError("Circle PDF cover date or attribution is missing")
        if pdf.embfile_info(0)["filename"] != "Circle-financial-model.xlsx":
            raise RuntimeError("Unexpected Circle PDF attachment")
        workbook = pdf.embfile_get(0)

    pdf_output = SITE / "pdfs" / "circle-financial-model.pdf"
    model_output = SITE / "models" / "circle-financial-model.xlsx"
    pdf_output.parent.mkdir(parents=True, exist_ok=True)
    model_output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SOURCE, pdf_output)
    model_output.write_bytes(workbook)

    item = {
        "kind": "financial_models",
        "slug": "circle-financial-model",
        "title": "Circle Financial Model",
        "subtitle": "USDC Growth, Interest Rates and Equity Valuation",
        "published": "October 14, 2026",
        "source": None,
        "provenance": "personal",
        "pdf": "pdfs/circle-financial-model.pdf",
        "workbook": "models/circle-financial-model.xlsx",
        "pages": 19,
        "bytes": len(source_bytes),
    }
    (SITE / "financial_models.json").write_text(json.dumps([item], indent=2) + "\n")
    print(f"Published {pdf_output} and {model_output}")


if __name__ == "__main__":
    main()
