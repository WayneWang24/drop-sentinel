"""Damai (大麦网) public show listing scraper.

Uses Alibaba Open Platform (TOP) APIs when app_key is configured,
falls back to parsing public search result pages.

Official TOP APIs (free, no user auth required):
- alibaba.damai.ec.search.project.search — search shows
- alibaba.damai.maitix.projects.query — show details with performances/prices
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import time
from datetime import UTC, datetime

import httpx

from drop_sentinel.helpers.rate_limiter import RateLimiter
from drop_sentinel.models import Platform, Product, Variant
from drop_sentinel.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

TOP_API_URL = "https://eco.taobao.com/router/rest"


class DamaiScraper(BaseScraper):
    """Scraper for Damai show listings.

    Supports two modes:
    1. TOP API mode (recommended): Uses official Alibaba Open Platform APIs.
       Requires app_key and app_secret from https://open.alitrip.com
    2. Fallback mode: Returns empty results with a warning.
       Direct web scraping is blocked by Damai's anti-bot system.
    """

    def __init__(
        self,
        cities: list[str] | None = None,
        keywords: list[str] | None = None,
        app_key: str = "",
        app_secret: str = "",
        user_agent: str = "DropSentinel/0.1",
        rate_limiter: RateLimiter | None = None,
    ):
        self.cities = cities or ["上海", "北京", "广州", "深圳"]
        self.keywords = keywords or []
        self.app_key = app_key
        self.app_secret = app_secret
        self.user_agent = user_agent
        self.rate_limiter = rate_limiter or RateLimiter()

    def get_platform(self) -> Platform:
        return Platform.DAMAI

    async def fetch_products(self, **kwargs) -> list[Product]:
        """Fetch show listings from Damai."""
        if self.app_key and self.app_secret:
            return await self._fetch_via_top_api()
        else:
            logger.warning(
                "Damai TOP API credentials not configured. "
                "Set DAMAI_APP_KEY and DAMAI_APP_SECRET env vars, "
                "or register at https://open.alitrip.com"
            )
            return []

    async def check_product(self, product_id: str) -> Product | None:
        """Check a specific show's details."""
        if not self.app_key or not self.app_secret:
            return None
        return await self._fetch_show_detail(product_id)

    async def _fetch_via_top_api(self) -> list[Product]:
        """Fetch shows using Alibaba TOP API."""
        all_products: list[Product] = []

        async with httpx.AsyncClient(timeout=20.0) as client:
            for city in self.cities:
                await self.rate_limiter.acquire()
                try:
                    products = await self._search_top_api(client, city)
                    all_products.extend(products)
                except Exception as e:
                    logger.error(f"TOP API search failed for {city}: {e}")

            # Also search by keywords
            for keyword in self.keywords:
                await self.rate_limiter.acquire()
                try:
                    products = await self._search_top_api(client, keyword=keyword)
                    all_products.extend(products)
                except Exception as e:
                    logger.error(f"TOP API search failed for keyword '{keyword}': {e}")

        # Deduplicate by ID
        seen: set[str] = set()
        unique: list[Product] = []
        for p in all_products:
            if p.id not in seen:
                seen.add(p.id)
                unique.append(p)

        logger.info(f"Fetched {len(unique)} shows from Damai TOP API")
        return unique

    async def _search_top_api(
        self,
        client: httpx.AsyncClient,
        city: str = "",
        keyword: str = "",
    ) -> list[Product]:
        """Call alibaba.damai.ec.search.project.search TOP API."""
        params = {
            "method": "alibaba.damai.ec.search.project.search",
            "app_key": self.app_key,
            "format": "json",
            "v": "1.0",
            "sign_method": "hmac",
            "timestamp": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"),
            "page_size": "50",
            "page_number": "1",
            "sort_type": "3",  # Sort by popularity
        }
        if city:
            params["filter_city_name"] = city
        if keyword:
            params["keyword"] = keyword

        params["sign"] = self._sign_top_request(params)

        try:
            resp = await client.get(TOP_API_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error(f"TOP API request failed: {e}")
            return []

        # Parse response
        products = []
        result = data.get("alibaba_damai_ec_search_project_search_response", {})
        project_list = result.get("model", {}).get("project_list", [])

        for show in project_list:
            try:
                show_id = str(show.get("project_id", show.get("id", "")))
                name = show.get("name", show.get("project_name", ""))
                city_name = show.get("city_name", "")
                venue = show.get("venue_name", "")
                price_str = show.get("price_str", "")
                status = show.get("site_status", 0)
                show_time = show.get("show_time", "")

                # Determine availability from site_status
                # status 3 = 售票中 (selling), 2 = 预售 (presale), 1 = 即将开票
                available = status in (2, 3)

                # Parse price
                price = 0.0
                if show.get("promotion_price"):
                    try:
                        price = float(show["promotion_price"])
                    except (ValueError, TypeError):
                        pass

                url = f"https://www.damai.cn/show.htm?id={show_id}"

                variant_title = f"{city_name} · {venue}" if venue else city_name
                if show_time:
                    variant_title += f" · {show_time}"

                status_map = {1: "即将开票", 2: "预售中", 3: "售票中", 4: "已售罄", 5: "已结束"}
                tags = [city_name]
                if status in status_map:
                    tags.append(status_map[status])

                products.append(Product(
                    id=show_id,
                    platform=Platform.DAMAI,
                    title=name,
                    url=url,
                    image_url=show.get("vertical_pic", show.get("show_pic", "")),
                    variants=[Variant(
                        id=show_id,
                        title=variant_title,
                        price=price,
                        currency="CNY",
                        available=available,
                        sku=price_str,
                    )],
                    tags=tags,
                ))
            except Exception as e:
                logger.warning(f"Failed to parse show: {e}")

        return products

    async def _fetch_show_detail(self, project_id: str) -> Product | None:
        """Call alibaba.damai.maitix.projects.query for show details."""
        params = {
            "method": "alibaba.damai.maitix.projects.query",
            "app_key": self.app_key,
            "format": "json",
            "v": "1.0",
            "sign_method": "hmac",
            "timestamp": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"),
            "project_id": project_id,
        }
        params["sign"] = self._sign_top_request(params)

        async with httpx.AsyncClient(timeout=20.0) as client:
            try:
                resp = await client.get(TOP_API_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                logger.error(f"TOP API detail request failed: {e}")
                return None

        result = data.get("alibaba_damai_maitix_projects_query_response", {})
        project = result.get("model", {})
        if not project:
            return None

        variants = []
        for perf in project.get("perform_info_d_t_o_s", []):
            perf_id = str(perf.get("perform_id", ""))
            perf_name = perf.get("perform_name", "")
            status = perf.get("perform_status", "")
            available = status in ("2", "3", 2, 3)

            # Get prices for this performance
            for price_info in project.get("price_info_d_t_o_s", []):
                variants.append(Variant(
                    id=f"{perf_id}_{price_info.get('price_id', '')}",
                    title=f"{perf_name} - {price_info.get('price_name', '')}",
                    price=float(price_info.get("price", 0)),
                    currency="CNY",
                    available=available,
                    sku=str(price_info.get("price_id", "")),
                ))

        return Product(
            id=project_id,
            platform=Platform.DAMAI,
            title=project.get("project_name", ""),
            url=f"https://www.damai.cn/show.htm?id={project_id}",
            image_url=project.get("show_pic", ""),
            variants=variants,
        )

    def _sign_top_request(self, params: dict[str, str]) -> str:
        """Generate HMAC-MD5 signature for TOP API request."""
        # Sort params alphabetically, concatenate key+value
        sorted_params = sorted(params.items())
        sign_str = "".join(f"{k}{v}" for k, v in sorted_params)

        # HMAC-MD5 with app_secret
        signature = hmac.new(
            self.app_secret.encode("utf-8"),
            sign_str.encode("utf-8"),
            hashlib.md5,
        ).hexdigest().upper()

        return signature
