from __future__ import annotations
from typing import TYPE_CHECKING
from urllib.parse import urlencode
from .orders import Order, AsyncOrder
from .enums import Action, Side, OrderType, OrderStatus, TimeInForce, SelfTradePrevention, PositionCountFilter
from .dataframe import DataFrameList
from ._utils import normalize_ticker, normalize_tickers
from .models import (
    OrderModel, BalanceModel, PositionModel, FillModel,
    SettlementModel, QueuePositionModel, OrderGroupModel,
    SubaccountModel, SubaccountBalanceModel, SubaccountTransferModel,
)

if TYPE_CHECKING:
    from .client import KalshiClient
    from .markets import Market


class Portfolio:
    """Authenticated user's portfolio and trading operations."""

    def __init__(self, client: KalshiClient) -> None:
        self._client = client

    def get_balance(self) -> BalanceModel:
        """Get portfolio balance. Values are in cents."""
        data = self._client.get("/portfolio/balance")
        return BalanceModel.model_validate(data)

    def place_order(
        self,
        ticker: str | Market,
        action: Action,
        side: Side,
        count: int,
        order_type: OrderType = OrderType.LIMIT,
        *,
        yes_price: int | None = None,
        no_price: int | None = None,
        client_order_id: str | None = None,
        time_in_force: TimeInForce | None = None,
        post_only: bool = False,
        reduce_only: bool = False,
        expiration_ts: int | None = None,
        buy_max_cost: int | None = None,
        self_trade_prevention: SelfTradePrevention | None = None,
        order_group_id: str | None = None,
        subaccount: int | None = None,
        cancel_order_on_pause: bool | None = None,
    ) -> Order:
        """Place an order on a market.

        Args:
            ticker: Market ticker string or Market object.
            action: BUY or SELL.
            side: YES or NO.
            count: Number of contracts.
            order_type: LIMIT or MARKET.
            yes_price: Price in cents (1-99) for the YES side.
            no_price: Price in cents (1-99) for the NO side.
                      Converted to yes_price internally (yes_price = 100 - no_price).
            client_order_id: Idempotency key. Resubmitting returns existing order.
            time_in_force: GTC (default), IOC (immediate-or-cancel), FOK (fill-or-kill).
            post_only: If True, reject order if it would take liquidity. Essential for market makers.
            reduce_only: If True, only reduce existing position, never increase.
            expiration_ts: Unix timestamp when order auto-cancels.
            buy_max_cost: Maximum total cost in cents. Protects against slippage.
            self_trade_prevention: Behavior on self-cross (CANCEL_RESTING or CANCEL_INCOMING).
            order_group_id: Link to an order group for OCO/bracket strategies.
            subaccount: Subaccount number (0 for primary, 1-32 for subaccounts).
            cancel_order_on_pause: If True, cancel order if market is paused.
        """
        order_data = self._build_order_data(
            ticker, action, side, count, order_type,
            yes_price=yes_price, no_price=no_price,
            client_order_id=client_order_id, time_in_force=time_in_force,
            post_only=post_only, reduce_only=reduce_only,
            expiration_ts=expiration_ts, buy_max_cost=buy_max_cost,
            self_trade_prevention=self_trade_prevention,
            order_group_id=order_group_id, subaccount=subaccount,
            cancel_order_on_pause=cancel_order_on_pause,
        )
        response = self._client.post("/portfolio/orders", order_data)
        model = OrderModel.model_validate(response["order"])
        return Order(self._client, model)

    def cancel_order(self, order_id: str, *, subaccount: int | None = None) -> Order:
        """Cancel a resting order.

        Args:
            order_id: ID of the order to cancel.
            subaccount: Subaccount number (0 for primary, 1-32 for subaccounts).

        Returns:
            The canceled Order with updated status.
        """
        endpoint = f"/portfolio/orders/{order_id}"
        if subaccount is not None:
            endpoint += f"?subaccount={subaccount}"
        response = self._client.delete(endpoint)
        model = OrderModel.model_validate(response["order"])
        return Order(self._client, model)

    def amend_order(
        self,
        order_id: str,
        *,
        count: int | None = None,
        yes_price: int | None = None,
        no_price: int | None = None,
        subaccount: int | None = None,
        # Required by API but can be fetched from existing order
        ticker: str | None = None,
        action: Action | None = None,
        side: Side | None = None,
    ) -> Order:
        """Amend a resting order's price or count.

        Args:
            order_id: ID of the order to amend.
            count: New total contract count.
            yes_price: New YES price in cents.
            no_price: New NO price in cents. Converted to yes_price internally.
            subaccount: Subaccount number (0 for primary, 1-32 for subaccounts).
            ticker: Market ticker (fetched from order if not provided).
            action: Order action (fetched from order if not provided).
            side: Order side (fetched from order if not provided).
        """
        if yes_price is not None and no_price is not None:
            raise ValueError("Specify yes_price or no_price, not both")

        if no_price is not None:
            yes_price = 100 - no_price

        ticker = normalize_ticker(ticker)

        # Fetch original order to get required fields if not provided
        if ticker is None or action is None or side is None or count is None:
            original = self.get_order(order_id)
            ticker = ticker or original.ticker
            action = action or original.action
            side = side or original.side
            if count is None:
                count = original.remaining_count

        body: dict = {
            "ticker": ticker,
            "action": action.value if isinstance(action, Action) else action,
            "side": side.value if isinstance(side, Side) else side,
            "count": count,
        }
        if yes_price is not None:
            body["yes_price"] = yes_price
        if subaccount is not None:
            body["subaccount"] = subaccount

        if "count" not in body and "yes_price" not in body:
            raise ValueError("Must specify at least one of count, yes_price, or no_price")

        response = self._client.post(f"/portfolio/orders/{order_id}/amend", body)
        model = OrderModel.model_validate(response["order"])
        return Order(self._client, model)

    def decrease_order(self, order_id: str, reduce_by: int) -> Order:
        """Decrease the remaining count of a resting order.

        Args:
            order_id: ID of the order to decrease.
            reduce_by: Number of contracts to reduce by.
        """
        response = self._client.post(
            f"/portfolio/orders/{order_id}/decrease", {"reduce_by": reduce_by}
        )
        model = OrderModel.model_validate(response["order"])
        return Order(self._client, model)

    def get_orders(
        self,
        *,
        status: OrderStatus | None = None,
        ticker: str | None = None,
        event_ticker: str | None = None,
        min_ts: int | None = None,
        max_ts: int | None = None,
        limit: int = 100,
        cursor: str | None = None,
        fetch_all: bool = False,
        **extra_params,
    ) -> DataFrameList[Order]:
        """Get list of orders.

        Args:
            status: Filter by order status (resting, canceled, executed).
            ticker: Filter by market ticker.
            event_ticker: Filter by event ticker (supports comma-separated, max 10).
            min_ts: Filter orders after this Unix timestamp.
            max_ts: Filter orders before this Unix timestamp.
            limit: Maximum results per page (default 100, max 200).
            cursor: Pagination cursor for fetching next page.
            fetch_all: If True, automatically fetch all pages.
            **extra_params: Additional API parameters (e.g., subaccount).
                           See https://docs.kalshi.com/api-reference/orders/get-orders
        """
        params = {
            "limit": limit,
            "status": status.value if status is not None else None,
            "ticker": normalize_ticker(ticker),
            "event_ticker": normalize_ticker(event_ticker),
            "min_ts": min_ts,
            "max_ts": max_ts,
            "cursor": cursor,
            **extra_params,
        }
        data = self._client.paginated_get("/portfolio/orders", "orders", params, fetch_all)
        return DataFrameList(Order(self._client, OrderModel.model_validate(d)) for d in data)

    def get_order(self, order_id: str) -> Order:
        """Get a single order by ID."""
        response = self._client.get(f"/portfolio/orders/{order_id}")
        model = OrderModel.model_validate(response["order"])
        return Order(self._client, model)

    def get_positions(
        self,
        *,
        ticker: str | None = None,
        event_ticker: str | None = None,
        count_filter: PositionCountFilter | None = None,
        limit: int = 100,
        cursor: str | None = None,
        fetch_all: bool = False,
        **extra_params,
    ) -> DataFrameList[PositionModel]:
        """Get portfolio positions.

        Args:
            ticker: Filter by specific market ticker.
            event_ticker: Filter by event ticker (supports comma-separated, max 10).
            count_filter: Filter positions with non-zero values (POSITION or TOTAL_TRADED).
            limit: Maximum positions per page (default 100, max 1000).
            cursor: Pagination cursor for fetching next page.
            fetch_all: If True, automatically fetch all pages.
            **extra_params: Additional API parameters (e.g., subaccount).
        """
        params = {
            "limit": limit,
            "ticker": normalize_ticker(ticker),
            "event_ticker": normalize_ticker(event_ticker),
            "count_filter": count_filter.value if count_filter is not None else None,
            "cursor": cursor,
            **extra_params,
        }
        data = self._client.paginated_get("/portfolio/positions", "market_positions", params, fetch_all)
        return DataFrameList(PositionModel.model_validate(p) for p in data)

    def get_fills(
        self,
        *,
        ticker: str | None = None,
        order_id: str | None = None,
        min_ts: int | None = None,
        max_ts: int | None = None,
        limit: int = 100,
        cursor: str | None = None,
        fetch_all: bool = False,
        **extra_params,
    ) -> DataFrameList[FillModel]:
        """Get trade fills (executed trades).

        Args:
            ticker: Filter by market ticker.
            order_id: Filter by specific order ID.
            min_ts: Minimum timestamp (Unix seconds).
            max_ts: Maximum timestamp (Unix seconds).
            limit: Maximum fills per page (default 100, max 200).
            cursor: Pagination cursor for fetching next page.
            fetch_all: If True, automatically fetch all pages.
            **extra_params: Additional API parameters (e.g., subaccount).
        """
        params = {
            "limit": limit,
            "ticker": normalize_ticker(ticker),
            "order_id": order_id,
            "min_ts": min_ts,
            "max_ts": max_ts,
            "cursor": cursor,
            **extra_params,
        }
        data = self._client.paginated_get("/portfolio/fills", "fills", params, fetch_all)
        return DataFrameList(FillModel.model_validate(f) for f in data)

    # --- Batch Operations ---

    def batch_place_orders(self, orders: list[dict]) -> DataFrameList[Order]:
        """Place multiple orders atomically.

        Args:
            orders: List of order dicts with keys: ticker, action, side, count,
                    type, yes_price/no_price, and optional advanced params.

        Example:
            orders = [
                {"ticker": "KXBTC", "action": "buy", "side": "yes", "count": 10, "type": "limit", "yes_price": 45},
                {"ticker": "KXBTC", "action": "buy", "side": "no", "count": 10, "type": "limit", "no_price": 45},
            ]
            results = portfolio.batch_place_orders(orders)
        """
        prepared = self._build_batch_orders(orders)
        response = self._client.post("/portfolio/orders/batched", {"orders": prepared})
        result = []
        for item in response.get("orders", []):
            order_data = item.get("order")
            if order_data is None:
                continue
            result.append(Order(self._client, OrderModel.model_validate(order_data)))
        return DataFrameList(result)

    def batch_cancel_orders(self, order_ids: list[str]) -> DataFrameList[Order]:
        """Cancel multiple orders atomically.

        Args:
            order_ids: List of order IDs to cancel (max 20).

        Returns:
            The canceled Orders with updated status.
        """
        orders = [{"order_id": oid} for oid in order_ids]
        response = self._client.delete("/portfolio/orders/batched", {"orders": orders})
        result = []
        for item in response.get("orders", []):
            order_data = item.get("order")
            if order_data is None:
                continue
            result.append(Order(self._client, OrderModel.model_validate(order_data)))
        return DataFrameList(result)

    # --- Queue Position ---

    def get_queue_position(self, order_id: str) -> QueuePositionModel:
        """Get queue position for a single resting order.

        Returns 0-indexed position in the queue at the order's price level.
        Position 0 means you're first in line to be filled.
        """
        response = self._client.get(f"/portfolio/orders/{order_id}/queue_position")
        return QueuePositionModel(
            order_id=order_id,
            queue_position=response.get("queue_position", 0)
        )

    def get_queue_positions(
        self,
        *,
        market_tickers: list[str] | None = None,
        event_ticker: str | None = None,
    ) -> DataFrameList[QueuePositionModel]:
        """Get queue positions for all resting orders.

        Queue position represents the number of contracts that need to be
        matched before an order receives a partial or full match.

        Args:
            market_tickers: Filter by market tickers (optional).
            event_ticker: Filter by event ticker (optional).
        """
        params: dict = {}
        if market_tickers:
            params["market_tickers"] = ",".join(normalize_tickers(market_tickers))
        if event_ticker:
            params["event_ticker"] = normalize_ticker(event_ticker)

        endpoint = "/portfolio/orders/queue_positions"
        if params:
            endpoint = f"{endpoint}?{urlencode(params)}"

        response = self._client.get(endpoint)
        return DataFrameList(
            QueuePositionModel.model_validate(qp)
            for qp in response.get("queue_positions", [])
        )

    # --- Settlements ---

    def get_settlements(
        self,
        *,
        ticker: str | None = None,
        event_ticker: str | None = None,
        limit: int = 100,
        cursor: str | None = None,
        fetch_all: bool = False,
        **extra_params,
    ) -> DataFrameList[SettlementModel]:
        """Get settlement records for resolved positions.

        Args:
            ticker: Filter by market ticker.
            event_ticker: Filter by event ticker.
            limit: Maximum settlements per page (default 100).
            cursor: Pagination cursor.
            fetch_all: If True, automatically fetch all pages.
            **extra_params: Additional API parameters.
        """
        params = {
            "limit": limit,
            "ticker": normalize_ticker(ticker),
            "event_ticker": normalize_ticker(event_ticker),
            "cursor": cursor,
            **extra_params,
        }
        data = self._client.paginated_get("/portfolio/settlements", "settlements", params, fetch_all)
        return DataFrameList(SettlementModel.model_validate(s) for s in data)

    def get_resting_order_value(self) -> int:
        """Get total value of all resting orders in cents.

        NOTE: This endpoint is FCM-only (institutional accounts).
        Regular users will get a 403 Forbidden error.
        """
        response = self._client.get("/portfolio/summary/total_resting_order_value")
        return response.get("total_resting_order_value", 0)

    # --- Order Groups (Contract Rate Limiting) ---

    def create_order_group(
        self,
        contracts_limit: int,
    ) -> OrderGroupModel:
        """Create an order group for rate-limiting contract matches.

        Order groups limit total contracts matched across all orders in the group
        over a rolling 15-second window. When the limit is hit, all orders in the
        group are cancelled.

        To add orders to a group, pass `order_group_id` when calling `place_order`.

        Args:
            contracts_limit: Maximum contracts that can be matched in a rolling
                15-second window. When hit, all orders in the group are cancelled.

        Returns:
            Created OrderGroupModel.
        """
        body: dict = {"contracts_limit": contracts_limit}
        response = self._client.post("/portfolio/order_groups/create", body)
        return OrderGroupModel.model_validate(response)

    def get_order_group(self, order_group_id: str) -> OrderGroupModel:
        """Get an order group by ID.

        Returns order group details including list of order IDs in the group.
        """
        response = self._client.get(f"/portfolio/order_groups/{order_group_id}")
        response["id"] = order_group_id
        return OrderGroupModel.model_validate(response)

    def trigger_order_group(self, order_group_id: str) -> None:
        """Manually trigger an order group, cancelling all orders in it."""
        self._client.put(f"/portfolio/order_groups/{order_group_id}/trigger", {})

    def get_order_groups(self) -> DataFrameList[OrderGroupModel]:
        """List all order groups."""
        response = self._client.get("/portfolio/order_groups")
        return DataFrameList(
            OrderGroupModel.model_validate(og)
            for og in response.get("order_groups", [])
        )

    def reset_order_group(self, order_group_id: str) -> None:
        """Reset matched contract counter for an order group.

        Use this to re-enable the group after it has been triggered,
        allowing orders to continue matching up to the contracts_limit again.
        """
        self._client.put(f"/portfolio/order_groups/{order_group_id}/reset", {})

    def update_order_group_limit(
        self,
        order_group_id: str,
        contracts_limit: int,
    ) -> None:
        """Update the contracts limit for an order group.

        If the new limit would immediately trigger the group (because current
        matched contracts exceed it), all orders are cancelled and the group
        is triggered.

        Args:
            order_group_id: ID of the order group.
            contracts_limit: New maximum contracts for 15-second rolling window.
        """
        body: dict = {"contracts_limit": contracts_limit}
        self._client.put(f"/portfolio/order_groups/{order_group_id}/limit", body)

    # --- Subaccounts ---

    def create_subaccount(self) -> SubaccountModel:
        """Create a new numbered subaccount.

        Subaccounts allow strategy isolation - run multiple bots
        with separate capital pools under one API key.

        Returns:
            Created SubaccountModel with ID and number.
        """
        response = self._client.post("/portfolio/subaccounts", {})
        return SubaccountModel.model_validate(response.get("subaccount", response))

    def transfer_between_subaccounts(
        self,
        from_subaccount_id: str,
        to_subaccount_id: str,
        amount: int,
    ) -> SubaccountTransferModel:
        """Transfer funds between subaccounts.

        Args:
            from_subaccount_id: Source subaccount ID.
            to_subaccount_id: Destination subaccount ID.
            amount: Amount to transfer in cents.

        Returns:
            Transfer record.
        """
        body = {
            "from_subaccount_id": from_subaccount_id,
            "to_subaccount_id": to_subaccount_id,
            "amount": amount,
        }
        response = self._client.post("/portfolio/subaccounts/transfer", body)
        return SubaccountTransferModel.model_validate(response.get("transfer", response))

    def get_subaccount_balances(self) -> DataFrameList[SubaccountBalanceModel]:
        """Get balances for all subaccounts."""
        response = self._client.get("/portfolio/subaccounts/balances")
        return DataFrameList(
            SubaccountBalanceModel.model_validate(b)
            for b in response.get("balances", [])
        )

    def get_subaccount_transfers(
        self,
        *,
        limit: int = 100,
        cursor: str | None = None,
        fetch_all: bool = False,
        **extra_params,
    ) -> DataFrameList[SubaccountTransferModel]:
        """Get transfer history between subaccounts.

        Args:
            limit: Maximum results per page (default 100).
            cursor: Pagination cursor for fetching next page.
            fetch_all: If True, automatically fetch all pages.
            **extra_params: Additional API parameters.
        """
        params = {"limit": limit, "cursor": cursor, **extra_params}
        data = self._client.paginated_get(
            "/portfolio/subaccounts/transfers", "transfers", params, fetch_all
        )
        return DataFrameList(SubaccountTransferModel.model_validate(t) for t in data)

    # --- Shared validation helpers ---

    @staticmethod
    def _build_order_data(
        ticker,
        action: Action,
        side: Side,
        count: int,
        order_type: OrderType = OrderType.LIMIT,
        *,
        yes_price=None,
        no_price=None,
        client_order_id=None,
        time_in_force=None,
        post_only=False,
        reduce_only=False,
        expiration_ts=None,
        buy_max_cost=None,
        self_trade_prevention=None,
        order_group_id=None,
        subaccount=None,
        cancel_order_on_pause=None,
    ) -> dict:
        """Build and validate order data dict. No I/O."""
        if yes_price is not None and no_price is not None:
            raise ValueError("Specify yes_price or no_price, not both")
        if yes_price is None and no_price is None and order_type == OrderType.LIMIT:
            raise ValueError("Limit orders require yes_price or no_price")
        if no_price is not None:
            yes_price = 100 - no_price

        ticker_str = ticker.upper() if isinstance(ticker, str) else ticker.ticker

        order_data: dict = {
            "ticker": ticker_str,
            "action": action.value,
            "side": side.value,
            "count": count,
            "type": order_type.value,
        }
        if yes_price is not None:
            order_data["yes_price"] = yes_price
        if client_order_id is not None:
            order_data["client_order_id"] = client_order_id
        if time_in_force is not None:
            order_data["time_in_force"] = time_in_force.value
        if post_only:
            order_data["post_only"] = True
        if reduce_only:
            order_data["reduce_only"] = True
        if expiration_ts is not None:
            order_data["expiration_ts"] = expiration_ts
        if buy_max_cost is not None:
            order_data["buy_max_cost"] = buy_max_cost
        if self_trade_prevention is not None:
            order_data["self_trade_prevention_type"] = self_trade_prevention.value
        if order_group_id is not None:
            order_data["order_group_id"] = order_group_id
        if subaccount is not None:
            order_data["subaccount"] = subaccount
        if cancel_order_on_pause is not None:
            order_data["cancel_order_on_pause"] = cancel_order_on_pause
        return order_data

    @staticmethod
    def _build_batch_orders(orders: list[dict]) -> list[dict]:
        """Validate and prepare batch orders. No I/O."""
        prepared = []
        for order in orders:
            o = dict(order)
            if "yes_price" in o and "no_price" in o:
                raise ValueError("Specify yes_price or no_price, not both")
            if o.get("type", "limit") == "limit" and "yes_price" not in o and "no_price" not in o:
                raise ValueError("Limit orders require yes_price or no_price")
            if "no_price" in o:
                o["yes_price"] = 100 - o.pop("no_price")
            prepared.append(o)
        return prepared


class AsyncPortfolio(Portfolio):
    """Async variant of Portfolio. Inherits validation helpers."""

    async def get_balance(self) -> BalanceModel:  # type: ignore[override]
        data = await self._client.get("/portfolio/balance")
        return BalanceModel.model_validate(data)

    async def place_order(  # type: ignore[override]
        self,
        ticker,
        action: Action,
        side: Side,
        count: int,
        order_type: OrderType = OrderType.LIMIT,
        **kwargs,
    ) -> AsyncOrder:
        order_data = self._build_order_data(
            ticker, action, side, count, order_type, **kwargs
        )
        response = await self._client.post("/portfolio/orders", order_data)
        model = OrderModel.model_validate(response["order"])
        return AsyncOrder(self._client, model)

    async def cancel_order(self, order_id: str, *, subaccount: int | None = None) -> AsyncOrder:  # type: ignore[override]
        endpoint = f"/portfolio/orders/{order_id}"
        if subaccount is not None:
            endpoint += f"?subaccount={subaccount}"
        response = await self._client.delete(endpoint)
        model = OrderModel.model_validate(response["order"])
        return AsyncOrder(self._client, model)

    async def amend_order(  # type: ignore[override]
        self,
        order_id: str,
        *,
        count: int | None = None,
        yes_price: int | None = None,
        no_price: int | None = None,
        subaccount: int | None = None,
        ticker: str | None = None,
        action: Action | None = None,
        side: Side | None = None,
    ) -> AsyncOrder:
        if yes_price is not None and no_price is not None:
            raise ValueError("Specify yes_price or no_price, not both")
        if no_price is not None:
            yes_price = 100 - no_price
        ticker = normalize_ticker(ticker)

        if ticker is None or action is None or side is None or count is None:
            original = await self.get_order(order_id)
            ticker = ticker or original.ticker
            action = action or original.action
            side = side or original.side
            if count is None:
                count = original.remaining_count

        body: dict = {
            "ticker": ticker,
            "action": action.value if isinstance(action, Action) else action,
            "side": side.value if isinstance(side, Side) else side,
            "count": count,
        }
        if yes_price is not None:
            body["yes_price"] = yes_price
        if subaccount is not None:
            body["subaccount"] = subaccount
        if "count" not in body and "yes_price" not in body:
            raise ValueError("Must specify at least one of count, yes_price, or no_price")

        response = await self._client.post(f"/portfolio/orders/{order_id}/amend", body)
        model = OrderModel.model_validate(response["order"])
        return AsyncOrder(self._client, model)

    async def decrease_order(self, order_id: str, reduce_by: int) -> AsyncOrder:  # type: ignore[override]
        response = await self._client.post(
            f"/portfolio/orders/{order_id}/decrease", {"reduce_by": reduce_by}
        )
        model = OrderModel.model_validate(response["order"])
        return AsyncOrder(self._client, model)

    async def get_orders(self, *, status=None, ticker=None, event_ticker=None,  # type: ignore[override]
                         min_ts=None, max_ts=None, limit=100, cursor=None,
                         fetch_all=False, **extra_params) -> DataFrameList[AsyncOrder]:
        params = {
            "limit": limit,
            "status": status.value if status is not None else None,
            "ticker": normalize_ticker(ticker),
            "event_ticker": normalize_ticker(event_ticker),
            "min_ts": min_ts, "max_ts": max_ts, "cursor": cursor,
            **extra_params,
        }
        data = await self._client.paginated_get("/portfolio/orders", "orders", params, fetch_all)
        return DataFrameList(AsyncOrder(self._client, OrderModel.model_validate(d)) for d in data)

    async def get_order(self, order_id: str) -> AsyncOrder:  # type: ignore[override]
        response = await self._client.get(f"/portfolio/orders/{order_id}")
        model = OrderModel.model_validate(response["order"])
        return AsyncOrder(self._client, model)

    async def get_positions(self, *, ticker=None, event_ticker=None,  # type: ignore[override]
                            count_filter=None, limit=100, cursor=None,
                            fetch_all=False, **extra_params) -> DataFrameList[PositionModel]:
        params = {
            "limit": limit,
            "ticker": normalize_ticker(ticker),
            "event_ticker": normalize_ticker(event_ticker),
            "count_filter": count_filter.value if count_filter is not None else None,
            "cursor": cursor, **extra_params,
        }
        data = await self._client.paginated_get("/portfolio/positions", "market_positions", params, fetch_all)
        return DataFrameList(PositionModel.model_validate(p) for p in data)

    async def get_fills(self, *, ticker=None, order_id=None,  # type: ignore[override]
                        min_ts=None, max_ts=None, limit=100, cursor=None,
                        fetch_all=False, **extra_params) -> DataFrameList[FillModel]:
        params = {
            "limit": limit, "ticker": normalize_ticker(ticker),
            "order_id": order_id, "min_ts": min_ts, "max_ts": max_ts,
            "cursor": cursor, **extra_params,
        }
        data = await self._client.paginated_get("/portfolio/fills", "fills", params, fetch_all)
        return DataFrameList(FillModel.model_validate(f) for f in data)

    async def batch_place_orders(self, orders: list[dict]) -> DataFrameList[AsyncOrder]:  # type: ignore[override]
        prepared = self._build_batch_orders(orders)
        response = await self._client.post("/portfolio/orders/batched", {"orders": prepared})
        result = []
        for item in response.get("orders", []):
            order_data = item.get("order")
            if order_data is None:
                continue
            result.append(AsyncOrder(self._client, OrderModel.model_validate(order_data)))
        return DataFrameList(result)

    async def batch_cancel_orders(self, order_ids: list[str]) -> DataFrameList[AsyncOrder]:  # type: ignore[override]
        orders = [{"order_id": oid} for oid in order_ids]
        response = await self._client.delete("/portfolio/orders/batched", {"orders": orders})
        result = []
        for item in response.get("orders", []):
            order_data = item.get("order")
            if order_data is None:
                continue
            result.append(AsyncOrder(self._client, OrderModel.model_validate(order_data)))
        return DataFrameList(result)

    async def get_queue_position(self, order_id: str) -> QueuePositionModel:  # type: ignore[override]
        response = await self._client.get(f"/portfolio/orders/{order_id}/queue_position")
        return QueuePositionModel(order_id=order_id, queue_position=response.get("queue_position", 0))

    async def get_queue_positions(self, *, market_tickers=None, event_ticker=None) -> DataFrameList[QueuePositionModel]:  # type: ignore[override]
        params: dict = {}
        if market_tickers:
            params["market_tickers"] = ",".join(normalize_tickers(market_tickers))
        if event_ticker:
            params["event_ticker"] = normalize_ticker(event_ticker)
        endpoint = "/portfolio/orders/queue_positions"
        if params:
            endpoint = f"{endpoint}?{urlencode(params)}"
        response = await self._client.get(endpoint)
        return DataFrameList(QueuePositionModel.model_validate(qp) for qp in response.get("queue_positions", []))

    async def get_settlements(self, *, ticker=None, event_ticker=None,  # type: ignore[override]
                              limit=100, cursor=None, fetch_all=False,
                              **extra_params) -> DataFrameList[SettlementModel]:
        params = {
            "limit": limit, "ticker": normalize_ticker(ticker),
            "event_ticker": normalize_ticker(event_ticker),
            "cursor": cursor, **extra_params,
        }
        data = await self._client.paginated_get("/portfolio/settlements", "settlements", params, fetch_all)
        return DataFrameList(SettlementModel.model_validate(s) for s in data)

    async def get_resting_order_value(self) -> int:  # type: ignore[override]
        response = await self._client.get("/portfolio/summary/total_resting_order_value")
        return response.get("total_resting_order_value", 0)

    async def create_order_group(self, contracts_limit: int) -> OrderGroupModel:  # type: ignore[override]
        response = await self._client.post("/portfolio/order_groups/create", {"contracts_limit": contracts_limit})
        return OrderGroupModel.model_validate(response)

    async def get_order_group(self, order_group_id: str) -> OrderGroupModel:  # type: ignore[override]
        response = await self._client.get(f"/portfolio/order_groups/{order_group_id}")
        response["id"] = order_group_id
        return OrderGroupModel.model_validate(response)

    async def trigger_order_group(self, order_group_id: str) -> None:  # type: ignore[override]
        await self._client.put(f"/portfolio/order_groups/{order_group_id}/trigger", {})

    async def get_order_groups(self) -> DataFrameList[OrderGroupModel]:  # type: ignore[override]
        response = await self._client.get("/portfolio/order_groups")
        return DataFrameList(OrderGroupModel.model_validate(og) for og in response.get("order_groups", []))

    async def reset_order_group(self, order_group_id: str) -> None:  # type: ignore[override]
        await self._client.put(f"/portfolio/order_groups/{order_group_id}/reset", {})

    async def update_order_group_limit(self, order_group_id: str, contracts_limit: int) -> None:  # type: ignore[override]
        await self._client.put(f"/portfolio/order_groups/{order_group_id}/limit", {"contracts_limit": contracts_limit})

    async def create_subaccount(self) -> SubaccountModel:  # type: ignore[override]
        response = await self._client.post("/portfolio/subaccounts", {})
        return SubaccountModel.model_validate(response.get("subaccount", response))

    async def transfer_between_subaccounts(self, from_subaccount_id, to_subaccount_id, amount) -> SubaccountTransferModel:  # type: ignore[override]
        body = {"from_subaccount_id": from_subaccount_id, "to_subaccount_id": to_subaccount_id, "amount": amount}
        response = await self._client.post("/portfolio/subaccounts/transfer", body)
        return SubaccountTransferModel.model_validate(response.get("transfer", response))

    async def get_subaccount_balances(self) -> DataFrameList[SubaccountBalanceModel]:  # type: ignore[override]
        response = await self._client.get("/portfolio/subaccounts/balances")
        return DataFrameList(SubaccountBalanceModel.model_validate(b) for b in response.get("balances", []))

    async def get_subaccount_transfers(self, *, limit=100, cursor=None,  # type: ignore[override]
                                       fetch_all=False, **extra_params) -> DataFrameList[SubaccountTransferModel]:
        params = {"limit": limit, "cursor": cursor, **extra_params}
        data = await self._client.paginated_get("/portfolio/subaccounts/transfers", "transfers", params, fetch_all)
        return DataFrameList(SubaccountTransferModel.model_validate(t) for t in data)
