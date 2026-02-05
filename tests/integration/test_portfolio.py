"""Integration tests for Portfolio endpoints."""

import pytest
from pykalshi.enums import Action, Side, OrderStatus, MarketStatus


class TestPortfolioReadOnly:
    """Read-only portfolio tests - safe to run anytime."""

    def test_get_balance(self, client):
        """Get account balance."""
        balance = client.portfolio.get_balance()

        assert hasattr(balance, "balance")
        assert hasattr(balance, "portfolio_value")
        assert isinstance(balance.balance, int)

    def test_get_positions(self, client):
        """Get positions list."""
        positions = client.portfolio.get_positions(limit=10)

        assert isinstance(positions, list)
        # If positions exist, verify structure
        if positions:
            pos = positions[0]
            assert hasattr(pos, "ticker")
            assert hasattr(pos, "position")

    def test_get_orders(self, client):
        """Get orders list."""
        orders = client.portfolio.get_orders(limit=10)

        assert isinstance(orders, list)
        if orders:
            order = orders[0]
            assert hasattr(order, "order_id")
            assert hasattr(order, "ticker")
            assert hasattr(order, "status")

    def test_get_fills(self, client):
        """Get fills list."""
        fills = client.portfolio.get_fills(limit=10)

        assert isinstance(fills, list)
        if fills:
            fill = fills[0]
            assert hasattr(fill, "ticker")
            assert hasattr(fill, "yes_price")

    def test_get_settlements(self, client):
        """Get settlements list."""
        settlements = client.portfolio.get_settlements(limit=10)

        assert isinstance(settlements, list)
        if settlements:
            settlement = settlements[0]
            assert hasattr(settlement, "ticker")


class TestOrderGroups:
    """Tests for order group endpoints."""

    def test_get_order_groups_empty(self, client):
        """Get order groups (may be empty)."""
        groups = client.portfolio.get_order_groups()

        assert isinstance(groups, list)

    def test_order_group_lifecycle(self, client):
        """Full lifecycle: create, get, update, reset, delete order group."""
        from pykalshi.enums import MarketStatus

        # Find an open market
        markets = client.get_markets(limit=10, status=MarketStatus.OPEN)
        market = None
        for m in markets:
            if m.yes_bid or m.yes_ask:
                market = m
                break
        if not market:
            market = markets[0] if markets else None
        if not market:
            pytest.skip("No open markets available")

        # Create 2 resting orders to link
        order1 = client.portfolio.place_order(
            market,
            action=Action.BUY,
            side=Side.YES,
            count=1,
            yes_price=1,
        )
        order2 = client.portfolio.place_order(
            market,
            action=Action.BUY,
            side=Side.YES,
            count=1,
            yes_price=2,
        )

        try:
            # Create order group
            group = client.portfolio.create_order_group(
                order_ids=[order1.order_id, order2.order_id],
                max_loss=100,  # 100 cents = $1
            )

            assert group.order_group_id is not None
            group_id = group.order_group_id

            # Get order group
            fetched = client.portfolio.get_order_group(group_id)
            assert fetched.order_group_id == group_id

            # Update order group limit
            updated = client.portfolio.update_order_group_limit(
                group_id,
                max_loss=200,
            )
            assert updated.order_group_id == group_id

            # Reset order group
            reset = client.portfolio.reset_order_group(group_id)
            assert reset.order_group_id == group_id

            # Delete order group (does not cancel orders)
            client.portfolio.delete_order_group(group_id)

            # Verify it's gone
            groups = client.portfolio.get_order_groups()
            group_ids = [g.order_group_id for g in groups]
            assert group_id not in group_ids

        finally:
            # Cleanup - cancel the orders
            client.portfolio.batch_cancel_orders([order1.order_id, order2.order_id])


class TestOrderMutations:
    """Tests for order placement, amendment, and cancellation.

    These tests place real orders on the demo account at prices
    that won't fill (far from market), then clean up.

    Note: These tests require the exchange to be available for trading.
    They may be skipped during exchange maintenance windows.
    """

    @pytest.fixture
    def market_for_orders(self, client):
        """Get an active market suitable for placing test orders."""
        from pykalshi.exceptions import KalshiAPIError

        try:
            markets = client.get_markets(limit=10, status=MarketStatus.OPEN)
        except KalshiAPIError as e:
            if e.status_code == 503:
                pytest.skip("Exchange unavailable (503)")
            raise

        # Find one with some activity (has yes_bid or yes_ask)
        for m in markets:
            if m.data.yes_bid or m.data.yes_ask:
                return m
        # Fall back to any open market
        if markets:
            return markets[0]
        pytest.skip("No open markets available")

    def test_place_and_cancel_order(self, client, market_for_orders):
        """Place an order and cancel it."""
        market = market_for_orders

        # Place limit order at 1 cent (won't fill)
        order = client.portfolio.place_order(
            market,
            action=Action.BUY,
            side=Side.YES,
            count=1,
            yes_price=1,  # 1 cent - won't fill
        )

        assert order.order_id is not None
        assert order.ticker == market.ticker
        assert order.status == OrderStatus.RESTING

        # Cancel it
        cancelled = client.portfolio.cancel_order(order.order_id)

        assert cancelled.order_id == order.order_id
        assert cancelled.status == OrderStatus.CANCELED

    def test_order_cancel_method(self, client, market_for_orders):
        """Test Order.cancel() method."""
        market = market_for_orders

        order = client.portfolio.place_order(
            market,
            action=Action.BUY,
            side=Side.YES,
            count=1,
            yes_price=1,
        )

        assert order.order_id is not None
        assert order.status == OrderStatus.RESTING

        # Use the order's cancel method
        order.cancel()
        assert order.status == OrderStatus.CANCELED

    def test_amend_order(self, client, market_for_orders):
        """Place an order and amend its price."""
        market = market_for_orders

        # Place at 1 cent
        order = client.portfolio.place_order(
            market,
            action=Action.BUY,
            side=Side.YES,
            count=1,
            yes_price=1,
        )

        # Amend to 2 cents - pass order data to avoid re-fetch
        amended = client.portfolio.amend_order(
            order_id=order.order_id,
            count=1,
            yes_price=2,
            ticker=order.ticker,
            action=order.action,
            side=order.side,
        )

        # Verify amendment succeeded
        assert amended.order_id is not None
        assert amended.status == OrderStatus.RESTING

        # Cleanup
        client.portfolio.cancel_order(amended.order_id)

    def test_order_amend_method(self, client, market_for_orders):
        """Test Order.amend() method."""
        market = market_for_orders

        order = client.portfolio.place_order(
            market,
            action=Action.BUY,
            side=Side.YES,
            count=1,
            yes_price=1,
        )

        original_price = order.yes_price

        # Use the order's amend method
        order.amend(count=1, yes_price=2)

        # Verify amendment - price should have changed
        assert order.yes_price == 2
        assert order.yes_price != original_price
        assert order.status == OrderStatus.RESTING

        # Cleanup
        order.cancel()

    def test_decrease_order(self, client, market_for_orders):
        """Place an order and decrease its count."""
        market = market_for_orders

        # Place order for 5 contracts
        order = client.portfolio.place_order(
            market,
            action=Action.BUY,
            side=Side.YES,
            count=5,
            yes_price=1,
        )

        assert order.remaining_count == 5

        # Decrease to 2
        decreased = client.portfolio.decrease_order(
            order_id=order.order_id,
            reduce_by=3,
        )

        assert decreased.order_id == order.order_id
        assert decreased.remaining_count == 2

        # Cleanup
        client.portfolio.cancel_order(order.order_id)

    def test_order_decrease_method(self, client, market_for_orders):
        """Test Order.decrease() method."""
        market = market_for_orders

        order = client.portfolio.place_order(
            market,
            action=Action.BUY,
            side=Side.YES,
            count=5,
            yes_price=1,
        )

        # Use the order's decrease method
        order.decrease(reduce_by=2)

        assert order.remaining_count == 3

        # Cleanup
        order.cancel()

    def test_order_refresh(self, client, market_for_orders):
        """Test Order.refresh() to get latest state.

        Note: The demo API's single order lookup may return 404.
        This test verifies the refresh method works when the API is available.
        """
        from pykalshi.exceptions import ResourceNotFoundError

        market = market_for_orders

        order = client.portfolio.place_order(
            market,
            action=Action.BUY,
            side=Side.YES,
            count=1,
            yes_price=1,
        )

        # Refresh may fail on demo due to single order lookup 404
        try:
            original_status = order.status
            order.refresh()
            assert order.status == original_status
        except ResourceNotFoundError:
            # Demo API limitation - skip this assertion
            pass

        # Cleanup
        order.cancel()

    def test_batch_cancel_orders(self, client, market_for_orders):
        """Place multiple orders and batch cancel them."""
        market = market_for_orders

        # Place 3 orders
        orders = []
        for i in range(3):
            order = client.portfolio.place_order(
                market,
                action=Action.BUY,
                side=Side.YES,
                count=1,
                yes_price=1,
            )
            orders.append(order)

        order_ids = [o.order_id for o in orders]

        # Batch cancel
        result = client.portfolio.batch_cancel_orders(order_ids)

        # Result should contain cancelled orders
        assert isinstance(result, dict)
        assert "orders" in result

    def test_get_order_by_id(self, client, market_for_orders):
        """Get a specific order by ID.

        Note: The demo API sometimes returns 404 for single order lookup
        even when the order exists. This test may be skipped on demo.
        """
        from pykalshi.exceptions import ResourceNotFoundError

        market = market_for_orders

        order = client.portfolio.place_order(
            market,
            action=Action.BUY,
            side=Side.YES,
            count=1,
            yes_price=1,
        )

        # Fetch by ID - may fail on demo
        try:
            fetched = client.portfolio.get_order(order.order_id)
            assert fetched.order_id == order.order_id
            assert fetched.ticker == order.ticker
        except ResourceNotFoundError:
            # Demo API limitation - order exists but single lookup fails
            # Verify it exists in list instead
            orders = client.portfolio.get_orders(limit=10)
            order_ids = [o.order_id for o in orders]
            assert order.order_id in order_ids

        # Cleanup
        client.portfolio.cancel_order(order.order_id)

    def test_batch_place_orders(self, client, market_for_orders):
        """Place multiple orders atomically with batch_place_orders."""
        market = market_for_orders

        orders_to_place = [
            {
                "ticker": market.ticker,
                "action": "buy",
                "side": "yes",
                "count": 1,
                "type": "limit",
                "yes_price": 1,
            },
            {
                "ticker": market.ticker,
                "action": "buy",
                "side": "yes",
                "count": 1,
                "type": "limit",
                "yes_price": 2,
            },
        ]

        result = client.portfolio.batch_place_orders(orders_to_place)

        assert isinstance(result, list)
        assert len(result) == 2

        # All orders should be resting
        for order in result:
            assert order.order_id is not None
            assert order.ticker == market.ticker

        # Cleanup - batch cancel
        order_ids = [o.order_id for o in result]
        client.portfolio.batch_cancel_orders(order_ids)

    def test_get_queue_position(self, client, market_for_orders):
        """Get queue position for a resting order."""
        market = market_for_orders

        order = client.portfolio.place_order(
            market,
            action=Action.BUY,
            side=Side.YES,
            count=1,
            yes_price=1,
        )

        # Get queue position
        queue_pos = client.portfolio.get_queue_position(order.order_id)

        assert hasattr(queue_pos, "order_id")
        assert hasattr(queue_pos, "queue_position")
        assert queue_pos.order_id == order.order_id
        # Queue position should be a non-negative integer
        assert isinstance(queue_pos.queue_position, int)
        assert queue_pos.queue_position >= 0

        # Cleanup
        order.cancel()

    def test_get_queue_positions_multiple(self, client, market_for_orders):
        """Get queue positions for multiple orders."""
        market = market_for_orders

        # Place 2 orders
        orders = []
        for _ in range(2):
            order = client.portfolio.place_order(
                market,
                action=Action.BUY,
                side=Side.YES,
                count=1,
                yes_price=1,
            )
            orders.append(order)

        order_ids = [o.order_id for o in orders]

        # Get queue positions
        queue_positions = client.portfolio.get_queue_positions(order_ids)

        assert isinstance(queue_positions, list)
        assert len(queue_positions) == 2

        for qp in queue_positions:
            assert qp.order_id in order_ids
            assert isinstance(qp.queue_position, int)

        # Cleanup
        client.portfolio.batch_cancel_orders(order_ids)

    def test_order_wait_until_terminal(self, client, market_for_orders):
        """Test Order.wait_until_terminal() by cancelling an order."""
        market = market_for_orders

        order = client.portfolio.place_order(
            market,
            action=Action.BUY,
            side=Side.YES,
            count=1,
            yes_price=1,
        )

        assert order.status == OrderStatus.RESTING

        # Cancel the order
        client.portfolio.cancel_order(order.order_id)

        # Now wait for terminal state (should already be terminal)
        order.wait_until_terminal(timeout=5.0)

        assert order.status == OrderStatus.CANCELED
