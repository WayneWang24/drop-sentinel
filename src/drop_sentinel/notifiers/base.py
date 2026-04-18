"""Base notifier interface."""
from __future__ import annotations

from abc import ABC, abstractmethod

from drop_sentinel.models import Event


class BaseNotifier(ABC):
    """Abstract base class for notification channels."""

    @abstractmethod
    async def send(self, event: Event) -> bool:
        """Send a notification for an event. Returns True on success."""
        ...

    def format_event(self, event: Event) -> str:
        """Format an event into a human-readable message."""
        emoji_map = {
            "new_product": "\U0001f195",
            "restock": "\U0001f514",
            "out_of_stock": "\u274c",
            "price_change": "\U0001f4b0",
            "new_release": "\U0001f4c5",
        }
        emoji = emoji_map.get(event.type.value, "\U0001f4e2")
        lines = [
            f"{emoji} {event.type.value.upper().replace('_', ' ')}",
            f"",
            f"**{event.product.title}**",
            f"Platform: {event.product.platform.value}",
        ]
        if event.details:
            lines.append(f"Details: {event.details}")
        if event.product.min_price is not None:
            lines.append(f"Price: {event.product.min_price} {event.product.variants[0].currency if event.product.variants else 'USD'}")
        if event.old_price is not None and event.new_price is not None:
            lines.append(f"Price change: {event.old_price} \u2192 {event.new_price}")
        if event.product.url:
            lines.append(f"")
            lines.append(f"\U0001f517 {event.product.url}")
        return "\n".join(lines)
