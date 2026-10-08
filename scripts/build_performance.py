"""Snapshot token returns for Alea theses and memos using DefiLlama prices.

Publication timestamps are not public. Entry is 00:00 UTC on the day after
publication, so the full publication date has elapsed before measurement.
"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "docs"
PRICE_API = "https://coins.llama.fi/prices/historical"
ASSETS = {
    "hyperliquid": ("hyperliquid", "HYPE"),
    "ethena": ("ethena", "ENA"),
    "derive": ("derive", "DRV"),
    "ether-fi": ("ether-fi", "ETHFI"),
    "hyperliquid-2": ("hyperliquid", "HYPE"),
    "lit": ("lighter", "LIT"),
    "morpho": ("morpho", "MORPHO"),
    "vvv": ("venice-token", "VVV"),
    "near": ("near", "NEAR"),
    "zro": ("layerzero", "ZRO"),
}
BENCHMARK = ("bitcoin", "BTC")


def timestamp(day: date) -> int:
    return int(datetime(day.year, day.month, day.day, tzinfo=timezone.utc).timestamp())


def observation(session: requests.Session, day: date, asset: tuple[str, str]) -> dict:
    coin = f"coingecko:{asset[0]}"
    requested_at = timestamp(day)
    url = f"{PRICE_API}/{requested_at}/{coin}"
    response = session.get(url, timeout=30)
    response.raise_for_status()
    point = response.json().get("coins", {}).get(coin)
    if not point:
        raise ValueError(f"No price for {coin} at {day}")
    if point.get("symbol", "").upper() != asset[1]:
        raise ValueError(f"Wrong token for {coin} at {day}: {point.get('symbol')}")
    if abs(point["timestamp"] - requested_at) > 7200:
        raise ValueError(f"Stale price for {coin} at {day}: {point['timestamp']}")
    if point.get("confidence", 0) < 0.8 or point["price"] <= 0:
        raise ValueError(f"Low-confidence or invalid price for {coin} at {day}")
    return {"usd": point["price"], "observed_at_utc": datetime.fromtimestamp(point["timestamp"], timezone.utc).isoformat(), "confidence": point["confidence"], "source": url}


def period(session: requests.Session, start: date, end: date, asset: tuple[str, str]) -> dict:
    asset_start = observation(session, start, asset)
    asset_end = observation(session, end, asset)
    btc_start = observation(session, start, BENCHMARK)
    btc_end = observation(session, end, BENCHMARK)
    token_return = 100 * (asset_end["usd"] / asset_start["usd"] - 1)
    btc_return = 100 * (btc_end["usd"] / btc_start["usd"] - 1)
    return {
        "start_utc": start.isoformat(), "end_utc": end.isoformat(),
        "holding_days": (end - start).days,
        "token_start": asset_start, "token_end": asset_end,
        "btc_start": btc_start, "btc_end": btc_end,
        "token_return_pct": token_return, "btc_return_pct": btc_return,
        "relative_to_btc_pp": token_return - btc_return,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", type=date.fromisoformat, default=datetime.now(timezone.utc).date() - timedelta(days=1), help="Latest completed UTC day, YYYY-MM-DD")
    args = parser.parse_args()
    if args.as_of >= datetime.now(timezone.utc).date():
        raise ValueError("As-of must be a completed UTC day")
    articles = json.loads((SITE / "articles.json").read_text())
    snapshot = {
        "as_of_utc": args.as_of.isoformat(),
        "method": "USD spot observations nearest 00:00 UTC (within two hours) on the day after publication versus the day after the as-of date, and separately after 30 days. Relative return is token return minus BTC return in percentage points. Prices are DefiLlama historical observations; returns exclude fees, slippage, staking, dividends, and funding. This is token price performance, not a realized trade or a verdict on thesis quality.",
        "source_docs": "https://github.com/DefiLlama/api-sdk#prices",
        "items": {},
    }
    session = requests.Session()
    for article in articles:
        slug = article["slug"]
        published = datetime.strptime(article["published"], "%B %d, %Y").date()
        start = published + timedelta(days=1)
        if slug == "polymarket":
            snapshot["items"][slug] = {"status": "not_applicable", "reason": "The report discusses a potential POLY token; no identified traded token was available at publication.", "published": published.isoformat(), "asset": "POLY"}
            continue
        asset = ASSETS[slug]
        if start + timedelta(days=30) > args.as_of + timedelta(days=1):
            raise ValueError(f"No complete 30-day window for {slug}")
        snapshot["items"][slug] = {
            "status": "verified", "published": published.isoformat(),
            "asset": asset[1], "coin_id": f"coingecko:{asset[0]}",
            "since_publication": period(session, start, args.as_of + timedelta(days=1), asset),
            "first_30_days": period(session, start, start + timedelta(days=30), asset),
        }
        print(slug, round(snapshot["items"][slug]["since_publication"]["token_return_pct"], 1), round(snapshot["items"][slug]["since_publication"]["relative_to_btc_pp"], 1))
    (SITE / "performance.json").write_text(json.dumps(snapshot, indent=2) + "\n")


if __name__ == "__main__":
    main()
