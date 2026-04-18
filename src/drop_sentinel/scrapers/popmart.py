"""Pop Mart global store scraper via CDN JSON endpoints."""
from __future__ import annotations

import logging

import httpx

from drop_sentinel.helpers.rate_limiter import RateLimiter
from drop_sentinel.models import Platform, Product, Variant
from drop_sentinel.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

# CDN base for North America / Australia cluster
CDN_BASE = "https://cdn-global.popmart.com"

# Key collection IDs (from sitemap-collections.xml)
DEFAULT_COLLECTIONS = {
    329: "Best Sellers",
    330: "Trending Now",
    331: "New Arrivals",
}

# Supported countries on the naus CDN cluster
SUPPORTED_COUNTRIES = ["us", "ca", "au"]


class PopMartScraper(BaseScraper):
    """Scraper for Pop Mart global store using public CDN JSON.

    Pop Mart caches product data on Alibaba Cloud OSS CDN.
    These endpoints require no authentication.
    """

    def __init__(
        self,
        countries: list[str] | None = None,
        collection_ids: list[int] | None = None,
        include_new_arrivals: bool = True,
        user_agent: str = "DropSentinel/0.1",
        rate_limiter: RateLimiter | None = None,
    ):
        self.countries = countries or ["us"]
        self.collection_ids = collection_ids or list(DEFAULT_COLLECTIONS.keys())
        self.include_new_arrivals = include_new_arrivals
        self.user_agent = user_agent
        self.rate_limiter = rate_limiter or RateLimiter()
        self.store_name = "popmart_global"

    def get_platform(self) -> Platform:
        return Platform.SHOPIFY_POPMART  # Reuse existing platform enum

    async def fetch_products(self, **kwargs) -> list[Product]:
        """Fetch products from Pop Mart CDN endpoints."""
        seen_ids: set[str] = set()
        all_products: list[Product] = []

        async with httpx.AsyncClient(
            headers={"User-Agent": self.user_agent},
            timeout=20.0,
            follow_redirects=True,
        ) as client:
            for country in self.countries:
                # Fetch from collections
                for cid in self.collection_ids:
                    await self.rate_limiter.acquire()
                    products = await self._fetch_collection(client, cid, country)
                    for p in products:
                        if p.id not in seen_ids:
                            seen_ids.add(p.id)
                            all_products.append(p)

                # Fetch new arrivals
                if self.include_new_arrivals:
                    await self.rate_limiter.acquire()
                    products = await self._fetch_new_arrivals(client, country)
                    for p in products:
                        if p.id not in seen_ids:
                            seen_ids.add(p.id)
                            all_products.append(p)

        logger.info(f"Fetched {len(all_products)} unique products from Pop Mart CDN")
        return all_products

    async def check_product(self, product_id: str) -> Product | None:
        return None  # CDN doesn't support single product lookup

    async def _fetch_collection(
        self, client: httpx.AsyncClient, collection_id: int, country: str
    ) -> list[Product]:
        """Fetch all pages of a collection."""
        products: list[Product] = []
        page = 1
        max_pages = 10  # Safety limit

        while page <= max_pages:
            url = (
                f"{CDN_BASE}/shop_productoncollection-{collection_id}"
                f"-1-{page}-{country}-en.json"
            )
            try:
                resp = await client.get(url)
                if resp.status_code == 404:
                    break
                resp.raise_for_status()
                data = resp.json()
            except (httpx.HTTPError, ValueError) as e:
                logger.warning(f"Failed to fetch collection {collection_id} page {page}: {e}")
                break

            product_data = data.get("productData", [])
            if not product_data:
                break

            for item in product_data:
                product = self._parse_product(item, country)
                if product:
                    products.append(product)

            total = data.get("total", 0)
            if page * 20 >= total:
                break
            page += 1

        return products

    async def _fetch_new_arrivals(
        self, client: httpx.AsyncClient, country: str
    ) -> list[Product]:
        """Fetch new arrivals / presale products."""
        url = f"{CDN_BASE}/shop_presalenewproducts-{country}-en.json"
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPError, ValueError) as e:
            logger.warning(f"Failed to fetch new arrivals: {e}")
            return []

        products = []
        for item in data if isinstance(data, list) else data.get("productData", []):
            product = self._parse_product(item, country)
            if product:
                products.append(product)

        return products

    def _parse_product(self, item: dict, country: str) -> Product | None:
        """Parse a CDN product item into a Product model."""
        try:
            spu_id = str(item.get("id", ""))
            title = item.get("title", "")
            if not spu_id or not title:
                return None

            subtitle = item.get("subTitle", "")
            images = item.get("bannerImages", [])
            image_url = images[0] if images else ""

            # Build product URL
            url_title = title.replace(" ", "-").replace("/", "-")
            product_url = f"https://www.popmart.com/{country}/products/{spu_id}/{url_title}"

            # Parse SKUs into variants
            variants = []
            for sku in item.get("skus", []):
                sku_id = str(sku.get("id", ""))
                price_cents = sku.get("price", 0)
                discount_cents = sku.get("discountPrice", price_cents)
                currency = sku.get("currency", "USD")

                stock_info = sku.get("stock", {})
                online_stock = stock_info.get("onlineStock", 0)
                is_sold_out = sku.get("isSkuSoldOut", True)
                available = online_stock > 0 and not is_sold_out

                sku_image = sku.get("mainImage", "")

                variants.append(Variant(
                    id=sku_id,
                    title=subtitle or title,
                    price=round(discount_cents / 100, 2),
                    currency=currency,
                    available=available,
                ))

                if not image_url and sku_image:
                    image_url = sku_image

            # Collect tags
            tags = []
            if item.get("isHot"):
                tags.append("hot")
            if item.get("isNew"):
                tags.append("new")
            if subtitle:
                tags.append(subtitle.lower().replace(" ", "_"))

            return Product(
                id=f"popmart_{country}_{spu_id}",
                platform=Platform.SHOPIFY_POPMART,
                title=title,
                url=product_url,
                image_url=image_url,
                variants=variants,
                tags=tags,
            )
        except Exception as e:
            logger.debug(f"Failed to parse Pop Mart product: {e}")
            return None
