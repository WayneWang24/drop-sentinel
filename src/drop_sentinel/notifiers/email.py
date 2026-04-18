"""Email notification channel via SMTP."""
from __future__ import annotations

import logging
import smtplib
from email.mime.text import MIMEText

from drop_sentinel.models import Event
from drop_sentinel.notifiers.base import BaseNotifier

logger = logging.getLogger(__name__)


class EmailNotifier(BaseNotifier):
    """Send notifications via SMTP email."""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int = 587,
        username: str = "",
        password: str = "",
        to_addresses: list[str] | None = None,
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.to_addresses = to_addresses or []

    async def send(self, event: Event) -> bool:
        """Send an email notification."""
        if not self.to_addresses:
            logger.warning("No email recipients configured")
            return False

        subject = f"[Drop Sentinel] {event.type.value.upper().replace('_', ' ')}: {event.product.title}"
        body = self.format_event(event)

        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = self.username
        msg["To"] = ", ".join(self.to_addresses)

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as server:
                server.starttls()
                if self.username and self.password:
                    server.login(self.username, self.password)
                server.sendmail(self.username, self.to_addresses, msg.as_string())
            logger.info(f"Email sent: {subject}")
            return True
        except Exception as e:
            logger.error(f"Email notification failed: {e}")
            return False
