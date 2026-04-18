"""Shopee product page scraper for Pop Mart SEA stores."""
from __future__ import annotations

import json
import logging
import re

import httpx

from drop_sentinel.helpers.rate_limiter import RateLimiter
from drop_sentinel.models import Platform, Product, Variant
from drop_sentinel.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

# Shopee Pop Mart official stores
DEFAULT_STORES = {
    "th": "https://shopee.co.th/popmartofficial.th",
    "sg": "https://shopee.sg/popmart.sg",
    "my": "https://shopee.com.my/popmart.my",
}


class ShopeeScraper(BaseScraper):
    """Scraper for Shopee Pop Mart official stores.

    Monitors public store pages. Shopee uses heavy anti-bot measures,
    so this scraper focuses on public store profile pages.
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
        return Platform.SHOPEE

    async def fetch_products(self, **kwargs) -> list[Product]:
        """Fetch products from Shopee Pop Mart stores."""
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
                    logger.warning(f"Failed to fetch Shopee {country}: {e}")

        logger.info(f"Fetched {len(all_products)} products from Shopee")
        return all_products

    async def check_product(self, product_id: str) -> Product | None:
        return None

    async def _fetch_store(
        self, client: httpx.AsyncClient, country: str, store_url: str
    ) -> list[Product]:
        """Fetch products from a single Shopee store."""
        try:
            resp = await client.get(store_url)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            logger.warning(f"Shopee {country} HTTP error: {e}")
            return []

        return self._parse_store_page(resp.text, country)

    def _parse_store_page(self, html: str, country: str) -> list[Product]:
        """Parse Shopee store page for product data."""
        products = []

        # Shopee renders client-side, but may have JSON in script tags
        json_patterns = [
            r'"items"\s*:\s*(\[.+?\])',
            r'"data"\s*:\s*(\{.+?"items"\s*:\s*\[.+?\]\})',
        ]

        for pattern in json_patterns:
            matches = re.findall(pattern, html, re.DOTALL)
            for match in matches:
                try:
                    data = json.loads(match)
                    items = data if isinstance(data, list) else data.get("items", [])
                    for item in items[:50]:
                        product = self._parse_item(item, country)
                        if product:
                            products.append(product)
                except (json.JSONDecodeError, TypeError):
                    continue

        if not products:
            logger.debug(f"No structured data found in Shopee {country} page (client-side rendered)")

        return products

    def _parse_item(self, item: dict, country: str) -> Product | None:
        """Parse a single Shopee product item."""
        try:
            item_id = str(item.get("itemid", item.get("item_id", "")))
            shop_id = str(item.get("shopid", item.get("shop_id", "")))
            title = item.get("name", item.get("title", ""))
            if not item_id or not title:
                return None

            # Shopee prices are in cents (multiply by 100000 in some regions)
            price = 0.0
            raw_price = item.get("price", item.get("price_min", 0))
            try:
                price = float(raw_price) / 100000
            except (ValueError, TypeError):
                pass

            currency_map = {"th": "THB", "sg": "SGD", "my": "MYR"}
            currency = currency_map.get(country, "USD")

            image = item.get("image", "")
            if image and not image.startswith("http"):
                image = f"https://cf.shopee.co.th/file/{image}"

            domain_map = {
                "th": "https://shopee.co.th",
                "sg": "https://shopee.sg",
                "my": "https://shopee.com.my",
            }
            base = domain_map.get(country, "")
            url = f"{base}/product/{shop_id}/{item_id}" if base else ""

            stock = item.get("stock", 1)

            return Product(
                id=f"shopee_{country}_{item_id}",
                platform=Platform.SHOPEE,
                title=title,
                url=url,
                image_url=image,
                variants=[Variant(
                    id=item_id,
                    title=f"Shopee {country.upper()}",
                    price=price,
                    currency=currency,
                    available=stock > 0,
                )],
                tags=[f"shopee_{country}"],
            )
        except Exception as e:
            logger.debug(f"Failed to parse Shopee item: {e}")
            return None
