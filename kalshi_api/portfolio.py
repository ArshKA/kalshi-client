from __future__ import annotations
from typing import TYPE_CHECKING
from .orders import Order
from .enums import Action, Side, OrderType, OrderStatus, TimeInForce, SelfTradePrevention
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
            self_trade_prevention: Behavior on self-cross (CANCEL_TAKER or CANCEL_MAKER).
            order_group_id: Link to an order group for OCO/bracket strategies.
        """
        if yes_price is not None and no_price is not None:
            raise ValueError("Specify yes_price or no_price, not both")
        if yes_price is None and no_price is None and order_type == OrderType.LIMIT:
            raise ValueError("Limit orders require yes_price or no_price")

        if no_price is not None:
            yes_price = 100 - no_price

        ticker_str = ticker if isinstance(ticker, str) else ticker.ticker

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

        response = self._client.post("/portfolio/orders", order_data)
        model = OrderModel.model_validate(response["order"])
        return Order(self._client, model)

    def cancel_order(self, order_id: str) -> Order:
        """Cancel a resting order.

        Args:
            order_id: ID of the order to cancel.

        Returns:
            The canceled Order with updated status.
        """
        response = self._client.delete(f"/portfolio/orders/{order_id}")
        model = OrderModel.model_validate(response["order"])
        return Order(self._client, model)

    def amend_order(
        self,
        order_id: str,
        *,
        count: int | None = None,
        yes_price: int | None = None,
        no_price: int | None = None,
    ) -> Order:
        """Amend a resting order's price or count.

        Args:
            order_id: ID of the order to amend.
            count: New total contract count.
            yes_price: New YES price in cents.
            no_price: New NO price in cents. Converted to yes_price internally.
        """
        if yes_price is not None and no_price is not None:
            raise ValueError("Specify yes_price or no_price, not both")

        if no_price is not None:
            yes_price = 100 - no_price

        body: dict = {}
        if count is not None:
            body["count"] = count
        if yes_price is not None:
            body["yes_price"] = yes_price

        if not body:
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
        status: OrderStatus | None = None,
        ticker: str | None = None,
        limit: int = 100,
        cursor: str | None = None,
        fetch_all: bool = False,
    ) -> list[Order]:
        """Get list of orders.

        Args:
            status: Filter by order status.
            ticker: Filter by market ticker.
            limit: Maximum results per page (default 100).
            cursor: Pagination cursor for fetching next page.
            fetch_all: If True, automatically fetch all pages.
        """
        params = {
            "limit": limit,
            "status": status.value if status is not None else None,
            "ticker": ticker,
            "cursor": cursor,
        }
        data = self._client.paginated_get("/portfolio/orders", "orders", params, fetch_all)
        return [Order(self._client, OrderModel.model_validate(d)) for d in data]

    def get_order(self, order_id: str) -> Order:
        """Get a single order by ID."""
        response = self._client.get(f"/portfolio/orders/{order_id}")
        model = OrderModel.model_validate(response["order"])
        return Order(self._client, model)

    def get_positions(
        self,
        ticker: str | None = None,
        event_ticker: str | None = None,
        count_filter: str | None = None,
        limit: int = 100,
        cursor: str | None = None,
        fetch_all: bool = False,
    ) -> list[PositionModel]:
        """Get portfolio positions.

        Args:
            ticker: Filter by specific market ticker.
            event_ticker: Filter by event ticker.
            count_filter: Filter positions with non-zero values.
                         Options: "position", "total_traded", or both comma-separated.
            limit: Maximum positions per page (default 100, max 1000).
            cursor: Pagination cursor for fetching next page.
            fetch_all: If True, automatically fetch all pages.
        """
        params = {
            "limit": limit,
            "ticker": ticker,
            "event_ticker": event_ticker,
            "count_filter": count_filter,
            "cursor": cursor,
        }
        data = self._client.paginated_get("/portfolio/positions", "market_positions", params, fetch_all)
        return [PositionModel.model_validate(p) for p in data]

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
        """Get trade fills (executed trades).

        Args:
            ticker: Filter by market ticker.
            order_id: Filter by specific order ID.
            min_ts: Minimum timestamp (Unix seconds).
            max_ts: Maximum timestamp (Unix seconds).
            limit: Maximum fills per page (default 100, max 200).
            cursor: Pagination cursor for fetching next page.
            fetch_all: If True, automatically fetch all pages.
        """
        params = {
            "limit": limit,
            "ticker": ticker,
            "order_id": order_id,
            "min_ts": min_ts,
            "max_ts": max_ts,
            "cursor": cursor,
        }
        data = self._client.paginated_get("/portfolio/fills", "fills", params, fetch_all)
        return [FillModel.model_validate(f) for f in data]

    # --- Batch Operations ---

    def batch_place_orders(self, orders: list[dict]) -> list[Order]:
        """Place multiple orders atomically.

        Args:
            orders: List of order dicts with keys: ticker, action, side, count,
                    type, yes_price/no_price, and optional advanced params.

        Returns:
            List of created Order objects.

        Example:
            orders = [
                {"ticker": "KXBTC", "action": "buy", "side": "yes", "count": 10, "type": "limit", "yes_price": 45},
                {"ticker": "KXBTC", "action": "buy", "side": "no", "count": 10, "type": "limit", "yes_price": 55},
            ]
            results = portfolio.batch_place_orders(orders)
        """
        response = self._client.post("/portfolio/orders/batched", {"orders": orders})
        return [Order(self._client, OrderModel.model_validate(o)) for o in response.get("orders", [])]

    def batch_cancel_orders(self, order_ids: list[str]) -> list[Order]:
        """Cancel multiple orders atomically.

        Args:
            order_ids: List of order IDs to cancel.

        Returns:
            List of canceled Order objects.
        """
        response = self._client.post(
            "/portfolio/orders/batched/cancel",
            {"order_ids": order_ids}
        )
        return [Order(self._client, OrderModel.model_validate(o)) for o in response.get("orders", [])]

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

    def get_queue_positions(self, order_ids: list[str]) -> list[QueuePositionModel]:
        """Get queue positions for multiple resting orders.

        Args:
            order_ids: List of order IDs.

        Returns:
            List of QueuePositionModel objects.
        """
        response = self._client.post(
            "/portfolio/orders/queue_positions",
            {"order_ids": order_ids}
        )
        return [
            QueuePositionModel.model_validate(qp)
            for qp in response.get("queue_positions", [])
        ]

    # --- Settlements ---

    def get_settlements(
        self,
        ticker: str | None = None,
        event_ticker: str | None = None,
        limit: int = 100,
        cursor: str | None = None,
        fetch_all: bool = False,
    ) -> list[SettlementModel]:
        """Get settlement records for resolved positions.

        Args:
            ticker: Filter by market ticker.
            event_ticker: Filter by event ticker.
            limit: Maximum settlements per page (default 100).
            cursor: Pagination cursor.
            fetch_all: If True, automatically fetch all pages.

        Returns:
            List of settlement records showing resolution outcomes.
        """
        params = {
            "limit": limit,
            "ticker": ticker,
            "event_ticker": event_ticker,
            "cursor": cursor,
        }
        data = self._client.paginated_get("/portfolio/settlements", "settlements", params, fetch_all)
        return [SettlementModel.model_validate(s) for s in data]

    def get_resting_order_value(self) -> int:
        """Get total value of all resting orders in cents.

        NOTE: This endpoint is FCM-only (institutional accounts).
        Regular users will get a 404.
        """
        response = self._client.get("/portfolio/summary/total_resting_order_value")
        return response.get("total_resting_order_value", 0)

    # --- Order Groups (OCO, Bracket Orders) ---

    def create_order_group(
        self,
        order_ids: list[str],
        *,
        max_profit: int | None = None,
        max_loss: int | None = None,
    ) -> OrderGroupModel:
        """Create an order group linking multiple orders.

        When one order fills, the group can trigger cancellation or
        execution of other orders based on the limit settings.

        Args:
            order_ids: List of order IDs to link.
            max_profit: Trigger when profit reaches this value (cents).
            max_loss: Trigger when loss reaches this value (cents).

        Returns:
            Created OrderGroupModel.
        """
        body: dict = {"order_ids": order_ids}
        if max_profit is not None:
            body["max_profit"] = max_profit
        if max_loss is not None:
            body["max_loss"] = max_loss

        response = self._client.post("/portfolio/order_groups", body)
        return OrderGroupModel.model_validate(response.get("order_group", response))

    def get_order_group(self, order_group_id: str) -> OrderGroupModel:
        """Get an order group by ID."""
        response = self._client.get(f"/portfolio/order_groups/{order_group_id}")
        return OrderGroupModel.model_validate(response.get("order_group", response))

    def trigger_order_group(self, order_group_id: str) -> OrderGroupModel:
        """Manually trigger an order group."""
        response = self._client.post(f"/portfolio/order_groups/{order_group_id}/trigger", {})
        return OrderGroupModel.model_validate(response.get("order_group", response))

    def delete_order_group(self, order_group_id: str) -> None:
        """Delete an order group (does not cancel the orders)."""
        self._client.delete(f"/portfolio/order_groups/{order_group_id}")

    def get_order_groups(
        self,
        limit: int = 100,
        cursor: str | None = None,
        fetch_all: bool = False,
    ) -> list[OrderGroupModel]:
        """List all order groups.

        Args:
            limit: Maximum results per page (default 100).
            cursor: Pagination cursor for fetching next page.
            fetch_all: If True, automatically fetch all pages.

        Returns:
            List of OrderGroupModel objects.
        """
        params = {"limit": limit, "cursor": cursor}
        data = self._client.paginated_get(
            "/portfolio/order_groups", "order_groups", params, fetch_all
        )
        return [OrderGroupModel.model_validate(og) for og in data]

    def reset_order_group(self, order_group_id: str) -> OrderGroupModel:
        """Reset matched contract counter for an order group.

        Useful for reusing a bracket/OCO after partial fills.
        """
        response = self._client.post(
            f"/portfolio/order_groups/{order_group_id}/reset", {}
        )
        return OrderGroupModel.model_validate(response.get("order_group", response))

    def update_order_group_limit(
        self,
        order_group_id: str,
        *,
        max_profit: int | None = None,
        max_loss: int | None = None,
    ) -> OrderGroupModel:
        """Update the contract limit for an order group.

        Args:
            order_group_id: ID of the order group.
            max_profit: New max profit trigger (cents).
            max_loss: New max loss trigger (cents).
        """
        body: dict = {}
        if max_profit is not None:
            body["max_profit"] = max_profit
        if max_loss is not None:
            body["max_loss"] = max_loss

        response = self._client.post(
            f"/portfolio/order_groups/{order_group_id}/limit", body
        )
        return OrderGroupModel.model_validate(response.get("order_group", response))

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

    def get_subaccount_balances(self) -> list[SubaccountBalanceModel]:
        """Get balances for all subaccounts.

        Returns:
            List of SubaccountBalanceModel with balance per subaccount.
        """
        response = self._client.get("/portfolio/subaccounts/balances")
        return [
            SubaccountBalanceModel.model_validate(b)
            for b in response.get("balances", [])
        ]

    def get_subaccount_transfers(
        self,
        limit: int = 100,
        cursor: str | None = None,
        fetch_all: bool = False,
    ) -> list[SubaccountTransferModel]:
        """Get transfer history between subaccounts.

        Args:
            limit: Maximum results per page (default 100).
            cursor: Pagination cursor for fetching next page.
            fetch_all: If True, automatically fetch all pages.

        Returns:
            List of transfer records.
        """
        params = {"limit": limit, "cursor": cursor}
        data = self._client.paginated_get(
            "/portfolio/subaccounts/transfers", "transfers", params, fetch_all
        )
        return [SubaccountTransferModel.model_validate(t) for t in data]
