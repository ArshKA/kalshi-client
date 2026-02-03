import pytest
import json
from unittest.mock import ANY
from kalshi_api.enums import Action, Side, OrderType, OrderStatus


def test_user_balance_workflow(client, mock_response):
    """Test fetching user balance."""
    client._session.request.return_value = mock_response(
        {"balance": 5000, "portfolio_value": 10000}
    )

    balance = client.portfolio.get_balance()

    # Verify values
    assert balance.balance == 5000
    assert balance.portfolio_value == 10000

    # Verify endpoint called
    client._session.request.assert_called_with(
        "GET",
        "https://demo-api.elections.kalshi.com/trade-api/v2/portfolio/balance",
        headers=ANY,
        timeout=ANY,
    )


def test_place_order_workflow(client, mock_response, mocker):
    """Test placing an order via Portfolio object."""
    client._session.request.return_value = mock_response(
        {
            "order": {
                "order_id": "bfs-123",
                "ticker": "KXTEST",
                "action": "buy",
                "side": "yes",
                "count": 5,
                "price": 50,
                "status": "resting",
                "created_time": "2023-01-01T00:00:00Z",
            }
        }
    )

    # Mock Market object (just need ticker)
    market = mocker.MagicMock()
    market.ticker = "KXTEST"

    order = client.portfolio.place_order(
        market, action=Action.BUY, side=Side.YES, count=5, yes_price=50
    )

    # Verify Order object returned
    assert order.order_id == "bfs-123"
    assert order.status == OrderStatus.RESTING

    # Verify correct payload sent
    call_args = client._session.request.call_args
    assert call_args.args[0] == "POST"
    assert "/portfolio/orders" in call_args.args[1]
    body = json.loads(call_args.kwargs["data"])
    assert body["ticker"] == "KXTEST"
    assert body["action"] == "buy"
    assert body["side"] == "yes"
    assert body["count"] == 5
    assert body["yes_price"] == 50


def test_market_orderbook_workflow(client, mock_response):
    """Test fetching orderbook via Market object."""
    client._session.request.side_effect = [
        # Call 1: Market data
        mock_response(
            {
                "market": {
                    "ticker": "KXTEST",
                    "title": "Test Market",
                    "status": "open",
                    "yes_bid": 10,
                    "yes_ask": 12,
                    "expiration_time": "2024-01-01T00:00:00Z",
                }
            }
        ),
        # Call 2: Orderbook data
        mock_response({"orderbook": {"yes": [[10, 50]], "no": [[90, 50]]}}),
    ]

    # 1. Fetch market
    market = client.get_market("KXTEST")

    # 2. Fetch orderbook
    ob = market.get_orderbook()

    # Verify typed OrderbookResponse
    assert ob.orderbook.yes == [(10, 50)]
    assert ob.best_yes_bid == 10
    assert client._session.request.call_count == 2

    # Verify URL of second call
    call_args_list = client._session.request.call_args_list
    assert "/markets/KXTEST/orderbook" in call_args_list[1].args[1]
