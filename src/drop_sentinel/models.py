"""Core data models for drop-sentinel."""
from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from pydantic import BaseModel, Field


class Platform(str, Enum):
    """Supported platforms."""
    SHOPIFY_POPMART = "shopify_popmart"
    DAMAI = "damai"
    LAZADA = "lazada"
    SHOPEE = "shopee"
    SOCIAL = "social"


class EventType(str, Enum):
    """Types of stock/release events."""
    NEW_PRODUCT = "new_product"
    RESTOCK = "restock"
    OUT_OF_STOCK = "out_of_stock"
    PRICE_CHANGE = "price_change"
    NEW_RELEASE = "new_release"


class Variant(BaseModel):
    """A product variant (size, color, etc.)."""
    id: str
    title: str
    price: float
    currency: str = "USD"
    available: bool = False
    sku: str = ""


class Product(BaseModel):
    """A product listing from any platform."""
    id: str
    platform: Platform
    title: str
    url: str
    image_url: str = ""
    variants: list[Variant] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def available(self) -> bool:
        return any(v.available for v in self.variants)

    @property
    def min_price(self) -> float | None:
        prices = [v.price for v in self.variants if v.available]
        return min(prices) if prices else None


class Event(BaseModel):
    """A detected change event."""
    type: EventType
    product: Product
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    details: str = ""
    old_price: float | None = None
    new_price: float | None = None


class Snapshot(BaseModel):
    """A point-in-time snapshot of products from a platform."""
    platform: Platform
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    products: list[Product] = Field(default_factory=list)


class ReleaseInfo(BaseModel):
    """Upcoming release information."""
    title: str
    platform: Platform
    release_time: datetime | None = None
    url: str = ""
    image_url: str = ""
    description: str = ""
    source: str = ""  # where we found this info
