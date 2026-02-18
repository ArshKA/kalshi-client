"""Shared fixtures for integration tests.

These tests run against the Kalshi Demo API with real market data
but fake money, making mutations safe to test.

Credentials can be provided in two ways:

1. Demo-specific env vars (recommended):
    KALSHI_DEMO_API_KEY_ID: Demo API key ID
    KALSHI_DEMO_PRIVATE_KEY_PATH: Path to demo private key file

2. Load from .env.demo file:
    Create .env.demo with KALSHI_API_KEY_ID and KALSHI_PRIVATE_KEY_PATH

Run with: pytest tests/integration/ -v
Skip with: pytest tests/ --ignore=tests/integration/
"""

import os
import pytest
from pathlib import Path


def _get_demo_credentials():
    """Get demo credentials from environment.

    Checks KALSHI_DEMO_* first, then loads .env.demo if available.
    """
    # First try KALSHI_DEMO_* vars
    key_id = os.getenv("KALSHI_DEMO_API_KEY_ID")
    key_path = os.getenv("KALSHI_DEMO_PRIVATE_KEY_PATH")

    if key_id and key_path:
        return key_id, key_path

    # Try loading .env.demo
    env_demo = Path(__file__).parent.parent.parent / ".env.demo"
    if env_demo.exists():
        with open(env_demo) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    if k == "KALSHI_API_KEY_ID":
                        key_id = v
                    elif k == "KALSHI_PRIVATE_KEY_PATH":
                        # Resolve relative to repo root
                        key_path = str(env_demo.parent / v)

    return key_id, key_path


def _has_demo_credentials():
    """Check if demo credentials are available."""
    key_id, key_path = _get_demo_credentials()
    return key_id and key_path and os.path.exists(key_path)


# Skip all tests in this directory if no demo credentials
pytestmark = pytest.mark.skipif(
    not _has_demo_credentials(),
    reason="Demo credentials not set. Set KALSHI_DEMO_API_KEY_ID/PATH or create .env.demo",
)


@pytest.fixture(scope="session")
def client():
    """Demo client for integration tests.

    Session-scoped to reuse connection across tests.
    Skips entire suite if the Kalshi API is unavailable (503/5xx).
    """
    from pykalshi import KalshiClient

    key_id, key_path = _get_demo_credentials()
    c = KalshiClient(
        api_key_id=key_id,
        private_key_path=key_path,
        demo=True,
    )

    # Health check: skip the whole suite if the API is down
    try:
        c.get_markets(limit=1)
    except Exception as e:
        pytest.skip(f"Kalshi API unavailable, skipping integration tests: {e}")

    return c


@pytest.fixture(scope="session")
def active_market(client):
    """Get an active open market for testing.

    Session-scoped to avoid repeated API calls.
    Prefers markets with higher 24h volume for more reliable tests.
    """
    from pykalshi.enums import MarketStatus

    markets = client.get_markets(limit=50, status=MarketStatus.OPEN)
    if not markets:
        pytest.skip("No open markets available")

    # Prefer markets with volume (more likely to have activity)
    markets_with_volume = [m for m in markets if m.volume_24h]
    if markets_with_volume:
        return max(markets_with_volume, key=lambda m: m.volume_24h or 0)

    # Fall back to any market with bid/ask
    for m in markets:
        if m.yes_bid or m.yes_ask:
            return m

    return markets[0]
