from __future__ import annotations
from typing import TYPE_CHECKING
from .models import OrderModel
from .enums import OrderStatus, Action, Side, OrderType

if TYPE_CHECKING:
    from .client import KalshiClient


class Order:
    """Represents a Kalshi order.

    Key fields are exposed as typed properties for IDE support.
    All other OrderModel fields are accessible via attribute delegation.
    """

    def __init__(self, client: KalshiClient, data: OrderModel) -> None:
        self._client = client
        self.data = data

    # --- Typed properties for core fields ---

    @property
    def order_id(self) -> str:
        return self.data.order_id

    @property
    def ticker(self) -> str:
        return self.data.ticker

    @property
    def status(self) -> OrderStatus:
        return self.data.status

    @property
    def action(self) -> Action | None:
        return self.data.action

    @property
    def side(self) -> Side | None:
        return self.data.side

    @property
    def type(self) -> OrderType | None:
        return self.data.type

    @property
    def yes_price(self) -> int | None:
        return self.data.yes_price

    @property
    def no_price(self) -> int | None:
        return self.data.no_price

    @property
    def initial_count(self) -> int | None:
        return self.data.initial_count

    @property
    def fill_count(self) -> int | None:
        return self.data.fill_count

    @property
    def remaining_count(self) -> int | None:
        return self.data.remaining_count

    @property
    def created_time(self) -> str | None:
        return self.data.created_time

    # --- Domain logic ---

    def cancel(self) -> Order:
        """Cancel this order.

        Returns:
            Self with updated data (status will be CANCELED).
        """
        updated = self._client.portfolio.cancel_order(self.order_id)
        self.data = updated.data
        return self

    def amend(
        self,
        *,
        count: int | None = None,
        yes_price: int | None = None,
        no_price: int | None = None,
    ) -> Order:
        """Amend this order's price or count.

        Args:
            count: New total contract count.
            yes_price: New YES price in cents.
            no_price: New NO price in cents (converted to yes_price internally).

        Returns:
            Self with updated data.
        """
        updated = self._client.portfolio.amend_order(
            self.order_id,
            count=count,
            yes_price=yes_price,
            no_price=no_price,
        )
        self.data = updated.data
        return self

    def decrease(self, reduce_by: int) -> Order:
        """Decrease the remaining count of this order.

        Args:
            reduce_by: Number of contracts to reduce by.

        Returns:
            Self with updated data.
        """
        updated = self._client.portfolio.decrease_order(self.order_id, reduce_by)
        self.data = updated.data
        return self

    def refresh(self) -> Order:
        """Re-fetch this order's current state from the API.

        Returns:
            Self with updated data.
        """
        updated = self._client.portfolio.get_order(self.order_id)
        self.data = updated.data
        return self

    def __getattr__(self, name: str):
        return getattr(self.data, name)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Order):
            return NotImplemented
        return self.data.order_id == other.data.order_id

    def __hash__(self) -> int:
        return hash(self.data.order_id)

    def __repr__(self) -> str:
        return f"<Order {self.data.order_id} {self.data.status.value}>"
