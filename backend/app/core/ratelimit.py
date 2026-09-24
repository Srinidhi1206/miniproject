"""Small in-memory sliding-window rate limiter.

Good enough for a single-process deployment. For multiple workers, swap the
store for Redis — the `RateLimiter.hit` interface stays the same.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from fastapi import Request

from app.core.config import get_settings
from app.core.errors import SentinelError


class RateLimiter:
    def __init__(self, limit: int, window_seconds: float = 60.0):
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, key: str) -> bool:
        """Record a hit; return False when the key is over its limit."""
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > self.window:
                q.popleft()
            if len(q) >= self.limit:
                return False
            q.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


_limiter: RateLimiter | None = None


def get_limiter() -> RateLimiter:
    global _limiter
    if _limiter is None:
        _limiter = RateLimiter(get_settings().rate_limit_per_minute)
    return _limiter


def client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


async def rate_limit(request: Request) -> None:
    """FastAPI dependency applied to write/analysis endpoints."""
    if not get_limiter().hit(client_key(request)):
        raise SentinelError(
            "RATE_LIMITED",
            "You're sending requests too quickly. Please wait a minute and try again.",
            429,
        )
