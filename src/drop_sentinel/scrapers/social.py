"""Social media monitor for release announcements."""
from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from xml.etree import ElementTree

import httpx

from drop_sentinel.helpers.rate_limiter import RateLimiter
from drop_sentinel.models import Platform, Product, ReleaseInfo, Variant
from drop_sentinel.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


# Public RSS/feed sources for monitoring
DEFAULT_FEEDS = [
    {
        "name": "popmart_weibo",
        "url": "https://rsshub.app/weibo/user/5765038311",  # Pop Mart official Weibo via RSSHub
        "type": "rss",
        "keywords": ["发售", "新品", "限定", "预售", "开售", "上新"],
    },
    {
        "name": "damai_weibo",
        "url": "https://rsshub.app/weibo/user/1652942270",  # Damai official Weibo
        "type": "rss",
        "keywords": ["开票", "预售", "演唱会", "巡演", "开售"],
    },
]


class SocialScraper(BaseScraper):
    """Monitor social media for release/sale announcements."""

    def __init__(
        self,
        feeds: list[dict] | None = None,
        user_agent: str = "DropSentinel/0.1",
        rate_limiter: RateLimiter | None = None,
    ):
        self.feeds = feeds or DEFAULT_FEEDS
        self.user_agent = user_agent
        self.rate_limiter = rate_limiter or RateLimiter()

    def get_platform(self) -> Platform:
        return Platform.SOCIAL

    async def fetch_products(self, **kwargs) -> list[Product]:
        """Fetch announcements as pseudo-products for unified pipeline."""
        releases = await self.fetch_releases()
        # Convert releases to Product format for the diff engine
        products = []
        for r in releases:
            products.append(Product(
                id=f"social_{hash(r.url) % 10**8}",
                platform=Platform.SOCIAL,
                title=r.title,
                url=r.url,
                image_url=r.image_url,
                variants=[Variant(
                    id="info",
                    title=r.source,
                    price=0.0,
                    available=True,
                )],
                tags=[r.source],
            ))
        return products

    async def check_product(self, product_id: str) -> Product | None:
        return None  # Social posts don't have individual check

    async def fetch_releases(self) -> list[ReleaseInfo]:
        """Fetch release announcements from all configured feeds."""
        all_releases: list[ReleaseInfo] = []

        async with httpx.AsyncClient(
            headers={"User-Agent": self.user_agent},
            timeout=20.0,
            follow_redirects=True,
        ) as client:
            for feed in self.feeds:
                try:
                    await self.rate_limiter.acquire()
                    releases = await self._fetch_feed(client, feed)
                    all_releases.extend(releases)
                except Exception as e:
                    logger.warning(f"Failed to fetch feed {feed['name']}: {e}")

        logger.info(f"Found {len(all_releases)} release announcements")
        return all_releases

    async def _fetch_feed(
        self, client: httpx.AsyncClient, feed: dict
    ) -> list[ReleaseInfo]:
        """Fetch and parse a single RSS feed."""
        resp = await client.get(feed["url"])
        resp.raise_for_status()

        releases = []
        keywords = feed.get("keywords", [])

        if feed.get("type") == "rss":
            releases = self._parse_rss(
                resp.text,
                source=feed["name"],
                keywords=keywords,
            )

        return releases

    def _parse_rss(
        self, xml_text: str, source: str, keywords: list[str]
    ) -> list[ReleaseInfo]:
        """Parse RSS/Atom XML and extract matching items."""
        releases = []
        try:
            root = ElementTree.fromstring(xml_text)
        except ElementTree.ParseError as e:
            logger.warning(f"RSS parse error from {source}: {e}")
            return releases

        # Handle both RSS 2.0 and Atom feeds
        items = root.findall(".//item")  # RSS 2.0
        if not items:
            # Try Atom namespace
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            items = root.findall(".//atom:entry", ns)

        for item in items[:20]:  # Limit to recent 20
            title = self._get_text(item, "title") or ""
            link = self._get_text(item, "link") or ""
            description = self._get_text(item, "description") or ""
            pub_date = self._get_text(item, "pubDate") or ""

            # If no link text, check for href attribute (Atom)
            if not link:
                link_elem = item.find("link")
                if link_elem is not None:
                    link = link_elem.get("href", "")

            content = f"{title} {description}".lower()

            # Filter by keywords
            if keywords and not any(kw in content for kw in keywords):
                continue

            # Extract image from description HTML
            image_url = ""
            img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', description)
            if img_match:
                image_url = img_match.group(1)

            # Parse publish date
            release_time = None
            if pub_date:
                try:
                    # RFC 2822 format common in RSS
                    from email.utils import parsedate_to_datetime
                    release_time = parsedate_to_datetime(pub_date)
                except (ValueError, TypeError):
                    pass

            releases.append(ReleaseInfo(
                title=title,
                platform=Platform.SOCIAL,
                release_time=release_time,
                url=link,
                image_url=image_url,
                description=description[:500],  # Truncate long descriptions
                source=source,
            ))

        return releases

    @staticmethod
    def _get_text(element: ElementTree.Element, tag: str) -> str | None:
        """Get text content of a child element."""
        child = element.find(tag)
        if child is not None and child.text:
            return child.text.strip()
        return None
