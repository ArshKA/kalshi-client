from __future__ import annotations
from typing import TYPE_CHECKING
from .orders import Order
from .enums import Action, Side, OrderType
from .models import OrderModel, BalanceModel, PositionModel, FillModel

if TYPE_CHECKING:
    from .client import KalshiClient
    from .markets import Market


class User:
    """
    Represents the authenticated Kalshi user/account.
    """

    def __init__(self, client: KalshiClient) -> None:
        self.client = client

    @property
    def balance(self) -> BalanceModel:
        """
        Get portfolio balance.
        Returns BalanceModel with 'balance' and 'portfolio_value' in cents.
        """
        data = self.client.get("/portfolio/balance")
        return BalanceModel.model_validate(data)

    def place_order(
        self,
        market: Market,
        action: Action,
        side: Side,
        count: int,
        price: int,
        order_type: OrderType = OrderType.LIMIT,
    ) -> Order:
        """
        Place an order on a specific market.
        """
        order_data = {
            "ticker": market.ticker,
            "action": action.value,
            "side": side.value,
            "count": count,
            "type": order_type.value,
            "yes_price": price,
        }
        response = self.client.post("/portfolio/orders", order_data)
        data = response.get("order", response)
        # Validate logic
        model = OrderModel.model_validate(data)
        return Order(self.client, model)

    def get_orders(self, status: str | None = None) -> list[Order]:
        """
        Get list of orders.
        """
        endpoint = "/portfolio/orders"
        if status:
            endpoint += f"?status={status}"
        response = self.client.get(endpoint)
        orders_data = response.get("orders", [])
        # Validate data
        return [Order(self.client, OrderModel.model_validate(d)) for d in orders_data]

    def get_order(self, order_id: str) -> Order:
        """
        Get a single order by ID.

        Args:
            order_id: The unique order identifier.

        Returns:
            Order object for the specified order.
        """
        response = self.client.get(f"/portfolio/orders/{order_id}")
        data = response.get("order", response)
        model = OrderModel.model_validate(data)
        return Order(self.client, model)

    def get_positions(
        self,
        ticker: str | None = None,
        event_ticker: str | None = None,
        count_filter: str | None = None,
        limit: int = 100,
        cursor: str | None = None,
        fetch_all: bool = False,
    ) -> list[PositionModel]:
        """
        Get portfolio positions.

        Args:
            ticker: Filter by specific market ticker.
            event_ticker: Filter by event ticker.
            count_filter: Filter positions with non-zero values.
                         Options: "position", "total_traded", or both comma-separated.
            limit: Maximum number of positions per page (default 100, max 1000).
            cursor: Pagination cursor for fetching next page.
            fetch_all: If True, automatically fetch all pages.

        Returns:
            List of PositionModel objects representing portfolio holdings.
        """
        all_positions: list[PositionModel] = []
        current_cursor = cursor

        while True:
            params = [f"limit={limit}"]
            if ticker:
                params.append(f"ticker={ticker}")
            if event_ticker:
                params.append(f"event_ticker={event_ticker}")
            if count_filter:
                params.append(f"count_filter={count_filter}")
            if current_cursor:
                params.append(f"cursor={current_cursor}")

            endpoint = f"/portfolio/positions?{'&'.join(params)}"
            response = self.client.get(endpoint)
            positions_data = response.get("market_positions", [])

            positions = [PositionModel.model_validate(p) for p in positions_data]
            all_positions.extend(positions)

            next_cursor = response.get("cursor", "")
            if not fetch_all or not next_cursor:
                break
            current_cursor = next_cursor

        return all_positions

    def get_positions_paginated(
        self,
        ticker: str | None = None,
        event_ticker: str | None = None,
        count_filter: str | None = None,
        limit: int = 100,
        cursor: str | None = None,
    ) -> tuple[list[PositionModel], str]:
        """
        Get portfolio positions with pagination info.

        Returns:
            Tuple of (list of PositionModel, next cursor string).
        """
        params = [f"limit={limit}"]
        if ticker:
            params.append(f"ticker={ticker}")
        if event_ticker:
            params.append(f"event_ticker={event_ticker}")
        if count_filter:
            params.append(f"count_filter={count_filter}")
        if cursor:
            params.append(f"cursor={cursor}")

        endpoint = f"/portfolio/positions?{'&'.join(params)}"
        response = self.client.get(endpoint)
        positions_data = response.get("market_positions", [])
        next_cursor = response.get("cursor", "")

        positions = [PositionModel.model_validate(p) for p in positions_data]
        return positions, next_cursor

    def get_fills(
        self,
        ticker: str | None = None,
        order_id: str | None = None,
        min_ts: int | None = None,
        max_ts: int | None = None,
        limit: int = 100,
        cursor: str | None = None,
        fetch_all: bool = False,
    ) -> list[FillModel]:
        """
        Get trade fills (executed trades).

        Args:
            ticker: Filter by market ticker.
            order_id: Filter by specific order ID.
            min_ts: Minimum timestamp (Unix timestamp in seconds).
            max_ts: Maximum timestamp (Unix timestamp in seconds).
            limit: Maximum number of fills per page (default 100, max 200).
            cursor: Pagination cursor for fetching next page.
            fetch_all: If True, automatically fetch all pages.

        Returns:
            List of FillModel objects representing executed trades.
        """
        all_fills: list[FillModel] = []
        current_cursor = cursor

        while True:
            params = [f"limit={limit}"]
            if ticker:
                params.append(f"ticker={ticker}")
            if order_id:
                params.append(f"order_id={order_id}")
            if min_ts:
                params.append(f"min_ts={min_ts}")
            if max_ts:
                params.append(f"max_ts={max_ts}")
            if current_cursor:
                params.append(f"cursor={current_cursor}")

            endpoint = f"/portfolio/fills?{'&'.join(params)}"
            response = self.client.get(endpoint)
            fills_data = response.get("fills", [])

            fills = [FillModel.model_validate(f) for f in fills_data]
            all_fills.extend(fills)

            next_cursor = response.get("cursor", "")
            if not fetch_all or not next_cursor:
                break
            current_cursor = next_cursor

        return all_fills

    def get_fills_paginated(
        self,
        ticker: str | None = None,
        order_id: str | None = None,
        min_ts: int | None = None,
        max_ts: int | None = None,
        limit: int = 100,
        cursor: str | None = None,
    ) -> tuple[list[FillModel], str]:
        """
        Get trade fills with pagination info.

        Returns:
            Tuple of (list of FillModel, next cursor string).
        """
        params = [f"limit={limit}"]
        if ticker:
            params.append(f"ticker={ticker}")
        if order_id:
            params.append(f"order_id={order_id}")
        if min_ts:
            params.append(f"min_ts={min_ts}")
        if max_ts:
            params.append(f"max_ts={max_ts}")
        if cursor:
            params.append(f"cursor={cursor}")

        endpoint = f"/portfolio/fills?{'&'.join(params)}"
        response = self.client.get(endpoint)
        fills_data = response.get("fills", [])
        next_cursor = response.get("cursor", "")

        fills = [FillModel.model_validate(f) for f in fills_data]
        return fills, next_cursor

