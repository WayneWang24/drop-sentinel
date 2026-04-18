"""Generic webhook notification channel."""
from __future__ import annotations

import logging

import httpx

from drop_sentinel.models import Event
from drop_sentinel.notifiers.base import BaseNotifier

logger = logging.getLogger(__name__)


class WebhookNotifier(BaseNotifier):
    """Send notifications via generic webhook (Discord, Slack, custom)."""

    def __init__(self, url: str):
        self.url = url

    async def send(self, event: Event) -> bool:
        """POST event data to the configured webhook URL."""
        payload = {
            "text": self.format_event(event),
            "content": self.format_event(event),  # Discord compatibility
            "event_type": event.type.value,
            "product_title": event.product.title,
            "product_url": event.product.url,
            "platform": event.product.platform.value,
            "details": event.details,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.post(self.url, json=payload)
                resp.raise_for_status()
                logger.info(f"Webhook notification sent: {event.type.value}")
                return True
            except httpx.HTTPError as e:
                logger.error(f"Webhook notification failed: {e}")
                return False
