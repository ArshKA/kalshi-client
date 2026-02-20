from __future__ import annotations
from typing import TYPE_CHECKING
from .models import EventModel, ForecastPercentileHistory
from .dataframe import DataFrameList

if TYPE_CHECKING:
    from .client import KalshiClient
    from .markets import Market, Series, AsyncMarket, AsyncSeries


class Event:
    """Represents a Kalshi Event.

    An event is a container for related markets (e.g., "Will X happen?" with
    multiple outcome markets).

    Key fields are exposed as typed properties for IDE support.
    All other EventModel fields are accessible via attribute delegation.
    """

    def __init__(self, client: KalshiClient, data: EventModel) -> None:
        self._client = client
        self.data = data

    # --- Typed properties for core fields ---

    @property
    def event_ticker(self) -> str:
        return self.data.event_ticker

    @property
    def series_ticker(self) -> str:
        return self.data.series_ticker

    @property
    def title(self) -> str | None:
        return self.data.title

    @property
    def category(self) -> str | None:
        return self.data.category

    @property
    def mutually_exclusive(self) -> bool:
        return self.data.mutually_exclusive

    # --- Domain logic ---

    def get_markets(self) -> DataFrameList[Market]:
        """Get all markets for this event."""
        return self._client.get_markets(event_ticker=self.data.event_ticker)

    def get_series(self) -> Series:
        """Get the parent Series for this event."""
        return self._client.get_series(self.series_ticker)

    def get_forecast_percentile_history(
        self,
        percentiles: list[int] | None = None,
    ) -> ForecastPercentileHistory:
        """Get historical forecast data at various percentiles.

        Args:
            percentiles: List of percentiles to fetch (e.g., [10, 25, 50, 75, 90]).
                        If None, returns all available percentiles.

        Returns:
            ForecastPercentileHistory with percentile -> history mapping.
        """
        endpoint = f"/events/{self.event_ticker}/forecast/percentile_history"
        if percentiles:
            endpoint += f"?percentiles={','.join(str(p) for p in percentiles)}"
        response = self._client.get(endpoint)
        return ForecastPercentileHistory.model_validate(response)

    def __getattr__(self, name: str):
        return getattr(self.data, name)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Event):
            return NotImplemented
        return self.data.event_ticker == other.data.event_ticker

    def __hash__(self) -> int:
        return hash(self.data.event_ticker)

    def __repr__(self) -> str:
        parts = [f"<Event {self.event_ticker}"]
        if self.title:
            parts.append(self.title)
        if self.mutually_exclusive:
            parts.append("excl")
        return " | ".join(parts) + ">"

    def _repr_html_(self) -> str:
        from ._repr import event_html
        return event_html(self)


class AsyncEvent(Event):
    """Async variant of Event. Inherits all properties and non-I/O methods."""

    async def get_markets(self) -> DataFrameList[AsyncMarket]:  # type: ignore[override]
        return await self._client.get_markets(event_ticker=self.data.event_ticker)

    async def get_series(self) -> AsyncSeries:  # type: ignore[override]
        return await self._client.get_series(self.series_ticker)

    async def get_forecast_percentile_history(  # type: ignore[override]
        self, percentiles: list[int] | None = None,
    ) -> ForecastPercentileHistory:
        endpoint = f"/events/{self.event_ticker}/forecast/percentile_history"
        if percentiles:
            endpoint += f"?percentiles={','.join(str(p) for p in percentiles)}"
        response = await self._client.get(endpoint)
        return ForecastPercentileHistory.model_validate(response)
