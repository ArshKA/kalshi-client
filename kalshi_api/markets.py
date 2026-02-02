from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .models import MarketModel, CandlestickResponse, OrderbookResponse
from .enums import CandlestickPeriod, MarketStatus

if TYPE_CHECKING:
    from .client import KalshiClient

logger = logging.getLogger(__name__)


class Market:
    """Represents a Kalshi Market.

    Key fields are exposed as typed properties for IDE support.
    All other MarketModel fields are accessible via attribute delegation.
    """

    def __init__(self, client: KalshiClient, data: MarketModel) -> None:
        self.client = client
        self.data = data
        self._series_ticker_resolved = False
        self._resolved_series_ticker: str | None = None

    # --- Typed properties for core fields ---

    @property
    def ticker(self) -> str:
        return self.data.ticker

    @property
    def event_ticker(self) -> str | None:
        return self.data.event_ticker

    @property
    def status(self) -> MarketStatus | None:
        return self.data.status

    @property
    def title(self) -> str | None:
        return self.data.title

    @property
    def subtitle(self) -> str | None:
        return self.data.subtitle

    @property
    def yes_bid(self) -> int | None:
        return self.data.yes_bid

    @property
    def yes_ask(self) -> int | None:
        return self.data.yes_ask

    @property
    def no_bid(self) -> int | None:
        return self.data.no_bid

    @property
    def no_ask(self) -> int | None:
        return self.data.no_ask

    @property
    def last_price(self) -> int | None:
        return self.data.last_price

    @property
    def volume(self) -> int | None:
        return self.data.volume

    @property
    def volume_24h(self) -> int | None:
        return self.data.volume_24h

    @property
    def open_interest(self) -> int | None:
        return self.data.open_interest

    @property
    def liquidity(self) -> int | None:
        return self.data.liquidity

    @property
    def open_time(self) -> str | None:
        return self.data.open_time

    @property
    def close_time(self) -> str | None:
        return self.data.close_time

    @property
    def result(self) -> str | None:
        return self.data.result

    # --- Domain logic ---

    @property
    def series_ticker(self) -> str | None:
        """Lazy-resolved series_ticker. Fetches from event API on first access if missing."""
        if self.data.series_ticker is not None:
            return self.data.series_ticker
        if not self._series_ticker_resolved:
            self._series_ticker_resolved = True
            if self.data.event_ticker:
                try:
                    event_response = self.client.get(f"/events/{self.data.event_ticker}")
                    self._resolved_series_ticker = event_response["event"]["series_ticker"]
                except Exception as e:
                    logger.warning(
                        "Failed to resolve series_ticker for %s: %s", self.data.ticker, e
                    )
        return self._resolved_series_ticker

    def get_orderbook(self) -> OrderbookResponse:
        """Get the orderbook for this market."""
        response = self.client.get(f"/markets/{self.data.ticker}/orderbook")
        return OrderbookResponse.model_validate(response)

    def get_candlesticks(
        self,
        start_ts: int,
        end_ts: int,
        period: CandlestickPeriod = CandlestickPeriod.ONE_HOUR,
    ) -> CandlestickResponse:
        """Get candlestick data for this market.

        Args:
            start_ts: Start timestamp (Unix seconds).
            end_ts: End timestamp (Unix seconds).
            period: Candlestick period (ONE_MINUTE, ONE_HOUR, or ONE_DAY).
        """
        if not self.series_ticker:
            raise ValueError(f"Market {self.data.ticker} does not have a series_ticker.")

        query = f"start_ts={start_ts}&end_ts={end_ts}&period_interval={period.value}"
        endpoint = f"/series/{self.series_ticker}/markets/{self.data.ticker}/candlesticks?{query}"
        response = self.client.get(endpoint)
        return CandlestickResponse.model_validate(response)

    def __getattr__(self, name: str):
        # Fallback for fields without explicit properties.
        return getattr(self.data, name)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Market):
            return NotImplemented
        return self.data.ticker == other.data.ticker

    def __hash__(self) -> int:
        return hash(self.data.ticker)

    def __repr__(self) -> str:
        return f"<Market {self.data.ticker}>"
