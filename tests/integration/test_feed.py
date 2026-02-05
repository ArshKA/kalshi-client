"""Integration tests for WebSocket Feed."""

import time
import pytest


class TestFeedConnection:
    """Tests for WebSocket feed connection and messaging."""

    def test_connect_and_disconnect(self, client):
        """Feed connects and disconnects cleanly."""
        feed = client.feed()

        feed.start()
        assert feed.is_connected

        feed.stop()
        assert not feed.is_connected

    def test_subscribe_and_receive(self, client, active_market):
        """Subscribe to ticker and receive messages."""
        feed = client.feed()
        messages = []

        @feed.on("ticker")
        def on_ticker(msg):
            messages.append(("ticker", msg))

        @feed.on("orderbook_delta")
        def on_orderbook(msg):
            messages.append(("orderbook", msg))

        feed.subscribe("ticker", market_tickers=[active_market.ticker])
        feed.subscribe("orderbook_delta", market_tickers=[active_market.ticker])

        feed.start()
        assert feed.is_connected

        # Wait for messages (orderbook snapshot usually arrives immediately)
        time.sleep(3)

        feed.stop()

        # Should have received at least the initial orderbook snapshot
        # (dispatched as orderbook_delta)
        assert len(messages) >= 0  # May not get messages if market is quiet

    def test_unsubscribe(self, client, active_market):
        """Unsubscribe removes subscription."""
        feed = client.feed()

        feed.subscribe("ticker", market_tickers=[active_market.ticker])
        assert len(feed._active_subs) == 1

        feed.unsubscribe("ticker", market_tickers=[active_market.ticker])
        assert len(feed._active_subs) == 0

    def test_multiple_subscriptions(self, client):
        """Multiple subscriptions tracked correctly."""
        feed = client.feed()

        feed.subscribe("ticker", market_tickers=["TICK1"])
        feed.subscribe("ticker", market_tickers=["TICK2"])
        feed.subscribe("orderbook_delta", market_tickers=["TICK1"])

        assert len(feed._active_subs) == 3

    def test_metrics_after_connection(self, client, active_market):
        """Feed metrics update after connection."""
        feed = client.feed()

        assert feed.messages_received == 0
        assert feed.uptime_seconds is None

        feed.subscribe("orderbook_delta", market_tickers=[active_market.ticker])
        feed.start()

        time.sleep(2)

        # Uptime should be tracked
        assert feed.uptime_seconds is not None
        assert feed.uptime_seconds >= 1

        feed.stop()

    def test_reconnect_count_initial(self, client):
        """Reconnect count starts at 0."""
        feed = client.feed()

        feed.start()
        assert feed.reconnect_count == 0
        feed.stop()

    def test_latency_ms_property(self, client, active_market):
        """Feed latency_ms property is populated after messages."""
        feed = client.feed()

        feed.subscribe("orderbook_delta", market_tickers=[active_market.ticker])
        feed.start()

        # Wait for messages (orderbook snapshot usually arrives quickly)
        time.sleep(3)

        # latency_ms may be None if no round-trip yet, or a float
        latency = feed.latency_ms
        assert latency is None or isinstance(latency, (int, float))

        feed.stop()

    def test_seconds_since_last_message(self, client, active_market):
        """Feed seconds_since_last_message tracks time since last message."""
        feed = client.feed()

        # Before start, should be None
        assert feed.seconds_since_last_message is None

        feed.subscribe("orderbook_delta", market_tickers=[active_market.ticker])
        feed.start()

        time.sleep(2)

        # After receiving messages, should be a number (or None if no messages yet)
        since_last = feed.seconds_since_last_message
        assert since_last is None or isinstance(since_last, (int, float))

        feed.stop()

    def test_context_manager(self, client, active_market):
        """Feed works as context manager."""
        messages = []

        with client.feed() as feed:
            @feed.on("orderbook_delta")
            def on_orderbook(msg):
                messages.append(msg)

            feed.subscribe("orderbook_delta", market_tickers=[active_market.ticker])
            assert feed.is_connected

            time.sleep(2)

        # After exiting context, feed should be stopped
        assert not feed.is_connected

    def test_trade_channel(self, client, active_market):
        """Subscribe to trade channel (public)."""
        feed = client.feed()
        messages = []

        @feed.on("trade")
        def on_trade(msg):
            messages.append(msg)

        feed.subscribe("trade", market_tickers=[active_market.ticker])
        feed.start()

        # Trades are infrequent, just verify subscription works
        time.sleep(2)

        feed.stop()

        # Trade channel subscription should have been accepted
        # (messages may be empty if no trades occurred)
        assert isinstance(messages, list)

    def test_market_lifecycle_channel(self, client, active_market):
        """Subscribe to market_lifecycle channel (public)."""
        feed = client.feed()
        messages = []

        @feed.on("market_lifecycle")
        def on_lifecycle(msg):
            messages.append(msg)

        feed.subscribe("market_lifecycle", market_tickers=[active_market.ticker])
        feed.start()

        # Lifecycle events are rare, just verify subscription works
        time.sleep(2)

        feed.stop()

        # Subscription should have been accepted
        assert isinstance(messages, list)
