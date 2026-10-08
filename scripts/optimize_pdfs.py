"""Reduce article PDF size without changing text, links, or page layout."""

from __future__ import annotations

import json
from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "docs"


def evidence(pdf: fitz.Document) -> tuple[int, int, int, int]:
    return (
        len(pdf),
        sum(len(page.get_text()) for page in pdf),
        sum(len(page.get_links()) for page in pdf),
        sum(len(page.get_images()) for page in pdf),
    )


def optimize(path: Path) -> tuple[int, int]:
    before = path.stat().st_size
    output = path.with_suffix(".optimized.pdf")
    with fitz.open(path) as source:
        expected = evidence(source)
        source.rewrite_images(dpi_target=190, quality=82)
        source.save(output, garbage=4, deflate=True)
    with fitz.open(output) as result:
        actual = evidence(result)
        if actual != expected:
            output.unlink()
            raise RuntimeError(f"PDF evidence changed: {path} {expected} -> {actual}")
    after = output.stat().st_size
    if after < before:
        output.replace(path)
    else:
        output.unlink()
        after = before
    return before, after


def main() -> None:
    articles = json.loads((SITE / "articles.json").read_text())
    saved = 0
    for item in articles:
        path = SITE / item["pdf"]
        before, after = optimize(path)
        item["bytes"] = after
        saved += before - after
        print(f"{path.name}: {before / 1024 / 1024:.1f} -> {after / 1024 / 1024:.1f} MiB")
    (SITE / "articles.json").write_text(json.dumps(articles, indent=2) + "\n")
    print(f"Saved {saved / 1024 / 1024:.1f} MiB")


if __name__ == "__main__":
    main()
