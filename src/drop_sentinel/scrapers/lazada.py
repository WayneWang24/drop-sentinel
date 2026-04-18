"""Lazada product page scraper for Pop Mart SEA stores."""
from __future__ import annotations

import logging
import re
from datetime import datetime

import httpx

from drop_sentinel.helpers.rate_limiter import RateLimiter
from drop_sentinel.models import Platform, Product, Variant
from drop_sentinel.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

# Lazada Pop Mart official stores by country
DEFAULT_STORES = {
    "th": "https://www.lazada.co.th/shop/pop-mart-official-store",
    "sg": "https://www.lazada.sg/shop/pop-mart-official-store",
    "my": "https://www.lazada.com.my/shop/pop-mart-official-store",
    "ph": "https://www.lazada.com.ph/shop/pop-mart-official-store",
}


class LazadaScraper(BaseScraper):
    """Scraper for Lazada Pop Mart official stores.

    Monitors public store pages for product availability.
    Note: Lazada has anti-bot protection. This scraper may need
    proxy rotation for reliability in production.
    """

    def __init__(
        self,
        stores: dict[str, str] | None = None,
        user_agent: str = "DropSentinel/0.1",
        rate_limiter: RateLimiter | None = None,
    ):
        self.stores = stores or DEFAULT_STORES
        self.user_agent = user_agent
        self.rate_limiter = rate_limiter or RateLimiter()

    def get_platform(self) -> Platform:
        return Platform.LAZADA

    async def fetch_products(self, **kwargs) -> list[Product]:
        """Fetch products from Lazada Pop Mart stores."""
        all_products: list[Product] = []

        async with httpx.AsyncClient(
            headers={
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
            },
            timeout=20.0,
            follow_redirects=True,
        ) as client:
            for country, store_url in self.stores.items():
                await self.rate_limiter.acquire()
                try:
                    products = await self._fetch_store(client, country, store_url)
                    all_products.extend(products)
                except Exception as e:
                    logger.warning(f"Failed to fetch Lazada {country}: {e}")

        logger.info(f"Fetched {len(all_products)} products from Lazada")
        return all_products

    async def check_product(self, product_id: str) -> Product | None:
        return None  # Individual product check not implemented

    async def _fetch_store(
        self, client: httpx.AsyncClient, country: str, store_url: str
    ) -> list[Product]:
        """Fetch products from a single Lazada store page."""
        try:
            resp = await client.get(store_url)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            logger.warning(f"Lazada {country} HTTP error: {e}")
            return []

        return self._parse_store_page(resp.text, country)

    def _parse_store_page(self, html: str, country: str) -> list[Product]:
        """Parse Lazada store page HTML for product data."""
        products = []

        # Lazada embeds product data in JSON within script tags
        # Look for __NEXT_DATA__ or similar JSON payloads
        json_patterns = [
            r'"listItems"\s*:\s*(\[.+?\])\s*[,}]',
            r'"items"\s*:\s*(\[.+?\])\s*[,}]',
        ]

        import json
        for pattern in json_patterns:
            matches = re.findall(pattern, html, re.DOTALL)
            for match in matches:
                try:
                    items = json.loads(match)
                    for item in items[:50]:  # Limit
                        product = self._parse_item(item, country)
                        if product:
                            products.append(product)
                except (json.JSONDecodeError, TypeError):
                    continue

        if not products:
            logger.debug(f"No structured data found in Lazada {country} page")

        return products

    def _parse_item(self, item: dict, country: str) -> Product | None:
        """Parse a single Lazada product item."""
        try:
            item_id = str(item.get("itemId", item.get("nid", "")))
            title = item.get("name", item.get("title", ""))
            if not item_id or not title:
                return None

            price = 0.0
            price_str = item.get("price", item.get("priceShow", "0"))
            try:
                price = float(re.sub(r"[^\d.]", "", str(price_str)))
            except (ValueError, TypeError):
                pass

            currency_map = {"th": "THB", "sg": "SGD", "my": "MYR", "ph": "PHP"}
            currency = currency_map.get(country, "USD")

            image = item.get("image", item.get("img", ""))
            url = item.get("itemUrl", item.get("productUrl", ""))
            if url and not url.startswith("http"):
                domain_map = {
                    "th": "https://www.lazada.co.th",
                    "sg": "https://www.lazada.sg",
                    "my": "https://www.lazada.com.my",
                    "ph": "https://www.lazada.com.ph",
                }
                url = domain_map.get(country, "") + url

            return Product(
                id=f"lazada_{country}_{item_id}",
                platform=Platform.LAZADA,
                title=title,
                url=url,
                image_url=image,
                variants=[Variant(
                    id=item_id,
                    title=f"Lazada {country.upper()}",
                    price=price,
                    currency=currency,
                    available=True,  # Listed = available
                )],
                tags=[f"lazada_{country}"],
            )
        except Exception as e:
            logger.debug(f"Failed to parse Lazada item: {e}")
            return None
