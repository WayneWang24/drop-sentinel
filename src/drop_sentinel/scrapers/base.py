"""Base scraper interface."""
from __future__ import annotations

from abc import ABC, abstractmethod

from drop_sentinel.models import Platform, Product, Snapshot


class BaseScraper(ABC):
    """Abstract base class for all platform scrapers."""

    @abstractmethod
    def get_platform(self) -> Platform:
        """Return the platform this scraper handles."""
        ...

    @abstractmethod
    async def fetch_products(self, **kwargs) -> list[Product]:
        """Fetch product listings from the platform."""
        ...

    @abstractmethod
    async def check_product(self, product_id: str) -> Product | None:
        """Check a specific product's current status."""
        ...

    async def take_snapshot(self, **kwargs) -> Snapshot:
        """Take a full snapshot of monitored products."""
        from datetime import UTC, datetime
        products = await self.fetch_products(**kwargs)
        return Snapshot(
            platform=self.get_platform(),
            timestamp=datetime.now(UTC),
            products=products,
        )
