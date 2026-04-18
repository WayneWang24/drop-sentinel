"""Rate limiter using token bucket algorithm."""
from __future__ import annotations

import asyncio
import time


class RateLimiter:
    """Token bucket rate limiter for HTTP requests."""

    def __init__(self, max_per_minute: int = 12):
        self.max_per_minute = max_per_minute
        self.interval = 60.0 / max_per_minute
        self._last_request: float = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait until a request is allowed."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request
            if elapsed < self.interval:
                await asyncio.sleep(self.interval - elapsed)
            self._last_request = time.monotonic()
