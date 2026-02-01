from __future__ import annotations
from typing import TYPE_CHECKING, Any
from .models import MarketModel, CandlestickResponse
from .enums import CandlestickPeriod

if TYPE_CHECKING:
    from .client import KalshiClient


class Market:
    """
    Represents a Kalshi Market.
    """

    def __init__(self, client: KalshiClient, data: MarketModel) -> None:
        self.client = client
        self.data = data
        self.ticker = data.ticker
        self.event_ticker = data.event_ticker
        self.title = data.title
        self.yes_bid = data.yes_bid
        self.yes_ask = data.yes_ask

        # series_ticker may not be in API response - fetch from event if needed
        self.series_ticker = data.series_ticker or self._fetch_series_ticker()

    def _fetch_series_ticker(self) -> str | None:
        """Fetch series_ticker from the event endpoint."""
        if not self.event_ticker:
            return None
        try:
            event_response = self.client.get(f"/events/{self.event_ticker}")
            return event_response.get("event", {}).get("series_ticker")
        except Exception:
            return None

    def get_orderbook(self) -> dict[str, Any]:
        """Get the orderbook for this market."""
        return self.client.get(f"/markets/{self.ticker}/orderbook")

    def get_candlesticks(
        self,
        start_ts: int,
        end_ts: int,
        period: CandlestickPeriod = CandlestickPeriod.ONE_HOUR,
    ) -> CandlestickResponse:
        """
        Get candlestick data for this market.

        Args:
            start_ts: Start timestamp (Unix seconds)
            end_ts: End timestamp (Unix seconds)
            period: Candlestick period (ONE_MINUTE, ONE_HOUR, or ONE_DAY)
        """
        if not self.series_ticker:
            raise ValueError(f"Market {self.ticker} does not have a series_ticker.")

        query = f"start_ts={start_ts}&end_ts={end_ts}&period_interval={period.value}"
        endpoint = (
            f"/series/{self.series_ticker}/markets/{self.ticker}/candlesticks?{query}"
        )
        response = self.client.get(endpoint)
        return CandlestickResponse.model_validate(response)

    def __repr__(self) -> str:
        return f"<Market {self.ticker}>"
