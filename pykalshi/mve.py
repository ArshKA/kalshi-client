from __future__ import annotations
from typing import TYPE_CHECKING
from .models import MveCollectionModel, MveSelectedLeg, EventModel, MarketModel
from .dataframe import DataFrameList
from .enums import Side

if TYPE_CHECKING:
    from .client import KalshiClient
    from .events import Event
    from .markets import Market


class MveCollection:
    """Represents a multivariate event collection (combo container).

    Collections define which events can be combined into combo markets.
    Use create_market() to create a tradeable combo, then trade it via
    client.communications (RFQ system).
    """

    def __init__(self, client: KalshiClient, data: MveCollectionModel) -> None:
        self._client = client
        self.data = data

    @property
    def collection_ticker(self) -> str:
        return self.data.collection_ticker

    @property
    def title(self) -> str | None:
        return self.data.title

    @property
    def series_ticker(self) -> str | None:
        return self.data.series_ticker

    def create_market(
        self,
        selected_markets: list[dict[str, str]],
    ) -> Market:
        """Create a combo market in this collection.

        Must be called before trading or looking up a combo. Each entry
        specifies a leg of the combo.

        Args:
            selected_markets: List of leg dicts, each with keys:
                - market_ticker: The market ticker for this leg.
                - event_ticker: The event ticker for this leg.
                - side: "yes" or "no".

        Returns:
            The created combo Market.

        Example:
            market = collection.create_market([
                {"market_ticker": "KXABC-A", "event_ticker": "KXABC", "side": "yes"},
                {"market_ticker": "KXDEF-B", "event_ticker": "KXDEF", "side": "yes"},
            ])
        """
        from .markets import Market

        body = {"selected_markets": selected_markets}
        response = self._client.post(
            f"/multivariate_event_collections/{self.collection_ticker}", body
        )
        model = MarketModel.model_validate(response.get("market", response))
        return Market(self._client, model)

    def lookup_ticker(
        self,
        selected_markets: list[dict[str, str]],
    ) -> dict:
        """Look up tickers for a combo market by its leg combination.

        Returns 404 if the combination hasn't been previously created
        via create_market().

        Args:
            selected_markets: List of leg dicts (same format as create_market).

        Returns:
            Dict with market_ticker and event_ticker for the combo.
        """
        body = {"selected_markets": selected_markets}
        return self._client.put(
            f"/multivariate_event_collections/{self.collection_ticker}/lookup", body
        )

    def get_events(self, *, with_nested_markets: bool = False) -> DataFrameList[Event]:
        """Get multivariate events in this collection.

        Args:
            with_nested_markets: If True, include markets nested in each event.
        """
        return self._client.get_multivariate_events(
            collection_ticker=self.collection_ticker,
            with_nested_markets=with_nested_markets,
        )

    def __getattr__(self, name: str):
        return getattr(self.data, name)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MveCollection):
            return NotImplemented
        return self.data.collection_ticker == other.data.collection_ticker

    def __hash__(self) -> int:
        return hash(self.data.collection_ticker)

    def __repr__(self) -> str:
        parts = [f"<MveCollection {self.collection_ticker}"]
        if self.title:
            parts.append(self.title)
        n_events = len(self.data.associated_events) if self.data.associated_events else 0
        if n_events:
            parts.append(f"{n_events} events")
        return " | ".join(parts) + ">"

    def _repr_html_(self) -> str:
        from ._repr import mve_collection_html
        return mve_collection_html(self)
