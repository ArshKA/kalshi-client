import pytest
from kalshi_api.models import BalanceModel, OrderModel, MarketModel, FillModel
from kalshi_api.enums import Action, Side, OrderStatus


def test_balance_model_validation():
    data = {"balance": 1000, "portfolio_value": 2000}
    model = BalanceModel.model_validate(data)
    assert model.balance == 1000
    assert model.portfolio_value == 2000


def test_order_model_parsing():
    data = {
        "order_id": "123",
        "ticker": "TEST",
        "action": "buy",
        "side": "yes",
        "count": 10,
        "price": 50,
        "status": "resting",
        "created_time": "2023-01-01T00:00:00Z",
    }
    model = OrderModel.model_validate(data)
    # Check enum conversion
    assert model.action == Action.BUY
    assert model.side == Side.YES
    assert model.status == OrderStatus.RESTING


def test_market_model_validation():
    data = {
        "ticker": "TEST-1",
        "title": "Will it rain?",
        "status": "open",
        "yes_bid": 10,
        "yes_ask": 12,
        "expiration_time": "2023-12-31T23:59:59Z",
    }
    model = MarketModel.model_validate(data)
    assert model.ticker == "TEST-1"
    assert model.yes_bid == 10


def test_invalid_data_raises_error():
    with pytest.raises(ValueError):
        BalanceModel.model_validate({"balance": "not_an_int"})


def test_fill_model_fee_cost_is_dollar_string():
    """Verify fee_cost is kept as dollar amount string."""
    data = {
        "trade_id": "t1",
        "ticker": "TEST",
        "order_id": "o1",
        "side": "yes",
        "action": "buy",
        "count": 1,
        "yes_price": 50,
        "no_price": 50,
        "fee_cost": "0.3200",
    }
    model = FillModel.model_validate(data)
    assert model.fee_cost == "0.3200"
    assert isinstance(model.fee_cost, str)
