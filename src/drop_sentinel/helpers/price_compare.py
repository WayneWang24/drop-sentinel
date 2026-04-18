"""Cross-platform price comparison utility."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from drop_sentinel.models import Product

logger = logging.getLogger(__name__)

# Approximate exchange rates to USD (updated periodically)
EXCHANGE_RATES = {
    "USD": 1.0,
    "SGD": 0.74,
    "THB": 0.028,
    "MYR": 0.22,
    "PHP": 0.018,
    "CNY": 0.14,
    "JPY": 0.0067,
    "KRW": 0.00075,
    "EUR": 1.08,
    "GBP": 1.26,
}


@dataclass
class PriceEntry:
    """A price point for comparison."""
    platform: str
    title: str
    price: float
    currency: str
    price_usd: float
    url: str
    available: bool


def compare_prices(products: list[Product]) -> list[PriceEntry]:
    """Compare prices across platforms, normalized to USD.

    Returns entries sorted by USD price (lowest first).
    """
    entries: list[PriceEntry] = []

    for p in products:
        for v in p.variants:
            if v.price <= 0:
                continue
            rate = EXCHANGE_RATES.get(v.currency, 1.0)
            entries.append(PriceEntry(
                platform=p.platform.value,
                title=p.title,
                price=v.price,
                currency=v.currency,
                price_usd=round(v.price * rate, 2),
                url=p.url,
                available=v.available,
            ))

    entries.sort(key=lambda e: (not e.available, e.price_usd))
    return entries


def format_comparison(entries: list[PriceEntry]) -> str:
    """Format price comparison as a readable table string."""
    if not entries:
        return "No prices to compare."

    lines = [
        f"{'Platform':<20} {'Price':>12} {'USD':>8} {'Status':<10} URL",
        "-" * 80,
    ]
    for e in entries:
        status = "In Stock" if e.available else "Sold Out"
        lines.append(
            f"{e.platform:<20} {e.price:>8.2f} {e.currency:<3} "
            f"${e.price_usd:>6.2f}  {status:<10} {e.url}"
        )
    return "\n".join(lines)
