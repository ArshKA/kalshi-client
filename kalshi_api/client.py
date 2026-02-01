"""
Kalshi API Client

Core client class for authenticated API requests.
"""

import os
import time
import json
import logging
from base64 import b64encode
from typing import Any
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)


from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from dotenv import load_dotenv

from .exceptions import (
    KalshiAPIError,
    AuthenticationError,
    InsufficientFundsError,
    ResourceNotFoundError,
)
from .markets import Market
from .models import MarketModel
from .portfolio import User


# Load environment variables
load_dotenv()

# Default configuration
DEFAULT_API_BASE = "https://api.elections.kalshi.com/trade-api/v2"
DEMO_API_BASE = "https://demo-api.elections.kalshi.com/trade-api/v2"


class KalshiClient:
    """
    Authenticated client for the Kalshi Trading API.

    Usage:
        client = KalshiClient()  # Uses env vars
        client = KalshiClient(api_key_id="...", private_key_path="...")
    """

    def __init__(
        self,
        api_key_id: str | None = None,
        private_key_path: str | None = None,
        api_base: str | None = None,
        demo: bool = False,
    ) -> None:
        """
        Initialize the Kalshi client.

        Args:
            api_key_id: API key ID. Defaults to KALSHI_API_KEY_ID env var.
            private_key_path: Path to private key file. Defaults to KALSHI_PRIVATE_KEY_PATH env var.
            api_base: API base URL. Defaults to production or demo based on `demo` flag.
            demo: If True, use demo environment. Ignored if api_base is provided.
        """
        self.api_key_id = api_key_id or os.getenv("KALSHI_API_KEY_ID")
        private_key_path = private_key_path or os.getenv("KALSHI_PRIVATE_KEY_PATH")

        if not self.api_key_id:
            raise ValueError(
                "API key ID required. Set KALSHI_API_KEY_ID env var or pass api_key_id."
            )
        if not private_key_path:
            raise ValueError(
                "Private key path required. Set KALSHI_PRIVATE_KEY_PATH env var or pass private_key_path."
            )

        self.api_base = api_base or (DEMO_API_BASE if demo else DEFAULT_API_BASE)
        self.private_key = self._load_private_key(private_key_path)

    def _load_private_key(self, key_path: str) -> RSAPrivateKey:
        """Load RSA private key from PEM file."""
        with open(key_path, "rb") as f:
            key = serialization.load_pem_private_key(f.read(), password=None)
            if not isinstance(key, RSAPrivateKey):
                raise TypeError(f"Expected RSA private key, got {type(key).__name__}")
            return key

    @property
    def exchange(self) -> str:
        """Exchange identifier for unified backtesting."""
        return "kalshi"

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
        # IMPORTANT: Signature must NOT include query parameters
        # Use urlparse to cleanly extract just the path
        path_without_query = urlparse(endpoint).path
        full_path = f"/trade-api/v2{path_without_query}"
        timestamp, signature = self._sign_request(method, full_path)
        return {
            "Content-Type": "application/json",
            "KALSHI-ACCESS-KEY": self.api_key_id,
            "KALSHI-ACCESS-SIGNATURE": signature,
            "KALSHI-ACCESS-TIMESTAMP": timestamp,
        }

    def _handle_response(self, response: requests.Response) -> dict[str, Any]:
        """Handle API response and raise custom exceptions."""
        status_code = int(response.status_code or 500)

        if status_code < 400:
            logger.debug("Response %s: Success", status_code)
            return response.json()

        logger.error("Response %s: Error body: %s", status_code, response.text)
        try:
            error_data = response.json()
            message = error_data.get("message") or error_data.get(
                "error_message", "Unknown Error"
            )
            code = error_data.get("code") or error_data.get("error_code")
        except ValueError:
            message = response.text
            code = None

        if status_code in (401, 403):
            raise AuthenticationError(status_code, message, code)
        elif status_code == 404:
            raise ResourceNotFoundError(status_code, message, code)
        elif code in ("insufficient_funds", "insufficient_balance"):
            raise InsufficientFundsError(status_code, message, code)
        else:
            raise KalshiAPIError(status_code, message, code)

    def get(self, endpoint: str) -> dict[str, Any]:
        """Make authenticated GET request."""
        url = f"{self.api_base}{endpoint}"
        logger.debug("GET %s", url)
        headers = self._get_headers("GET", endpoint)
        response = requests.get(url, headers=headers)
        return self._handle_response(response)

    def post(self, endpoint: str, data: dict[str, Any]) -> dict[str, Any]:
        """Make authenticated POST request."""
        url = f"{self.api_base}{endpoint}"
        logger.debug("POST %s", url)
        body = json.dumps(data, separators=(",", ":"))
        headers = self._get_headers("POST", endpoint)
        response = requests.post(url, headers=headers, data=body)
        return self._handle_response(response)

    def delete(self, endpoint: str) -> dict[str, Any]:
        """Make authenticated DELETE request."""
        url = f"{self.api_base}{endpoint}"
        headers = self._get_headers("DELETE", endpoint)
        response = requests.delete(url, headers=headers)
        return self._handle_response(response)

    def get_market(self, ticker: str) -> Market:
        """
        Get a Market object by ticker.
        """
        response = self.get(f"/markets/{ticker}")
        data = response.get("market", response)

        model = MarketModel.model_validate(data)
        return Market(self, model)

    def get_markets(
        self,
        series_ticker: str | None = None,
        event_ticker: str | None = None,
        status: str = "open",
        limit: int = 100,
        cursor: str | None = None,
        fetch_all: bool = False,
    ) -> list[Market]:
        """
        Search for markets.

        Args:
            series_ticker: Filter by series ticker.
            event_ticker: Filter by event ticker.
            status: Filter by market status (default: "open").
            limit: Maximum results per page (default: 100, max: 1000).
            cursor: Pagination cursor for fetching next page.
            fetch_all: If True, automatically fetch all pages.

        Returns:
            List of Market objects.
        """
        all_markets: list[Market] = []
        current_cursor = cursor

        while True:
            params = [f"status={status}", f"limit={limit}"]
            if series_ticker:
                params.append(f"series_ticker={series_ticker}")
            if event_ticker:
                params.append(f"event_ticker={event_ticker}")
            if current_cursor:
                params.append(f"cursor={current_cursor}")

            endpoint = f"/markets?{'&'.join(params)}"
            response = self.get(endpoint)
            markets_data = response.get("markets", [])

            markets = [Market(self, MarketModel.model_validate(m)) for m in markets_data]
            all_markets.extend(markets)

            # Check for next page
            next_cursor = response.get("cursor", "")
            if not fetch_all or not next_cursor:
                break
            current_cursor = next_cursor

        return all_markets

    def get_markets_paginated(
        self,
        series_ticker: str | None = None,
        event_ticker: str | None = None,
        status: str = "open",
        limit: int = 100,
        cursor: str | None = None,
    ) -> tuple[list[Market], str]:
        """
        Search for markets with pagination info.

        Args:
            series_ticker: Filter by series ticker.
            event_ticker: Filter by event ticker.
            status: Filter by market status (default: "open").
            limit: Maximum results per page (default: 100, max: 1000).
            cursor: Pagination cursor for fetching next page.

        Returns:
            Tuple of (list of Market objects, next cursor string).
            Empty cursor string indicates no more pages.
        """
        params = [f"status={status}", f"limit={limit}"]
        if series_ticker:
            params.append(f"series_ticker={series_ticker}")
        if event_ticker:
            params.append(f"event_ticker={event_ticker}")
        if cursor:
            params.append(f"cursor={cursor}")

        endpoint = f"/markets?{'&'.join(params)}"
        response = self.get(endpoint)
        markets_data = response.get("markets", [])
        next_cursor = response.get("cursor", "")

        markets = [Market(self, MarketModel.model_validate(m)) for m in markets_data]
        return markets, next_cursor

    def get_user(self) -> User:
        """
        Get the authenticated User object.
        """
        return User(self)

