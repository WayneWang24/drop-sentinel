"""Telegram Bot notification channel."""
from __future__ import annotations

import logging

import httpx

from drop_sentinel.models import Event
from drop_sentinel.notifiers.base import BaseNotifier

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


class TelegramNotifier(BaseNotifier):
    """Send notifications via Telegram Bot API."""

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id

    async def send(self, event: Event) -> bool:
        """Send a Telegram message for an event."""
        message = self.format_event(event)
        url = TELEGRAM_API.format(token=self.bot_token)

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.post(url, json={
                    "chat_id": self.chat_id,
                    "text": message,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": False,
                })
                resp.raise_for_status()
                logger.info(f"Telegram notification sent: {event.type.value}")
                return True
            except httpx.HTTPError as e:
                logger.error(f"Telegram notification failed: {e}")
                return False
