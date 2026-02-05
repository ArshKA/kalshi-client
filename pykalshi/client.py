"""
Kalshi API Client

Core client class for authenticated API requests.
"""

from __future__ import annotations

import os
import time
import json
import logging
from base64 import b64encode
from functools import cached_property
from typing import Any
from urllib.parse import urlparse, urlencode

import requests

logger = logging.getLogger(__name__)

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey

from .exceptions import (
    KalshiAPIError,
    AuthenticationError,
    InsufficientFundsError,
    ResourceNotFoundError,
    RateLimitError,
    OrderRejectedError,
)
from .events import Event
from .markets import Market, Series
from .models import MarketModel, EventModel, SeriesModel, TradeModel, CandlestickResponse
from .dataframe import DataFrameList
from .portfolio import Portfolio
from .enums import MarketStatus, CandlestickPeriod
from .feed import Feed
from .exchange import Exchange
from .api_keys import APIKeys
from .rate_limiter import RateLimiterProtocol


# Default configuration
DEFAULT_API_BASE = "https://api.elections.kalshi.com/trade-api/v2"
DEMO_API_BASE = "https://demo-api.kalshi.co/trade-api/v2"

_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class KalshiClient:
    """Authenticated client for the Kalshi Trading API.

    Usage:
        client = KalshiClient.from_env()  # Loads .env file
        client = KalshiClient(api_key_id="...", private_key_path="...")
    """

    def __init__(
        self,
        api_key_id: str | None = None,
        private_key_path: str | None = None,
        api_base: str | None = None,
        demo: bool = False,
        timeout: float = 10.0,
        max_retries: int = 3,
        rate_limiter: RateLimiterProtocol | None = None,
    ) -> None:
        """Initialize the Kalshi client.

        Args:
            api_key_id: API key ID. Falls back to KALSHI_API_KEY_ID env var.
            private_key_path: Path to private key file. Falls back to KALSHI_PRIVATE_KEY_PATH env var.
            api_base: API base URL. Defaults to production or demo based on `demo` flag.
            demo: If True, use demo environment. Ignored if api_base is provided.
            timeout: Request timeout in seconds (default 10).
            max_retries: Max retries for transient failures (default 3). Set to 0 to disable.
            rate_limiter: Optional rate limiter for proactive throttling. See RateLimiter class.
        """
        resolved_api_key_id = api_key_id or os.getenv("KALSHI_API_KEY_ID")
        private_key_path = private_key_path or os.getenv("KALSHI_PRIVATE_KEY_PATH")

        if not resolved_api_key_id:
            raise ValueError(
                "API key ID required. Set KALSHI_API_KEY_ID env var or pass api_key_id."
            )
        if not private_key_path:
            raise ValueError(
                "Private key path required. Set KALSHI_PRIVATE_KEY_PATH env var or pass private_key_path."
            )

        self.api_key_id: str = resolved_api_key_id
        self.api_base = api_base or (DEMO_API_BASE if demo else DEFAULT_API_BASE)
        self._api_path = urlparse(self.api_base).path
        self.timeout = timeout
        self.max_retries = max_retries
        self.rate_limiter = rate_limiter
        self.private_key = self._load_private_key(private_key_path)
        self._session = requests.Session()

    @classmethod
    def from_env(cls, **kwargs) -> "KalshiClient":
        """Create client from .env file.

        Loads dotenv before reading env vars. All keyword arguments
        are forwarded to the constructor.
        """
        from dotenv import load_dotenv
        load_dotenv()
        return cls(**kwargs)

    def _load_private_key(self, key_path: str) -> RSAPrivateKey:
        """Load RSA private key from PEM file."""
        with open(key_path, "rb") as f:
            key = serialization.load_pem_private_key(f.read(), password=None)
            if not isinstance(key, RSAPrivateKey):
                raise TypeError(f"Expected RSA private key, got {type(key).__name__}")
            return key

    def _sign_request(self, method: str, path: str) -> tuple[str, str]:
        """Create RSA-PSS signature for API request."""
        timestamp = str(int(time.time() * 1000))
        message = f"{timestamp}{method}{path}"

        signature = self.private_key.sign(
            message.encode(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256(),
        )
        return timestamp, b64encode(signature).decode()

    def _get_headers(self, method: str, endpoint: str) -> dict[str, str]:
        """Generate authenticated headers."""
        path_without_query = urlparse(endpoint).path
        full_path = f"{self._api_path}{path_without_query}"
        timestamp, signature = self._sign_request(method, full_path)
        return {
            "Content-Type": "application/json",
            "KALSHI-ACCESS-KEY": self.api_key_id,
            "KALSHI-ACCESS-SIGNATURE": signature,
            "KALSHI-ACCESS-TIMESTAMP": timestamp,
        }

    def _handle_response(
        self,
        response: requests.Response,
        *,
        method: str | None = None,
        endpoint: str | None = None,
        request_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Handle API response and raise custom exceptions with full context."""
        status_code = response.status_code

        if status_code < 400:
            logger.debug("Response %s: Success", status_code)
            if status_code == 204 or not response.content:
                return {}
            return response.json()

        logger.error("Response %s: Error body: %s", status_code, response.text)

        # Parse error details from response
        response_body: dict[str, Any] | str | None = None
        try:
            error_data = response.json()
            response_body = error_data
            message = error_data.get("message") or error_data.get(
                "error_message", "Unknown Error"
            )
            code = error_data.get("code") or error_data.get("error_code")
        except (ValueError, requests.exceptions.JSONDecodeError):
            message = response.text
            response_body = response.text
            code = None

        # Map to specific exception types
        if status_code in (401, 403):
            raise AuthenticationError(
                status_code, message, code,
                method=method, endpoint=endpoint,
                request_body=request_body, response_body=response_body,
            )
        elif status_code == 404:
            raise ResourceNotFoundError(
                status_code, message, code,
                method=method, endpoint=endpoint,
                request_body=request_body, response_body=response_body,
            )
        elif code in ("insufficient_funds", "insufficient_balance"):
            raise InsufficientFundsError(
                status_code, message, code,
                method=method, endpoint=endpoint,
                request_body=request_body, response_body=response_body,
            )
        elif code in (
            "order_rejected",
            "market_closed",
            "market_settled",
            "invalid_price",
            "self_trade",
            "post_only_rejected",
        ):
            raise OrderRejectedError(
                status_code, message, code,
                method=method, endpoint=endpoint,
                request_body=request_body, response_body=response_body,
            )
        else:
            raise KalshiAPIError(
                status_code, message, code,
                method=method, endpoint=endpoint,
                request_body=request_body, response_body=response_body,
            )

    def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs,
    ) -> requests.Response:
        """Execute an HTTP request with timeout and retry on transient failures.

        Retries on 429/5xx status codes and connection errors with exponential backoff.
        Re-signs each attempt to keep the timestamp fresh.
        """
        url = f"{self.api_base}{endpoint}"

        for attempt in range(self.max_retries + 1):
            # Proactive throttling if rate limiter is configured
            if self.rate_limiter is not None:
                wait_time = self.rate_limiter.acquire()
                if wait_time > 0:
                    logger.debug("Rate limiter waited %.3fs", wait_time)

            headers = self._get_headers(method, endpoint)
            try:
                response = self._session.request(
                    method, url, headers=headers, timeout=self.timeout, **kwargs
                )
            except (
                requests.exceptions.Timeout,
                requests.exceptions.ConnectionError,
            ) as e:
                if attempt == self.max_retries:
                    raise
                wait = min(2 ** attempt * 0.5, 30)
                logger.warning(
                    "%s %s failed (%s), retry %d/%d in %.1fs",
                    method, endpoint, type(e).__name__,
                    attempt + 1, self.max_retries, wait,
                )
                time.sleep(wait)
                continue

            # Update rate limiter from response headers
            if self.rate_limiter is not None:
                remaining = response.headers.get("X-RateLimit-Remaining")
                reset_at = response.headers.get("X-RateLimit-Reset")
                self.rate_limiter.update_from_headers(
                    remaining=int(remaining) if remaining else None,
                    reset_at=int(reset_at) if reset_at else None,
                )

            if response.status_code not in _RETRYABLE_STATUS_CODES:
                return response
            if attempt == self.max_retries:
                if response.status_code == 429:
                    raise RateLimitError(
                        429,
                        "Rate limit exceeded after retries",
                        method=method,
                        endpoint=endpoint,
                    )
                return response

            retry_after = response.headers.get("Retry-After")
            try:
                wait = float(retry_after) if retry_after else min(2 ** attempt * 0.5, 30)
            except (ValueError, TypeError):
                wait = min(2 ** attempt * 0.5, 30)

            logger.warning(
                "%s %s returned %d, retry %d/%d in %.1fs",
                method, endpoint, response.status_code,
                attempt + 1, self.max_retries, wait,
            )
            time.sleep(wait)

        return response  # unreachable, satisfies type checker

    def get(self, endpoint: str) -> dict[str, Any]:
        """Make authenticated GET request."""
        logger.debug("GET %s", endpoint)
        response = self._request("GET", endpoint)
        return self._handle_response(response, method="GET", endpoint=endpoint)

    def paginated_get(
        self,
        path: str,
        response_key: str,
        params: dict[str, Any],
        fetch_all: bool = False,
    ) -> list[dict]:
        """Fetch items with automatic cursor-based pagination.

        Args:
            path: API endpoint path (e.g., "/markets").
            response_key: Key in response JSON containing the items list.
            params: Query parameters (None values are filtered out).
            fetch_all: If True, follow cursors to fetch all pages.
        """
        params = dict(params)  # Don't mutate caller's dict
        all_items: list[dict] = []
        while True:
            filtered = {k: v for k, v in params.items() if v is not None}
            endpoint = f"{path}?{urlencode(filtered)}" if filtered else path
            response = self.get(endpoint)
            all_items.extend(response.get(response_key, []))
            cursor = response.get("cursor", "")
            if not fetch_all or not cursor:
                break
            params["cursor"] = cursor
        return all_items

    def post(self, endpoint: str, data: dict[str, Any]) -> dict[str, Any]:
        """Make authenticated POST request."""
        logger.debug("POST %s", endpoint)
        body = json.dumps(data, separators=(",", ":"))
        response = self._request("POST", endpoint, data=body)
        return self._handle_response(
            response, method="POST", endpoint=endpoint, request_body=data
        )

    def put(self, endpoint: str, data: dict[str, Any]) -> dict[str, Any]:
        """Make authenticated PUT request."""
        logger.debug("PUT %s", endpoint)
        body = json.dumps(data, separators=(",", ":"))
        response = self._request("PUT", endpoint, data=body)
        return self._handle_response(
            response, method="PUT", endpoint=endpoint, request_body=data
        )

    def delete(self, endpoint: str, body: dict | None = None) -> dict[str, Any]:
        """Make authenticated DELETE request."""
        logger.debug("DELETE %s", endpoint)
        if body:
            data = json.dumps(body, separators=(",", ":"))
            response = self._request("DELETE", endpoint, data=data)
        else:
            response = self._request("DELETE", endpoint)
        return self._handle_response(response, method="DELETE", endpoint=endpoint)

    # --- Domain methods ---

    @cached_property
    def portfolio(self) -> Portfolio:
        """The authenticated user's portfolio."""
        return Portfolio(self)

    @cached_property
    def exchange(self) -> Exchange:
        """Exchange status, schedule, and announcements."""
        return Exchange(self)

    @cached_property
    def api_keys(self) -> APIKeys:
        """API key management and rate limits."""
        return APIKeys(self)

    def feed(self) -> Feed:
        """Create a new real-time data feed.

        Returns a Feed instance for streaming market data via WebSocket.
        Each call creates a new Feed - use a single Feed for all subscriptions.

        Usage:
            feed = client.feed()

            @feed.on("ticker")
            def handle_ticker(msg):
                print(f"{msg.market_ticker}: {msg.yes_bid}/{msg.yes_ask}")

            feed.subscribe("ticker", market_ticker="KXBTC-26JAN")
            feed.start()
        """
        return Feed(self)

    def get_market(self, ticker: str) -> Market:
        """Get a Market by ticker."""
        response = self.get(f"/markets/{ticker}")
        model = MarketModel.model_validate(response["market"])
        return Market(self, model)

    def get_markets(
        self,
        *,
        status: MarketStatus | None = None,
        mve_filter: str | None = None,
        tickers: list[str] | None = None,
        series_ticker: str | None = None,
        event_ticker: str | None = None,
        limit: int = 100,
        cursor: str | None = None,
        fetch_all: bool = False,
        **extra_params,
    ) -> DataFrameList[Market]:
        """Search for markets.

        Args:
            status: Filter by market status (open, closed, settled, etc.).
            mve_filter: Filter multivariate/combo markets. "exclude" hides combos,
                       "only" returns only combos.
            tickers: List of specific market tickers to fetch.
            series_ticker: Filter by series ticker.
            event_ticker: Filter by event ticker (supports comma-separated, max 10).
            limit: Maximum results per page (default 100, max 1000).
            cursor: Pagination cursor for fetching next page.
            fetch_all: If True, automatically fetch all pages.
            **extra_params: Additional API parameters (min_close_ts, max_created_ts, etc.).
                           See https://docs.kalshi.com/api-reference/market/get-markets
        """
        params = {
            "status": status.value if status is not None else None,
            "mve_filter": mve_filter,
            "tickers": ",".join(tickers) if tickers else None,
            "series_ticker": series_ticker,
            "event_ticker": event_ticker,
            "limit": limit,
            "cursor": cursor,
            **extra_params,
        }
        data = self.paginated_get("/markets", "markets", params, fetch_all)
        return DataFrameList(Market(self, MarketModel.model_validate(m)) for m in data)

    def get_event(
        self,
        event_ticker: str,
        *,
        with_nested_markets: bool = False,
    ) -> Event:
        """Get an Event by ticker.

        Args:
            event_ticker: The event ticker.
            with_nested_markets: If True, include markets nested in the event object.
        """
        params = {}
        if with_nested_markets:
            params["with_nested_markets"] = "true"
        endpoint = f"/events/{event_ticker}"
        if params:
            endpoint += "?" + urlencode(params)
        response = self.get(endpoint)
        model = EventModel.model_validate(response["event"])
        return Event(self, model)

    def get_events(
        self,
        *,
        series_ticker: str | None = None,
        status: MarketStatus | None = None,
        limit: int = 100,
        cursor: str | None = None,
        fetch_all: bool = False,
        **extra_params,
    ) -> DataFrameList[Event]:
        """Search for events.

        Args:
            series_ticker: Filter by series ticker.
            status: Filter by event status.
            limit: Maximum results per page (default 100).
            cursor: Pagination cursor for fetching next page.
            fetch_all: If True, automatically fetch all pages.
            **extra_params: Additional API parameters.
        """
        params = {
            "limit": limit,
            "series_ticker": series_ticker,
            "status": status.value if status is not None else None,
            "cursor": cursor,
            **extra_params,
        }
        data = self.paginated_get("/events", "events", params, fetch_all)
        return DataFrameList(Event(self, EventModel.model_validate(e)) for e in data)

    def get_series(
        self,
        series_ticker: str,
        *,
        include_volume: bool = False,
    ) -> Series:
        """Get a Series by ticker.

        Args:
            series_ticker: The series ticker.
            include_volume: If True, include total volume traded across all events.
        """
        params = {}
        if include_volume:
            params["include_volume"] = "true"
        endpoint = f"/series/{series_ticker}"
        if params:
            endpoint += "?" + urlencode(params)
        response = self.get(endpoint)
        model = SeriesModel.model_validate(response["series"])
        return Series(self, model)

    def get_all_series(
        self,
        *,
        category: str | None = None,
        limit: int = 100,
        cursor: str | None = None,
        fetch_all: bool = False,
        **extra_params,
    ) -> DataFrameList[Series]:
        """List all series.

        Args:
            category: Filter by category.
            limit: Maximum results per page (default 100).
            cursor: Pagination cursor for fetching next page.
            fetch_all: If True, automatically fetch all pages.
            **extra_params: Additional API parameters.
        """
        params = {"limit": limit, "category": category, "cursor": cursor, **extra_params}
        data = self.paginated_get("/series", "series", params, fetch_all)
        return DataFrameList(Series(self, SeriesModel.model_validate(s)) for s in data)

    def get_trades(
        self,
        *,
        ticker: str | None = None,
        min_ts: int | None = None,
        max_ts: int | None = None,
        limit: int = 100,
        cursor: str | None = None,
        fetch_all: bool = False,
        **extra_params,
    ) -> DataFrameList[TradeModel]:
        """Get public trade history.

        Args:
            ticker: Filter by market ticker.
            min_ts: Minimum timestamp (Unix seconds).
            max_ts: Maximum timestamp (Unix seconds).
            limit: Maximum trades per page (default 100).
            cursor: Pagination cursor for fetching next page.
            fetch_all: If True, automatically fetch all pages.
            **extra_params: Additional API parameters.
        """
        params = {
            "limit": limit,
            "ticker": ticker,
            "min_ts": min_ts,
            "max_ts": max_ts,
            "cursor": cursor,
            **extra_params,
        }
        data = self.paginated_get("/markets/trades", "trades", params, fetch_all)
        return DataFrameList(TradeModel.model_validate(t) for t in data)

    def get_candlesticks_batch(
        self,
        tickers: list[str],
        start_ts: int,
        end_ts: int,
        period: CandlestickPeriod = CandlestickPeriod.ONE_HOUR,
    ) -> dict[str, CandlestickResponse]:
        """Batch fetch candlesticks for multiple markets (up to 100 tickers).

        Args:
            tickers: List of market tickers (max 100).
            start_ts: Start timestamp (Unix seconds).
            end_ts: End timestamp (Unix seconds).
            period: Candlestick period (ONE_MINUTE, ONE_HOUR, or ONE_DAY).

        Returns:
            Dict mapping ticker to CandlestickResponse.
        """
        query = urlencode({
            "market_tickers": ",".join(tickers),
            "start_ts": start_ts,
            "end_ts": end_ts,
            "period_interval": period.value,
        })
        response = self.get(f"/markets/candlesticks?{query}")
        return {
            item["market_ticker"]: CandlestickResponse.model_validate(item)
            for item in response.get("markets", [])
        }
