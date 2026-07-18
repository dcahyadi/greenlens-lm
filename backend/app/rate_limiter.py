"""
GreenLens LM — per-IP rate limiting for public API endpoints.

Uses a simple in-memory sliding window, keyed by client IP. This is
intentionally lightweight rather than Redis-backed: Render's free tier
(and the Dockerfile's `--workers 1`) runs a single process, so in-memory
state is sufficient and avoids adding an external dependency. This would
need to move to a shared store (Redis, etc.) if the app were later
horizontally scaled across multiple instances/workers.
"""

import time
from collections import defaultdict
from threading import Lock

from fastapi import HTTPException, Request, status

from app.config import settings


class InMemoryRateLimiter:
    """Sliding-window rate limiter: at most `max_requests` per `window_seconds`, per client IP."""

    def __init__(self, max_requests: int, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def _get_client_ip(self, request: Request) -> str:
        # Render (and most PaaS providers) sit behind a proxy; the real
        # client IP is in X-Forwarded-For, not request.client.host, which
        # would otherwise show the proxy's internal IP for every request.
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def check(self, request: Request) -> None:
        """Raises HTTPException(429) if this client has exceeded the limit."""
        ip = self._get_client_ip(request)
        now = time.monotonic()
        window_start = now - self.window_seconds

        with self._lock:
            timestamps = self._requests[ip]
            timestamps[:] = [t for t in timestamps if t > window_start]

            if len(timestamps) >= self.max_requests:
                retry_after = int(self.window_seconds - (now - timestamps[0])) + 1
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=(
                        f"Rate limit exceeded: max {self.max_requests} requests "
                        f"per {self.window_seconds}s. Try again in {retry_after}s."
                    ),
                    headers={"Retry-After": str(retry_after)},
                )

            timestamps.append(now)


# Singleton instance, configured from settings — shared across all requests
# in this process.
rate_limiter = InMemoryRateLimiter(
    max_requests=settings.RATE_LIMIT_PER_MINUTE,
    window_seconds=60,
)


def rate_limit_dependency(request: Request) -> None:
    """FastAPI dependency — attach to any route to apply rate limiting."""
    rate_limiter.check(request)
