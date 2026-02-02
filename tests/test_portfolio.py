"""Tests for portfolio functionality: positions, fills, and order retrieval."""

import pytest
from unittest.mock import ANY
from kalshi_api.enums import Action, Side, OrderStatus


def test_get_positions_workflow(client, mock_response):
    """Test fetching portfolio positions."""
    client._session.request.return_value = mock_response(
        {
            "market_positions": [
                {
                    "ticker": "KXTEST-A",
                    "event_ticker": "KXTEST",
                    "position": 10,
                    "total_traded": 25,
                    "resting_orders_count": 2,
                    "fees_paid": 50,
                    "realized_pnl": 100,
                },
                {
                    "ticker": "KXTEST-B",
                    "event_ticker": "KXTEST",
                    "position": -5,
                    "total_traded": 10,
                    "resting_orders_count": 0,
                    "fees_paid": 25,
                    "realized_pnl": -30,
                },
            ],
            "cursor": "",
        }
    )

    positions = client.portfolio.get_positions()

    # Verify results
    assert len(positions) == 2
    assert positions[0].ticker == "KXTEST-A"
    assert positions[0].position == 10
    assert positions[1].position == -5  # Short position

    # Verify endpoint called
    client._session.request.assert_called_with(
        "GET",
        "https://demo-api.elections.kalshi.com/trade-api/v2/portfolio/positions?limit=100",
        headers=ANY,
        timeout=ANY,
    )


def test_get_positions_with_filters(client, mock_response):
    """Test fetching positions with filters."""
    client._session.request.return_value = mock_response(
        {"market_positions": [], "cursor": ""}
    )

    client.portfolio.get_positions(
        ticker="KXTEST-A", event_ticker="KXTEST", count_filter="position", limit=50
    )

    # Verify all filters passed in URL
    call_url = client._session.request.call_args.args[1]
    assert "ticker=KXTEST-A" in call_url
    assert "event_ticker=KXTEST" in call_url
    assert "count_filter=position" in call_url
    assert "limit=50" in call_url


def test_get_fills_workflow(client, mock_response):
    """Test fetching trade fills."""
    client._session.request.return_value = mock_response(
        {
            "fills": [
                {
                    "trade_id": "trade-001",
                    "ticker": "KXTEST",
                    "order_id": "order-123",
                    "side": "yes",
                    "action": "buy",
                    "count": 5,
                    "yes_price": 50,
                    "no_price": 50,
                    "created_time": "2024-01-01T12:00:00Z",
                    "is_taker": True,
                },
                {
                    "trade_id": "trade-002",
                    "ticker": "KXTEST",
                    "order_id": "order-124",
                    "side": "no",
                    "action": "sell",
                    "count": 3,
                    "yes_price": 45,
                    "no_price": 55,
                    "created_time": "2024-01-01T13:00:00Z",
                    "is_taker": False,
                },
            ],
            "cursor": "",
        }
    )

    fills = client.portfolio.get_fills()

    # Verify results
    assert len(fills) == 2
    assert fills[0].trade_id == "trade-001"
    assert fills[0].action == Action.BUY
    assert fills[0].side == Side.YES
    assert fills[0].count == 5
    assert fills[0].is_taker == True

    assert fills[1].action == Action.SELL
    assert fills[1].side == Side.NO

    # Verify endpoint called
    client._session.request.assert_called_with(
        "GET",
        "https://demo-api.elections.kalshi.com/trade-api/v2/portfolio/fills?limit=100",
        headers=ANY,
        timeout=ANY,
    )


def test_get_fills_with_filters(client, mock_response):
    """Test fetching fills with filters."""
    client._session.request.return_value = mock_response(
        {"fills": [], "cursor": ""}
    )

    client.portfolio.get_fills(
        ticker="KXTEST",
        order_id="order-123",
        min_ts=1700000000,
        max_ts=1700100000,
        limit=25,
    )

    # Verify all filters in URL
    call_url = client._session.request.call_args.args[1]
    assert "ticker=KXTEST" in call_url
    assert "order_id=order-123" in call_url
    assert "min_ts=1700000000" in call_url
    assert "max_ts=1700100000" in call_url
    assert "limit=25" in call_url


def test_get_order_by_id(client, mock_response):
    """Test fetching a single order by ID."""
    client._session.request.return_value = mock_response(
        {
            "order": {
                "order_id": "order-abc-123",
                "ticker": "KXTEST",
                "action": "buy",
                "side": "yes",
                "count": 10,
                "yes_price": 55,
                "status": "resting",
                "type": "limit",
            }
        }
    )

    order = client.portfolio.get_order("order-abc-123")

    # Verify order data
    assert order.order_id == "order-abc-123"
    assert order.ticker == "KXTEST"
    assert order.status == OrderStatus.RESTING

    # Verify correct endpoint called
    client._session.request.assert_called_with(
        "GET",
        "https://demo-api.elections.kalshi.com/trade-api/v2/portfolio/orders/order-abc-123",
        headers=ANY,
        timeout=ANY,
    )


def test_get_order_not_found(client, mock_response):
    """Test that 404 raises ResourceNotFoundError."""
    from kalshi_api.exceptions import ResourceNotFoundError

    client._session.request.return_value = mock_response(
        {"message": "Order not found", "code": "not_found"}, status_code=404
    )

    with pytest.raises(ResourceNotFoundError):
        client.portfolio.get_order("nonexistent-order")


def test_cancel_order(client, mock_response):
    """Test canceling an order by ID."""
    client._session.request.return_value = mock_response(
        {
            "order": {
                "order_id": "order-abc-123",
                "ticker": "KXTEST",
                "action": "buy",
                "side": "yes",
                "count": 10,
                "yes_price": 55,
                "status": "canceled",
                "type": "limit",
            }
        }
    )

    order = client.portfolio.cancel_order("order-abc-123")

    assert order.order_id == "order-abc-123"
    assert order.status == OrderStatus.CANCELED

    # Verify DELETE request
    client._session.request.assert_called_with(
        "DELETE",
        "https://demo-api.elections.kalshi.com/trade-api/v2/portfolio/orders/order-abc-123",
        headers=ANY,
        timeout=ANY,
    )


def test_order_cancel_delegates_to_portfolio(client, mock_response):
    """Test that Order.cancel() delegates to Portfolio.cancel_order()."""
    from kalshi_api.orders import Order
    from kalshi_api.models import OrderModel

    # Initial order state
    initial_model = OrderModel(
        order_id="order-abc-123",
        ticker="KXTEST",
        status=OrderStatus.RESTING,
    )
    order = Order(client, initial_model)

    # Mock the cancel response
    client._session.request.return_value = mock_response(
        {
            "order": {
                "order_id": "order-abc-123",
                "ticker": "KXTEST",
                "status": "canceled",
            }
        }
    )

    result = order.cancel()

    # Should return self
    assert result is order
    # Should update internal data
    assert order.status == OrderStatus.CANCELED


def test_order_amend(client, mock_response):
    """Test Order.amend() method."""
    from kalshi_api.orders import Order
    from kalshi_api.models import OrderModel

    initial_model = OrderModel(
        order_id="order-abc-123",
        ticker="KXTEST",
        status=OrderStatus.RESTING,
        yes_price=50,
    )
    order = Order(client, initial_model)

    client._session.request.return_value = mock_response(
        {
            "order": {
                "order_id": "order-abc-123",
                "ticker": "KXTEST",
                "status": "resting",
                "yes_price": 55,
            }
        }
    )

    result = order.amend(yes_price=55)

    assert result is order
    assert order.yes_price == 55

    # Verify POST to amend endpoint
    call_args = client._session.request.call_args
    assert call_args.args[0] == "POST"
    assert "/portfolio/orders/order-abc-123/amend" in call_args.args[1]


def test_order_decrease(client, mock_response):
    """Test Order.decrease() method."""
    from kalshi_api.orders import Order
    from kalshi_api.models import OrderModel

    initial_model = OrderModel(
        order_id="order-abc-123",
        ticker="KXTEST",
        status=OrderStatus.RESTING,
        remaining_count=10,
    )
    order = Order(client, initial_model)

    client._session.request.return_value = mock_response(
        {
            "order": {
                "order_id": "order-abc-123",
                "ticker": "KXTEST",
                "status": "resting",
                "remaining_count": 7,
            }
        }
    )

    result = order.decrease(reduce_by=3)

    assert result is order
    assert order.remaining_count == 7

    # Verify POST to decrease endpoint
    call_args = client._session.request.call_args
    assert call_args.args[0] == "POST"
    assert "/portfolio/orders/order-abc-123/decrease" in call_args.args[1]


def test_order_refresh(client, mock_response):
    """Test Order.refresh() method."""
    from kalshi_api.orders import Order
    from kalshi_api.models import OrderModel

    initial_model = OrderModel(
        order_id="order-abc-123",
        ticker="KXTEST",
        status=OrderStatus.RESTING,
        fill_count=0,
    )
    order = Order(client, initial_model)

    # Simulate order getting partially filled
    client._session.request.return_value = mock_response(
        {
            "order": {
                "order_id": "order-abc-123",
                "ticker": "KXTEST",
                "status": "resting",
                "fill_count": 5,
            }
        }
    )

    result = order.refresh()

    assert result is order
    assert order.fill_count == 5

    # Verify GET to order endpoint
    client._session.request.assert_called_with(
        "GET",
        "https://demo-api.elections.kalshi.com/trade-api/v2/portfolio/orders/order-abc-123",
        headers=ANY,
        timeout=ANY,
    )
