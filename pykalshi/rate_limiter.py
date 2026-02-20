"""
Rate limiter for proactive request throttling.

Composable, optional, and easy to remove. Inject into KalshiClient
to prevent 429s rather than just retrying after them.
"""

from __future__ import annotations

import asyncio
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Protocol


class RateLimiterProtocol(Protocol):
    """Protocol for rate limiters. Implement this to create custom limiters."""

    def acquire(self, weight: int = 1) -> float:
        """Acquire permission to make a request.

        Args:
            weight: Cost of this request (default 1).

        Returns:
            Time waited in seconds (0 if no wait).
        """
        ...

    def update_from_headers(self, remaining: int | None, reset_at: int | None) -> None:
        """Update internal state from response headers.

        Args:
            remaining: Requests remaining in current window.
            reset_at: Unix timestamp when window resets.
        """
        ...


@dataclass
class RateLimiter:
    """Token bucket rate limiter with sliding window.

    Thread-safe. Proactively throttles requests to stay under limits.

    Usage:
        limiter = RateLimiter(requests_per_second=10)
        client = KalshiClient(..., rate_limiter=limiter)

        # Or manual usage:
        limiter.acquire()  # Blocks if needed
        response = make_request()
        limiter.update_from_headers(
            remaining=int(response.headers.get('X-RateLimit-Remaining')),
            reset_at=int(response.headers.get('X-RateLimit-Reset')),
        )

    Attributes:
        requests_per_second: Target request rate.
        burst: Maximum burst size (default: 2x requests_per_second).
        min_spacing_ms: Minimum ms between requests (anti-burst).
    """

    requests_per_second: float = 10.0
    burst: int | None = None
    min_spacing_ms: float = 0.0

    _timestamps: deque = field(default_factory=deque, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _last_request: float = field(default=0.0, repr=False)

    # Server-reported state (updated from headers)
    _server_remaining: int | None = field(default=None, repr=False)
    _server_reset_at: int | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self.burst is None:
            self.burst = max(1, int(self.requests_per_second * 2))
        self._window_size = 1.0  # 1 second sliding window

    def acquire(self, weight: int = 1) -> float:
        """Block until request is allowed. Returns wait time in seconds."""
        with self._lock:
            now = time.monotonic()
            waited = 0.0

            # Enforce minimum spacing
            if self.min_spacing_ms > 0:
                elapsed = (now - self._last_request) * 1000
                if elapsed < self.min_spacing_ms:
                    sleep_time = (self.min_spacing_ms - elapsed) / 1000
                    time.sleep(sleep_time)
                    waited += sleep_time
                    now = time.monotonic()

            # Clean old timestamps outside window
            cutoff = now - self._window_size
            while self._timestamps and self._timestamps[0] < cutoff:
                self._timestamps.popleft()

            # If at capacity, wait for oldest to expire
            while len(self._timestamps) >= self.burst:
                oldest = self._timestamps[0]
                sleep_time = oldest + self._window_size - now
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    waited += sleep_time
                    now = time.monotonic()
                # Re-clean after sleep
                cutoff = now - self._window_size
                while self._timestamps and self._timestamps[0] < cutoff:
                    self._timestamps.popleft()

            # Check server-reported limits (be conservative)
            if self._server_remaining is not None and self._server_remaining <= 1:
                if self._server_reset_at is not None:
                    sleep_until = self._server_reset_at - time.time()
                    if sleep_until > 0:
                        time.sleep(sleep_until)
                        waited += sleep_until
                        now = time.monotonic()
                        self._server_remaining = None

            # Record this request
            for _ in range(weight):
                self._timestamps.append(now)
            self._last_request = now

            return waited

    def update_from_headers(
        self, remaining: int | None, reset_at: int | None
    ) -> None:
        """Update state from X-RateLimit-Remaining and X-RateLimit-Reset headers."""
        with self._lock:
            if remaining is not None:
                self._server_remaining = remaining
            if reset_at is not None:
                self._server_reset_at = reset_at

    @property
    def current_rate(self) -> float:
        """Current request rate (requests in last second)."""
        with self._lock:
            now = time.monotonic()
            cutoff = now - self._window_size
            while self._timestamps and self._timestamps[0] < cutoff:
                self._timestamps.popleft()
            return len(self._timestamps)

    def reset(self) -> None:
        """Clear all state. Useful for testing."""
        with self._lock:
            self._timestamps.clear()
            self._last_request = 0.0
            self._server_remaining = None
            self._server_reset_at = None


@dataclass
class NoOpRateLimiter:
    """Rate limiter that does nothing. For testing or opt-out."""

    def acquire(self, weight: int = 1) -> float:
        return 0.0

    def update_from_headers(
        self, remaining: int | None, reset_at: int | None
    ) -> None:
        pass


class AsyncRateLimiterProtocol(Protocol):
    """Protocol for async rate limiters."""

    async def acquire(self, weight: int = 1) -> float: ...

    def update_from_headers(self, remaining: int | None, reset_at: int | None) -> None: ...


@dataclass
class AsyncRateLimiter:
    """Async token bucket rate limiter with sliding window.

    Same algorithm as RateLimiter but uses asyncio primitives
    so it never blocks the event loop.

    Usage:
        limiter = AsyncRateLimiter(requests_per_second=10)
        client = AsyncKalshiClient(..., rate_limiter=limiter)
    """

    requests_per_second: float = 10.0
    burst: int | None = None
    min_spacing_ms: float = 0.0

    _timestamps: deque = field(default_factory=deque, repr=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)
    _last_request: float = field(default=0.0, repr=False)
    _server_remaining: int | None = field(default=None, repr=False)
    _server_reset_at: int | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self.burst is None:
            self.burst = max(1, int(self.requests_per_second * 2))
        self._window_size = 1.0

    async def acquire(self, weight: int = 1) -> float:
        """Await until request is allowed. Returns wait time in seconds."""
        async with self._lock:
            now = time.monotonic()
            waited = 0.0

            if self.min_spacing_ms > 0:
                elapsed = (now - self._last_request) * 1000
                if elapsed < self.min_spacing_ms:
                    sleep_time = (self.min_spacing_ms - elapsed) / 1000
                    await asyncio.sleep(sleep_time)
                    waited += sleep_time
                    now = time.monotonic()

            cutoff = now - self._window_size
            while self._timestamps and self._timestamps[0] < cutoff:
                self._timestamps.popleft()

            while len(self._timestamps) >= self.burst:
                oldest = self._timestamps[0]
                sleep_time = oldest + self._window_size - now
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                    waited += sleep_time
                    now = time.monotonic()
                cutoff = now - self._window_size
                while self._timestamps and self._timestamps[0] < cutoff:
                    self._timestamps.popleft()

            if self._server_remaining is not None and self._server_remaining <= 1:
                if self._server_reset_at is not None:
                    sleep_until = self._server_reset_at - time.time()
                    if sleep_until > 0:
                        await asyncio.sleep(sleep_until)
                        waited += sleep_until
                        now = time.monotonic()
                        self._server_remaining = None

            for _ in range(weight):
                self._timestamps.append(now)
            self._last_request = now

            return waited

    def update_from_headers(
        self, remaining: int | None, reset_at: int | None
    ) -> None:
        """Update state from response headers. Safe to call outside async context."""
        if remaining is not None:
            self._server_remaining = remaining
        if reset_at is not None:
            self._server_reset_at = reset_at

    @property
    def current_rate(self) -> float:
        """Current request rate (requests in last second)."""
        now = time.monotonic()
        cutoff = now - self._window_size
        while self._timestamps and self._timestamps[0] < cutoff:
            self._timestamps.popleft()
        return len(self._timestamps)

    def reset(self) -> None:
        """Clear all state."""
        self._timestamps.clear()
        self._last_request = 0.0
        self._server_remaining = None
        self._server_reset_at = None


@dataclass
class AsyncNoOpRateLimiter:
    """Async rate limiter that does nothing. For testing or opt-out."""

    async def acquire(self, weight: int = 1) -> float:
        return 0.0

    def update_from_headers(
        self, remaining: int | None, reset_at: int | None
    ) -> None:
        pass
