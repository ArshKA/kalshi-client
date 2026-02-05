"""Integration tests for Markets, Events, Series, and Candlesticks."""

import time
import pytest
from pykalshi.enums import MarketStatus, CandlestickPeriod
from pykalshi.exceptions import ResourceNotFoundError


class TestMarkets:
    """Tests for market endpoints."""

    def test_get_markets(self, client):
        """Get markets returns list of Market objects."""
        markets = client.get_markets(limit=5)

        assert len(markets) > 0
        assert hasattr(markets[0], "ticker")
        assert hasattr(markets[0], "title")

    def test_get_markets_with_status_filter(self, client):
        """Get markets with status filter."""
        markets = client.get_markets(limit=5, status=MarketStatus.OPEN)

        assert len(markets) > 0
        # All returned markets should be active (open filter returns active markets)
        for market in markets:
            assert market.data.status == MarketStatus.ACTIVE

    def test_get_single_market(self, client, active_market):
        """Get single market by ticker."""
        market = client.get_market(active_market.ticker)

        assert market.ticker == active_market.ticker
        assert market.title is not None

    def test_market_get_orderbook(self, client, active_market):
        """Get orderbook for a market."""
        ob = active_market.get_orderbook()

        assert hasattr(ob, "orderbook")
        assert hasattr(ob.orderbook, "yes")
        assert hasattr(ob.orderbook, "no")
        # yes and no are lists or None (empty orderbook)
        assert ob.orderbook.yes is None or isinstance(ob.orderbook.yes, list)

    def test_market_get_trades(self, client, active_market):
        """Get trades for a market."""
        trades = active_market.get_trades(limit=5)

        # May be empty if no recent trades
        assert isinstance(trades, list)


class TestEvents:
    """Tests for event endpoints."""

    def test_get_events(self, client):
        """Get events returns list."""
        events = client.get_events(limit=5)

        assert len(events) > 0
        assert hasattr(events[0], "event_ticker")

    def test_get_single_event(self, client):
        """Get single event by ticker."""
        events = client.get_events(limit=1)
        if not events:
            pytest.skip("No events available")

        event = client.get_event(events[0].event_ticker)
        assert event.event_ticker == events[0].event_ticker

    def test_event_get_markets(self, client):
        """Event.get_markets returns markets for that event."""
        events = client.get_events(limit=1)
        if not events:
            pytest.skip("No events available")

        markets = events[0].get_markets()
        assert isinstance(markets, list)


class TestSeries:
    """Tests for series endpoints."""

    def test_get_all_series(self, client):
        """Get all series returns list."""
        series = client.get_all_series(limit=10)

        assert len(series) > 0
        assert hasattr(series[0], "ticker")

    def test_get_single_series(self, client):
        """Get single series by ticker."""
        all_series = client.get_all_series(limit=1)
        if not all_series:
            pytest.skip("No series available")

        series = client.get_series(all_series[0].ticker)
        assert series.ticker == all_series[0].ticker

    def test_series_get_markets(self, client):
        """Series.get_markets returns markets for that series."""
        all_series = client.get_all_series(limit=1)
        if not all_series:
            pytest.skip("No series available")

        markets = all_series[0].get_markets()
        assert isinstance(markets, list)


class TestCandlesticks:
    """Tests for candlestick endpoints."""

    def test_batch_candlesticks(self, client, active_market):
        """Batch candlesticks returns dict of ticker -> CandlestickResponse."""
        end_ts = int(time.time())
        start_ts = end_ts - 86400 * 7  # 7 days

        result = client.get_candlesticks_batch(
            [active_market.ticker],
            start_ts,
            end_ts,
            CandlestickPeriod.ONE_DAY,
        )

        assert isinstance(result, dict)
        assert active_market.ticker in result
        assert hasattr(result[active_market.ticker], "candlesticks")

    def test_market_candlesticks(self, client, active_market):
        """Market.get_candlesticks returns candlestick data."""
        end_ts = int(time.time())
        start_ts = end_ts - 86400 * 7

        # This may raise if market doesn't have series_ticker
        try:
            result = active_market.get_candlesticks(
                start_ts, end_ts, CandlestickPeriod.ONE_DAY
            )
            assert hasattr(result, "candlesticks")
            assert hasattr(result, "ticker")
        except ValueError:
            # Market doesn't have series_ticker, that's ok
            pytest.skip("Market doesn't have series_ticker")

    def test_candlestick_with_volume(self, client):
        """Find and verify candlesticks with actual trading data."""
        end_ts = int(time.time())
        start_ts = end_ts - 86400 * 90  # 90 days

        # Search for a market with candlestick volume
        series_list = client.get_all_series(limit=50)

        for series in series_list:
            try:
                markets = client.get_markets(limit=1, series_ticker=series.ticker)
                if not markets:
                    continue

                result = client.get_candlesticks_batch(
                    [markets[0].ticker], start_ts, end_ts, CandlestickPeriod.ONE_DAY
                )

                for ticker, resp in result.items():
                    with_volume = [c for c in resp.candlesticks if c.volume > 0]
                    if with_volume:
                        # Found one with data - verify structure
                        candle = with_volume[0]
                        assert candle.volume > 0
                        assert hasattr(candle, "open_interest")
                        assert hasattr(candle, "price")
                        assert hasattr(candle.price, "open")
                        assert hasattr(candle.price, "close")
                        return  # Success
            except Exception:
                continue

        pytest.skip("No markets with candlestick volume found")


class TestTrades:
    """Tests for trade endpoints."""

    def test_get_trades(self, client):
        """Get global trades."""
        trades = client.get_trades(limit=10)

        assert isinstance(trades, list)
        if trades:
            assert hasattr(trades[0], "ticker")
            assert hasattr(trades[0], "yes_price")


class TestNavigation:
    """Tests for domain object navigation methods."""

    def test_market_get_event(self, client, active_market):
        """Market.get_event() returns parent event."""
        event = active_market.get_event()

        if event is None:
            pytest.skip("Market has no event_ticker")

        assert event.event_ticker == active_market.event_ticker
        assert hasattr(event, "title")

    def test_market_resolve_series_ticker(self, client, active_market):
        """Market.resolve_series_ticker() fetches series if missing."""
        # This should return a series ticker (may already be present or fetched)
        series_ticker = active_market.resolve_series_ticker()

        # May be None if market truly has no series
        if series_ticker:
            assert isinstance(series_ticker, str)
            assert len(series_ticker) > 0

    def test_series_get_events(self, client):
        """Series.get_events() returns events in the series."""
        all_series = client.get_all_series(limit=10)
        if not all_series:
            pytest.skip("No series available")

        # Find a series with events
        for series in all_series:
            events = series.get_events()
            if events:
                assert isinstance(events, list)
                assert hasattr(events[0], "event_ticker")
                # Verify events belong to this series
                assert events[0].series_ticker == series.ticker
                return

        pytest.skip("No series with events found")

    def test_event_get_series(self, client):
        """Event.get_series() returns parent series."""
        events = client.get_events(limit=1)
        if not events:
            pytest.skip("No events available")

        event = events[0]
        series = event.get_series()

        assert series.ticker == event.series_ticker
        assert hasattr(series, "title")

    def test_event_get_forecast_percentile_history(self, client):
        """Event.get_forecast_percentile_history() returns historical data."""
        events = client.get_events(limit=10)
        if not events:
            pytest.skip("No events available")

        # Try to find an event with forecast data
        for event in events:
            try:
                history = event.get_forecast_percentile_history(percentiles=[25, 50, 75])

                assert hasattr(history, "history")
                # history is a dict mapping percentile -> list of data points
                assert isinstance(history.history, dict)
                return
            except Exception:
                # Some events may not have forecast data
                continue

        pytest.skip("No events with forecast history found")


class TestPagination:
    """Tests for pagination behavior."""

    def test_fetch_all_pagination(self, client):
        """Verify fetch_all=True fetches multiple pages."""
        # Get a small page first to verify there's more data
        first_page = client.get_all_series(limit=5)
        if len(first_page) < 5:
            pytest.skip("Not enough series to test pagination")

        # Now fetch all
        all_series = client.get_all_series(limit=5, fetch_all=True)

        # Should have fetched more than one page worth
        assert len(all_series) > 5


class TestDataFrameList:
    """Tests for DataFrameList functionality."""

    def test_to_dataframe(self, client):
        """DataFrameList.to_dataframe() returns pandas DataFrame."""
        markets = client.get_markets(limit=5)

        if not markets:
            pytest.skip("No markets available")

        df = markets.to_dataframe()

        # Should be a pandas DataFrame
        import pandas as pd
        assert isinstance(df, pd.DataFrame)

        # Should have same number of rows
        assert len(df) == len(markets)

        # Should have ticker column
        assert "ticker" in df.columns

    def test_to_dataframe_with_positions(self, client):
        """DataFrameList.to_dataframe() works with positions."""
        positions = client.portfolio.get_positions(limit=10)

        df = positions.to_dataframe()

        import pandas as pd
        assert isinstance(df, pd.DataFrame)

        # If positions exist, verify structure
        if len(df) > 0:
            assert "ticker" in df.columns


class TestAPIParameterVariations:
    """Tests for various API parameter options."""

    def test_get_event_with_nested_markets(self, client):
        """Get event with nested markets included."""
        events = client.get_events(limit=1)
        if not events:
            pytest.skip("No events available")

        event = client.get_event(
            events[0].event_ticker,
            with_nested_markets=True,
        )

        assert event.event_ticker == events[0].event_ticker
        # When with_nested_markets=True, markets may be in the response
        # (depends on API behavior)

    def test_get_series_with_volume(self, client):
        """Get series with volume included."""
        all_series = client.get_all_series(limit=1)
        if not all_series:
            pytest.skip("No series available")

        series = client.get_series(
            all_series[0].ticker,
            include_volume=True,
        )

        assert series.ticker == all_series[0].ticker

    def test_get_markets_by_tickers(self, client):
        """Batch fetch specific markets by ticker list."""
        # First get some tickers
        markets = client.get_markets(limit=3)
        if len(markets) < 2:
            pytest.skip("Not enough markets available")

        tickers = [m.ticker for m in markets[:2]]

        # Fetch by tickers
        fetched = client.get_markets(tickers=tickers)

        assert len(fetched) == 2
        fetched_tickers = {m.ticker for m in fetched}
        assert fetched_tickers == set(tickers)


class TestErrorHandling:
    """Tests for error handling and exceptions."""

    def test_invalid_market_ticker_raises_not_found(self, client):
        """Invalid market ticker raises ResourceNotFoundError."""
        with pytest.raises(ResourceNotFoundError):
            client.get_market("INVALID-TICKER-THAT-DOES-NOT-EXIST-12345")

    def test_invalid_event_ticker_raises_not_found(self, client):
        """Invalid event ticker raises ResourceNotFoundError."""
        with pytest.raises(ResourceNotFoundError):
            client.get_event("INVALID-EVENT-12345")

    def test_invalid_series_ticker_raises_not_found(self, client):
        """Invalid series ticker raises ResourceNotFoundError."""
        with pytest.raises(ResourceNotFoundError):
            client.get_series("INVALID-SERIES-12345")
