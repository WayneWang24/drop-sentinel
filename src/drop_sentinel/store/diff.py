"""Diff engine for detecting stock and price changes."""
from __future__ import annotations

import logging
from datetime import UTC, datetime

from drop_sentinel.models import Event, EventType, Product, Snapshot

logger = logging.getLogger(__name__)


class DiffEngine:
    """Compare two snapshots and produce change events."""

    def compare(self, old: Snapshot | None, new: Snapshot) -> list[Event]:
        """Compare old and new snapshots, return list of events."""
        if old is None:
            # First run — treat all available products as new
            return [
                Event(
                    type=EventType.NEW_PRODUCT,
                    product=p,
                    timestamp=datetime.now(UTC),
                    details=f"New product discovered: {p.title}",
                )
                for p in new.products
                if p.available
            ]

        old_map: dict[str, Product] = {p.id: p for p in old.products}
        new_map: dict[str, Product] = {p.id: p for p in new.products}
        events: list[Event] = []

        for pid, new_product in new_map.items():
            old_product = old_map.get(pid)

            if old_product is None:
                # Brand new product
                if new_product.available:
                    events.append(Event(
                        type=EventType.NEW_PRODUCT,
                        product=new_product,
                        timestamp=datetime.now(UTC),
                        details=f"New product: {new_product.title}",
                    ))
                continue

            # Check restock: was unavailable, now available
            if not old_product.available and new_product.available:
                events.append(Event(
                    type=EventType.RESTOCK,
                    product=new_product,
                    timestamp=datetime.now(UTC),
                    details=f"Restocked: {new_product.title}",
                ))

            # Check out of stock: was available, now unavailable
            elif old_product.available and not new_product.available:
                events.append(Event(
                    type=EventType.OUT_OF_STOCK,
                    product=new_product,
                    timestamp=datetime.now(UTC),
                    details=f"Out of stock: {new_product.title}",
                ))

            # Check price change
            old_price = old_product.min_price
            new_price = new_product.min_price
            if (
                old_price is not None
                and new_price is not None
                and abs(old_price - new_price) > 0.01
            ):
                events.append(Event(
                    type=EventType.PRICE_CHANGE,
                    product=new_product,
                    timestamp=datetime.now(UTC),
                    details=f"Price changed: {old_price} → {new_price}",
                    old_price=old_price,
                    new_price=new_price,
                ))

        if events:
            logger.info(f"Detected {len(events)} events for {new.platform.value}")
        return events
