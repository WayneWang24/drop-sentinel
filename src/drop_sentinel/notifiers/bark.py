"""Bark iOS push notification channel."""
from __future__ import annotations

import logging

import httpx

from drop_sentinel.models import Event
from drop_sentinel.notifiers.base import BaseNotifier

logger = logging.getLogger(__name__)


class BarkNotifier(BaseNotifier):
    """Send push notifications via Bark (iOS)."""

    def __init__(self, server_url: str = "https://api.day.app", device_key: str = ""):
        self.server_url = server_url.rstrip("/")
        self.device_key = device_key

    async def send(self, event: Event) -> bool:
        """Send a Bark push notification."""
        title = f"{event.type.value.upper().replace('_', ' ')}: {event.product.title}"
        body = event.details or ""
        url = event.product.url or ""

        endpoint = f"{self.server_url}/{self.device_key}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.post(endpoint, json={
                    "title": title[:100],
                    "body": body[:500],
                    "url": url,
                    "group": "drop-sentinel",
                    "sound": "minuet",
                })
                resp.raise_for_status()
                data = resp.json()
                if data.get("code") == 200:
                    logger.info(f"Bark notification sent: {event.type.value}")
                    return True
                else:
                    logger.error(f"Bark API error: {data}")
                    return False
            except httpx.HTTPError as e:
                logger.error(f"Bark notification failed: {e}")
                return False
