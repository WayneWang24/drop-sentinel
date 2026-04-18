"""Shopify store scraper for Pop Mart international sites."""
from __future__ import annotations

import logging
from datetime import datetime

import httpx

from drop_sentinel.helpers.rate_limiter import RateLimiter
from drop_sentinel.models import Platform, Product, Variant
from drop_sentinel.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

# Shopify public endpoints (no auth required)
PRODUCTS_ENDPOINT = "/products.json?limit=250&page={page}"
PRODUCT_ENDPOINT = "/products/{handle}.js"


class ShopifyScraper(BaseScraper):
    """Scraper for Shopify-based stores (Pop Mart international)."""

    def __init__(
        self,
        base_url: str,
        store_name: str = "popmart",
        user_agent: str = "DropSentinel/0.1",
        rate_limiter: RateLimiter | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.store_name = store_name
        self.user_agent = user_agent
        self.rate_limiter = rate_limiter or RateLimiter()

    def get_platform(self) -> Platform:
        return Platform.POPMART

    async def fetch_products(self, **kwargs) -> list[Product]:
        """Fetch all products from the Shopify store via public /products.json."""
        all_products: list[Product] = []
        page = 1

        async with httpx.AsyncClient(
            headers={"User-Agent": self.user_agent},
            timeout=30.0,
            follow_redirects=True,
        ) as client:
            while True:
                await self.rate_limiter.acquire()
                url = f"{self.base_url}{PRODUCTS_ENDPOINT.format(page=page)}"
                logger.info(f"Fetching {url}")

                try:
                    resp = await client.get(url)
                    resp.raise_for_status()
                except httpx.HTTPStatusError as e:
                    logger.warning(f"HTTP {e.response.status_code} from {url}")
                    break
                except httpx.RequestError as e:
                    logger.error(f"Request failed: {e}")
                    break

                data = resp.json()
                products_data = data.get("products", [])

                if not products_data:
                    break

                for p in products_data:
                    product = self._parse_product(p)
                    if product:
                        all_products.append(product)

                page += 1
                # Safety: don't fetch more than 20 pages (5000 products)
                if page > 20:
                    break

        logger.info(f"Fetched {len(all_products)} products from {self.store_name}")
        return all_products

    async def check_product(self, product_handle: str) -> Product | None:
        """Check a single product by its handle via /products/{handle}.js."""
        await self.rate_limiter.acquire()
        url = f"{self.base_url}{PRODUCT_ENDPOINT.format(handle=product_handle)}"

        async with httpx.AsyncClient(
            headers={"User-Agent": self.user_agent},
            timeout=30.0,
            follow_redirects=True,
        ) as client:
            try:
                resp = await client.get(url)
                resp.raise_for_status()
            except httpx.HTTPError as e:
                logger.error(f"Failed to check product {product_handle}: {e}")
                return None

            data = resp.json()
            return self._parse_product(data)

    def _parse_product(self, data: dict) -> Product | None:
        """Parse a Shopify product JSON into our Product model."""
        try:
            variants = []
            for v in data.get("variants", []):
                variants.append(Variant(
                    id=str(v.get("id", "")),
                    title=v.get("title", ""),
                    price=float(v.get("price", 0)),
                    currency="USD",  # Shopify returns price as string
                    available=v.get("available", False),
                    sku=v.get("sku", ""),
                ))

            # Build product URL
            handle = data.get("handle", "")
            product_url = f"{self.base_url}/products/{handle}" if handle else ""

            # Get first image
            images = data.get("images", [])
            image_url = ""
            if images:
                if isinstance(images[0], dict):
                    image_url = images[0].get("src", "")
                elif isinstance(images[0], str):
                    image_url = images[0]

            created_at = None
            if ts := data.get("created_at"):
                try:
                    created_at = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    pass

            updated_at = None
            if ts := data.get("updated_at"):
                try:
                    updated_at = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    pass

            return Product(
                id=str(data.get("id", "")),
                platform=Platform.POPMART,
                title=data.get("title", ""),
                url=product_url,
                image_url=image_url,
                variants=variants,
                tags=data.get("tags", []),
                created_at=created_at,
                updated_at=updated_at,
            )
        except Exception as e:
            logger.warning(f"Failed to parse product: {e}")
            return None
