from __future__ import annotations
from typing import TYPE_CHECKING
from .models import EventModel

if TYPE_CHECKING:
    from .client import KalshiClient
    from .markets import Market, Series


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

    def get_markets(self) -> list[Market]:
        """Get all markets for this event."""
        return self._client.get_markets(event_ticker=self.data.event_ticker)

    def get_series(self) -> Series:
        """Get the parent Series for this event."""
        return self._client.get_series(self.series_ticker)

    def __getattr__(self, name: str):
        return getattr(self.data, name)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Event):
            return NotImplemented
        return self.data.event_ticker == other.data.event_ticker

    def __hash__(self) -> int:
        return hash(self.data.event_ticker)

    def __repr__(self) -> str:
        return f"<Event {self.data.event_ticker}>"
