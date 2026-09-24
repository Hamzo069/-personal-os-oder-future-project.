"""A small in-memory fixed-window rate limiter.

Good enough for a single API instance (the MVP deployment target). For a
multi-instance deployment swap the store for Redis - the interface stays the same.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict

from fastapi import Request

from app.core.errors import RateLimitedError


class RateLimiter:
    def __init__(self, limit: int, window_seconds: int = 60) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._hits: dict[str, tuple[int, float]] = defaultdict(lambda: (0, 0.0))
        self._lock = threading.Lock()

    def check(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            count, window_start = self._hits[key]
            if now - window_start >= self.window_seconds:
                count, window_start = 0, now
            count += 1
            self._hits[key] = (count, window_start)
        if count > self.limit:
            retry_after = int(self.window_seconds - (now - window_start)) + 1
            raise RateLimitedError(
                "Too many requests, please slow down", details={"retry_after": retry_after}
            )

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


def client_ip(request: Request) -> str:
    """The peer address as seen by the ASGI server.

    `X-Forwarded-For` is deliberately *not* parsed here: any client could set it and pick
    its own rate-limit bucket. Behind a reverse proxy run uvicorn with `--proxy-headers`
    and `--forwarded-allow-ips` (see apps/api/Dockerfile) so the server rewrites the peer
    address only for trusted proxies.
    """
    return request.client.host if request.client else "unknown"
