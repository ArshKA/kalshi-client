"""Integration tests that use the real Kalshi API.

These tests perform READ-ONLY operations against the live API.
No orders are placed to avoid risking real money.

Run with: pytest tests/test_integration.py -v
"""

import pytest
from kalshi_api import KalshiClient
from kalshi_api.enums import MarketStatus


@pytest.fixture(scope="module")
def live_client():
    """Create a real KalshiClient using credentials from .env"""
    return KalshiClient.from_env()


class TestLiveAPI:
    """Integration tests against the real Kalshi API."""

    def test_get_balance(self, live_client):
        """Test fetching real account balance."""
        balance = live_client.portfolio.get_balance()

        print(f"\n  Balance: ${balance.balance / 100:.2f}")
        print(f"  Portfolio Value: ${balance.portfolio_value / 100:.2f}")

        assert balance.balance >= 0
        assert balance.portfolio_value >= 0

    def test_get_markets(self, live_client):
        """Test fetching open markets."""
        markets = live_client.get_markets(status=MarketStatus.OPEN, limit=5)

        print(f"\n  Found {len(markets)} markets")
        for m in markets[:3]:
            print(f"  - {m.ticker}: {m.title}")

        assert len(markets) > 0
        assert all(m.ticker for m in markets)

    def test_get_single_market(self, live_client):
        """Test fetching a specific market."""
        markets = live_client.get_markets(status=MarketStatus.OPEN, limit=1)
        assert len(markets) > 0

        ticker = markets[0].ticker
        market = live_client.get_market(ticker)

        print(f"\n  Market: {market.ticker}")
        print(f"  Title: {market.title}")
        print(f"  Yes Bid/Ask: {market.yes_bid}/{market.yes_ask}")

        assert market.ticker == ticker

    def test_get_orderbook(self, live_client):
        """Test fetching an orderbook."""
        markets = live_client.get_markets(status=MarketStatus.OPEN, limit=1)
        assert len(markets) > 0

        market = markets[0]
        orderbook = market.get_orderbook()

        print(f"\n  Orderbook for {market.ticker}:")
        print(f"  Yes levels: {len(orderbook.yes_levels)}")
        print(f"  No levels: {len(orderbook.no_levels)}")
        if orderbook.best_yes_bid is not None:
            print(f"  Best yes bid: {orderbook.best_yes_bid}")

        assert orderbook.orderbook is not None

    def test_get_positions(self, live_client):
        """Test fetching portfolio positions."""
        positions = live_client.portfolio.get_positions(limit=10)

        print(f"\n  Found {len(positions)} positions")
        for p in positions[:5]:
            print(f"  - {p.ticker}: {p.position} contracts")

        assert isinstance(positions, list)

    def test_get_fills(self, live_client):
        """Test fetching trade history."""
        fills = live_client.portfolio.get_fills(limit=10)

        print(f"\n  Found {len(fills)} recent fills")
        for f in fills[:3]:
            print(f"  - {f.ticker}: {f.action.value} {f.count} @ {f.yes_price}")

        assert isinstance(fills, list)

    def test_get_orders(self, live_client):
        """Test fetching orders."""
        orders = live_client.portfolio.get_orders(limit=10)

        print(f"\n  Found {len(orders)} orders")
        for o in orders[:3]:
            print(f"  - {o.ticker}: {o.status.value}")

        assert isinstance(orders, list)
