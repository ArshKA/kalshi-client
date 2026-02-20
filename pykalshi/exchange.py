from __future__ import annotations
from typing import TYPE_CHECKING, Any
from .models import ExchangeStatus, Announcement

if TYPE_CHECKING:
    from .client import KalshiClient


class Exchange:
    """Exchange status, schedule, and announcements."""

    def __init__(self, client: KalshiClient) -> None:
        self._client = client

    def get_status(self) -> ExchangeStatus:
        """Get current exchange operational status."""
        data = self._client.get("/exchange/status")
        return ExchangeStatus.model_validate(data)

    def is_trading(self) -> bool:
        """Quick check if trading is currently active."""
        return self.get_status().trading_active

    def get_schedule(self) -> dict[str, Any]:
        """Get exchange trading schedule (raw format)."""
        data = self._client.get("/exchange/schedule")
        return data.get("schedule", {})

    def get_announcements(self) -> list[Announcement]:
        """Get exchange-wide announcements."""
        data = self._client.get("/exchange/announcements")
        return [Announcement.model_validate(a) for a in data.get("announcements", [])]

    def get_user_data_timestamp(self) -> int:
        """Get timestamp of last user data validation (Unix ms)."""
        data = self._client.get("/exchange/user_data_timestamp")
        return data.get("user_data_timestamp", 0)


class AsyncExchange(Exchange):
    """Async variant of Exchange."""

    async def get_status(self) -> ExchangeStatus:  # type: ignore[override]
        data = await self._client.get("/exchange/status")
        return ExchangeStatus.model_validate(data)

    async def is_trading(self) -> bool:  # type: ignore[override]
        status = await self.get_status()
        return status.trading_active

    async def get_schedule(self) -> dict[str, Any]:  # type: ignore[override]
        data = await self._client.get("/exchange/schedule")
        return data.get("schedule", {})

    async def get_announcements(self) -> list[Announcement]:  # type: ignore[override]
        data = await self._client.get("/exchange/announcements")
        return [Announcement.model_validate(a) for a in data.get("announcements", [])]

    async def get_user_data_timestamp(self) -> int:  # type: ignore[override]
        data = await self._client.get("/exchange/user_data_timestamp")
        return data.get("user_data_timestamp", 0)
