"""Integration tests for AsyncKalshiClient against the Kalshi Demo API."""

import pytest
from pykalshi import AsyncMarket, AsyncEvent
from pykalshi.enums import MarketStatus


class TestAsyncMarkets:
    """Test async market retrieval against real API."""

    @pytest.mark.asyncio
    async def test_get_markets(self, async_client):
        """Fetch markets and verify structure."""
        markets = await async_client.get_markets(limit=5)
        assert len(markets) > 0
        assert all(isinstance(m, AsyncMarket) for m in markets)
        # All markets should have a ticker
        for m in markets:
            assert m.ticker

    @pytest.mark.asyncio
    async def test_get_market(self, async_client):
        """Fetch a single market by ticker."""
        markets = await async_client.get_markets(limit=1)
        if not markets:
            pytest.skip("No markets available")
        ticker = markets[0].ticker

        market = await async_client.get_market(ticker)
        assert isinstance(market, AsyncMarket)
        assert market.ticker == ticker

    @pytest.mark.asyncio
    async def test_get_market_orderbook(self, async_client):
        """Fetch orderbook for a market."""
        markets = await async_client.get_markets(limit=5, status=MarketStatus.OPEN)
        if not markets:
            pytest.skip("No open markets available")

        ob = await markets[0].get_orderbook()
        assert ob.orderbook is not None


class TestAsyncEvents:
    """Test async event retrieval."""

    @pytest.mark.asyncio
    async def test_get_events(self, async_client):
        """Fetch events."""
        events = await async_client.get_events(limit=3)
        assert len(events) > 0
        assert all(isinstance(e, AsyncEvent) for e in events)

    @pytest.mark.asyncio
    async def test_get_event(self, async_client):
        """Fetch a single event."""
        events = await async_client.get_events(limit=1)
        if not events:
            pytest.skip("No events available")

        event = await async_client.get_event(events[0].event_ticker)
        assert isinstance(event, AsyncEvent)
        assert event.event_ticker == events[0].event_ticker


class TestAsyncPortfolio:
    """Test async portfolio operations."""

    @pytest.mark.asyncio
    async def test_get_balance(self, async_client):
        """Fetch account balance."""
        balance = await async_client.portfolio.get_balance()
        assert balance.balance is not None

    @pytest.mark.asyncio
    async def test_get_positions(self, async_client):
        """Fetch positions (may be empty)."""
        positions = await async_client.portfolio.get_positions()
        assert isinstance(positions, list)


class TestAsyncExchange:
    """Test async exchange operations."""

    @pytest.mark.asyncio
    async def test_get_status(self, async_client):
        """Fetch exchange status."""
        status = await async_client.exchange.get_status()
        assert status.exchange_active is not None

    @pytest.mark.asyncio
    async def test_is_trading(self, async_client):
        """Check trading status."""
        result = await async_client.exchange.is_trading()
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_get_schedule(self, async_client):
        """Fetch exchange schedule."""
        schedule = await async_client.exchange.get_schedule()
        assert isinstance(schedule, dict)
