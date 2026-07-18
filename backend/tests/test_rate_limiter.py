"""
GreenLens LM — tests for app/rate_limiter.py

Tests the InMemoryRateLimiter class in isolation (not through the full
FastAPI app), so these run fast and don't interfere with other tests'
usage of the shared /api/query endpoint.
"""
import time
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.rate_limiter import InMemoryRateLimiter


def make_request(ip: str = "1.2.3.4", forwarded: str | None = None) -> MagicMock:
    """Build a minimal mock FastAPI Request with a given client IP."""
    request = MagicMock()
    request.headers = {"x-forwarded-for": forwarded} if forwarded else {}
    request.client.host = ip
    return request


def test_allows_requests_under_limit():
    limiter = InMemoryRateLimiter(max_requests=3, window_seconds=60)
    req = make_request()
    for _ in range(3):
        limiter.check(req)  # should not raise


def test_blocks_request_over_limit():
    limiter = InMemoryRateLimiter(max_requests=3, window_seconds=60)
    req = make_request()
    for _ in range(3):
        limiter.check(req)

    with pytest.raises(HTTPException) as exc_info:
        limiter.check(req)

    assert exc_info.value.status_code == 429
    assert "Retry-After" in exc_info.value.headers


def test_different_ips_tracked_independently():
    limiter = InMemoryRateLimiter(max_requests=2, window_seconds=60)
    req_a = make_request(ip="1.1.1.1")
    req_b = make_request(ip="2.2.2.2")

    limiter.check(req_a)
    limiter.check(req_a)
    # req_a is now at its limit, but req_b must be unaffected
    limiter.check(req_b)
    limiter.check(req_b)

    with pytest.raises(HTTPException):
        limiter.check(req_a)
    with pytest.raises(HTTPException):
        limiter.check(req_b)


def test_window_resets_after_time_passes():
    limiter = InMemoryRateLimiter(max_requests=1, window_seconds=1)
    req = make_request()

    limiter.check(req)  # first request OK
    with pytest.raises(HTTPException):
        limiter.check(req)  # second, immediate, blocked

    time.sleep(1.1)
    limiter.check(req)  # window has passed — should be allowed again


def test_uses_x_forwarded_for_header_when_present():
    """Render sits behind a proxy — the real client IP comes from
    X-Forwarded-For, not request.client.host (which would show the
    proxy's own IP for every request otherwise)."""
    limiter = InMemoryRateLimiter(max_requests=1, window_seconds=60)

    req_client_a = make_request(ip="10.0.0.1", forwarded="203.0.113.5, 10.0.0.1")
    limiter.check(req_client_a)  # consumes the limit for 203.0.113.5

    # Same proxy IP, but a DIFFERENT real client behind it — must not be blocked
    req_client_b = make_request(ip="10.0.0.1", forwarded="198.51.100.9, 10.0.0.1")
    limiter.check(req_client_b)

    # The original client is still correctly rate-limited
    with pytest.raises(HTTPException):
        limiter.check(req_client_a)


def test_falls_back_to_client_host_without_forwarded_header():
    limiter = InMemoryRateLimiter(max_requests=1, window_seconds=60)
    req = make_request(ip="127.0.0.1", forwarded=None)
    limiter.check(req)
    with pytest.raises(HTTPException):
        limiter.check(req)


def test_error_message_includes_limit_details():
    limiter = InMemoryRateLimiter(max_requests=1, window_seconds=60)
    req = make_request()
    limiter.check(req)

    with pytest.raises(HTTPException) as exc_info:
        limiter.check(req)

    assert "1 requests per 60s" in exc_info.value.detail
