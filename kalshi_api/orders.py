from __future__ import annotations
from typing import TYPE_CHECKING
from .models import OrderModel

if TYPE_CHECKING:
    from .client import KalshiClient


class Order:
    """
    Represents a Kalshi order.
    """

    def __init__(self, client: KalshiClient, data: OrderModel) -> None:
        self.client = client
        self.data = data
        self.order_id = data.order_id
        self.ticker = data.ticker
        self.status = data.status

    def cancel(self) -> OrderModel:
        """Cancel this order."""
        if not self.order_id:
            raise ValueError("Order ID not found")
        response = self.client.delete(f"/portfolio/orders/{self.order_id}")
        # Update local state
        self.data = OrderModel.model_validate(response.get("order", response))
        self.status = self.data.status
        return self.data

    def __repr__(self) -> str:
        return f"<Order {self.order_id} {self.status}>"
