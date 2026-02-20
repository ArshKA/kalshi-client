from __future__ import annotations
from functools import cached_property
from pydantic import AliasChoices, BaseModel, ConfigDict, Field
from .enums import OrderStatus, Side, Action, OrderType, MarketStatus


class MveSelectedLeg(BaseModel):
    """A single leg in a multivariate event combo."""
    event_ticker: str
    market_ticker: str
    side: str  # "yes" or "no"
    yes_settlement_value_dollars: str | None = None

    model_config = ConfigDict(extra="ignore")


class MarketModel(BaseModel):
    """Pydantic model for Market data."""

    ticker: str
    event_ticker: str | None = None
    series_ticker: str | None = None
    market_type: str | None = None
    title: str | None = None
    subtitle: str | None = None
    yes_sub_title: str | None = None
    no_sub_title: str | None = None

    # Timing
    open_time: str | None = None
    close_time: str | None = None
    expiration_time: str | None = None
    expected_expiration_time: str | None = None
    latest_expiration_time: str | None = None
    created_time: str | None = None
    updated_time: str | None = None

    # Status & Result
    status: MarketStatus | None = None
    result: str | None = None
    settlement_value: int | None = None

    # Pricing
    yes_bid: int | None = None
    yes_ask: int | None = None
    no_bid: int | None = None
    no_ask: int | None = None
    last_price: int | None = None
    previous_yes_bid: int | None = None
    previous_yes_ask: int | None = None
    previous_price: int | None = None
    notional_value: int | None = None

    # Volume & Liquidity
    volume: int | None = None
    volume_24h: int | None = None
    open_interest: int | None = None
    liquidity: int | None = None

    # Market structure
    tick_size: int | None = None
    strike_type: str | None = None
    can_close_early: bool | None = None
    rules_primary: str | None = None
    rules_secondary: str | None = None

    # Multivariate event (combo) fields
    mve_collection_ticker: str | None = None
    mve_selected_legs: list[MveSelectedLeg] | None = None
    is_provisional: bool | None = None

    model_config = ConfigDict(extra="ignore")


class EventModel(BaseModel):
    """Pydantic model for Event data."""

    event_ticker: str
    series_ticker: str
    title: str | None = None
    sub_title: str | None = None
    category: str | None = None

    # Event properties
    mutually_exclusive: bool = False
    collateral_return_type: str | None = None

    # Timing
    strike_date: str | None = None
    strike_period: str | None = None

    # Availability
    available_on_brokers: bool = False

    model_config = ConfigDict(extra="ignore")


class OrderModel(BaseModel):
    """Pydantic model for Order data."""

    order_id: str
    ticker: str
    status: OrderStatus
    action: Action | None = None
    side: Side | None = None
    type: OrderType | None = None

    # Pricing
    yes_price: int | None = None
    no_price: int | None = None

    # Counts
    initial_count: int | None = None
    fill_count: int | None = None
    remaining_count: int | None = None

    # Fees & costs (in cents)
    taker_fees: int | None = None
    maker_fees: int | None = None
    taker_fill_cost: int | None = None
    maker_fill_cost: int | None = None

    # Metadata
    user_id: str | None = None
    client_order_id: str | None = None
    created_time: str | None = None
    last_update_time: str | None = None
    expiration_time: str | None = None

    model_config = ConfigDict(extra="ignore")


class BalanceModel(BaseModel):
    """Pydantic model for Balance data. Values are in cents."""

    balance: int
    portfolio_value: int
    updated_ts: int | None = None

    model_config = ConfigDict(extra="ignore")

    def _repr_html_(self) -> str:
        from ._repr import balance_html
        return balance_html(self)


class PositionModel(BaseModel):
    """Pydantic model for a portfolio position."""

    ticker: str
    position: int  # Net position (positive = yes, negative = no)
    market_exposure: int | None = None
    total_traded: int | None = None
    resting_orders_count: int | None = None
    fees_paid: int | None = None
    realized_pnl: int | None = None
    last_updated_ts: str | None = None

    model_config = ConfigDict(extra="ignore")

    def _repr_html_(self) -> str:
        from ._repr import position_html
        return position_html(self)


class FillModel(BaseModel):
    """Pydantic model for a trade fill/execution."""

    trade_id: str
    ticker: str
    order_id: str
    side: Side
    action: Action
    count: int
    yes_price: int
    no_price: int
    is_taker: bool | None = None
    fill_id: str | None = None
    market_ticker: str | None = None
    fee_cost: str | None = None  # Dollar amount string (e.g., "0.3200")
    created_time: str | None = None
    ts: int | None = None

    model_config = ConfigDict(extra="ignore")

    def _repr_html_(self) -> str:
        from ._repr import fill_html
        return fill_html(self)


class OHLCData(BaseModel):
    """OHLC price data."""

    open: int | None = None
    high: int | None = None
    low: int | None = None
    close: int | None = None
    open_dollars: str | None = None
    high_dollars: str | None = None
    low_dollars: str | None = None
    close_dollars: str | None = None

    model_config = ConfigDict(extra="ignore")


class PriceData(BaseModel):
    """Price data with additional fields."""

    open: int | None = None
    high: int | None = None
    low: int | None = None
    close: int | None = None
    max: int | None = None
    min: int | None = None
    mean: int | None = None
    previous: int | None = None

    model_config = ConfigDict(extra="ignore")


class Candlestick(BaseModel):
    """Pydantic model for a single Candlestick."""

    end_period_ts: int
    volume: int
    open_interest: int
    price: PriceData
    yes_bid: OHLCData | None = None
    yes_ask: OHLCData | None = None

    model_config = ConfigDict(extra="ignore")


class CandlestickResponse(BaseModel):
    """Pydantic model for Candlestick API response."""

    candlesticks: list[Candlestick]
    ticker: str = Field(validation_alias="market_ticker")

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    def to_dataframe(self):
        """Convert candlesticks to a pandas DataFrame.

        Requires pandas: pip install pykalshi[dataframe]

        Returns:
            DataFrame with columns: ticker, end_period_ts, timestamp,
            volume, open_interest, open, high, low, close, mean.
        """
        from .dataframe import to_dataframe
        return to_dataframe(self)


# Orderbook Models
class OrderbookLevel(BaseModel):
    """A single price level in the orderbook (price, quantity)."""

    price: int  # Price in cents (1-99)
    quantity: int  # Number of contracts at this price level

    model_config = ConfigDict(extra="ignore")


class Orderbook(BaseModel):
    """Orderbook with yes/no price levels."""

    yes: list[tuple[int, int]] | None = None  # [(price, quantity), ...]
    no: list[tuple[int, int]] | None = None
    yes_dollars: list[tuple[str, int]] | None = None  # [(price_str, quantity_int), ...]
    no_dollars: list[tuple[str, int]] | None = None

    model_config = ConfigDict(extra="ignore")


class OrderbookFp(BaseModel):
    """Fixed-point orderbook data."""

    yes_dollars: list[tuple[str, int]] | None = None  # [(price_str, quantity_int), ...]
    no_dollars: list[tuple[str, int]] | None = None

    model_config = ConfigDict(extra="ignore")


class OrderbookResponse(BaseModel):
    """Pydantic model for the orderbook API response."""

    orderbook: Orderbook
    orderbook_fp: OrderbookFp | None = None

    model_config = ConfigDict(extra="ignore")

    @cached_property
    def yes_levels(self) -> list[OrderbookLevel]:
        """Get YES price levels as typed objects."""
        if not self.orderbook.yes:
            return []
        return [OrderbookLevel(price=p[0], quantity=p[1]) for p in self.orderbook.yes]

    @cached_property
    def no_levels(self) -> list[OrderbookLevel]:
        """Get NO price levels as typed objects."""
        if not self.orderbook.no:
            return []
        return [OrderbookLevel(price=p[0], quantity=p[1]) for p in self.orderbook.no]

    @cached_property
    def best_yes_bid(self) -> int | None:
        """Highest YES bid price, or None if no bids."""
        if not self.orderbook.yes:
            return None
        return max(p[0] for p in self.orderbook.yes)

    @cached_property
    def best_no_bid(self) -> int | None:
        """Highest NO bid price, or None if no bids."""
        if not self.orderbook.no:
            return None
        return max(p[0] for p in self.orderbook.no)

    @cached_property
    def best_yes_ask(self) -> int | None:
        """Lowest YES ask (= 100 - best NO bid)."""
        if self.best_no_bid is None:
            return None
        return 100 - self.best_no_bid

    @cached_property
    def spread(self) -> int | None:
        """Bid-ask spread in cents. None if no two-sided market."""
        if self.best_yes_bid is None or self.best_yes_ask is None:
            return None
        return self.best_yes_ask - self.best_yes_bid

    @cached_property
    def mid(self) -> float | None:
        """Mid price. None if no two-sided market."""
        if self.best_yes_bid is None or self.best_yes_ask is None:
            return None
        return (self.best_yes_bid + self.best_yes_ask) / 2

    @cached_property
    def spread_bps(self) -> float | None:
        """Spread as basis points of mid. None if no two-sided market."""
        if self.spread is None or self.mid is None or self.mid == 0:
            return None
        return (self.spread / self.mid) * 10000

    def yes_depth(self, through_price: int) -> int:
        """Total YES bid quantity at or above `through_price`."""
        if not self.orderbook.yes:
            return 0
        return sum(q for p, q in self.orderbook.yes if p >= through_price)

    def no_depth(self, through_price: int) -> int:
        """Total NO bid quantity at or above `through_price`."""
        if not self.orderbook.no:
            return 0
        return sum(q for p, q in self.orderbook.no if p >= through_price)

    @cached_property
    def imbalance(self) -> float | None:
        """Order imbalance: (yes_depth - no_depth) / (yes_depth + no_depth). Range [-1, 1]."""
        yes_total = sum(q for _, q in self.orderbook.yes) if self.orderbook.yes else 0
        no_total = sum(q for _, q in self.orderbook.no) if self.orderbook.no else 0
        total = yes_total + no_total
        if total == 0:
            return None
        return (yes_total - no_total) / total

    def vwap_to_fill(self, side: str, size: int) -> float | None:
        """Volume-weighted average price to fill `size` contracts.

        Args:
            side: "yes" or "no" - the side you're buying
            size: Number of contracts to fill

        Returns:
            VWAP in cents, or None if insufficient liquidity.
        """
        # To buy YES, you lift NO offers (sorted by price descending = best first)
        # To buy NO, you lift YES offers (sorted by price descending = best first)
        levels = self.orderbook.no if side == "yes" else self.orderbook.yes
        if not levels:
            return None

        # Sort by price descending (best offer = highest price for the other side)
        sorted_levels = sorted(levels, key=lambda x: x[0], reverse=True)

        remaining = size
        cost = 0
        for price, qty in sorted_levels:
            take = min(remaining, qty)
            # If buying YES, you pay (100 - no_price) per contract
            # If buying NO, you pay (100 - yes_price) per contract
            fill_price = 100 - price
            cost += take * fill_price
            remaining -= take
            if remaining <= 0:
                break

        if remaining > 0:
            return None  # Insufficient liquidity
        return cost / size

    def to_dataframe(self):
        """Convert orderbook to a pandas DataFrame with price levels.

        Requires pandas: pip install pykalshi[dataframe]

        Returns:
            DataFrame with columns: side, price, quantity.
            Sorted by side (yes first), then price descending.
        """
        from .dataframe import to_dataframe
        return to_dataframe(self)

    def _repr_html_(self) -> str:
        from ._repr import orderbook_html
        return orderbook_html(self)


# --- Exchange Models ---

class ExchangeStatus(BaseModel):
    """Exchange operational status."""
    exchange_active: bool
    trading_active: bool

    model_config = ConfigDict(extra="ignore")

    def _repr_html_(self) -> str:
        from ._repr import exchange_status_html
        return exchange_status_html(self)


class Announcement(BaseModel):
    """Exchange announcement."""
    id: str | None = None
    title: str
    body: str | None = None
    type: str | None = None
    created_time: str | None = None
    delivery_time: str | None = None
    status: str | None = None

    model_config = ConfigDict(extra="ignore")

    def _repr_html_(self) -> str:
        from ._repr import announcement_html
        return announcement_html(self)


# --- Account Models ---

class RateLimitTier(BaseModel):
    """Rate limit for a specific tier."""
    max_requests: int
    period_seconds: int

    model_config = ConfigDict(extra="ignore")


class APILimits(BaseModel):
    """API rate limits for the authenticated user."""
    usage_tier: str | None = None
    read_limit: int | None = None
    write_limit: int | None = None

    model_config = ConfigDict(extra="ignore")

    def _repr_html_(self) -> str:
        from ._repr import api_limits_html
        return api_limits_html(self)


# --- API Key Models ---

class APIKey(BaseModel):
    """API key information."""
    id: str = Field(validation_alias="api_key_id")
    name: str | None = None
    created_time: str | None = None
    last_used: str | None = None
    scopes: list[str] | None = None

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    def _repr_html_(self) -> str:
        from ._repr import api_key_html
        return api_key_html(self)


class GeneratedAPIKey(BaseModel):
    """Newly generated API key with private key (only returned once)."""
    id: str = Field(validation_alias="api_key_id")
    private_key: str
    name: str | None = None

    model_config = ConfigDict(extra="ignore", populate_by_name=True)


# --- Series & Trade Models ---

class SeriesModel(BaseModel):
    """Pydantic model for Series data."""
    ticker: str
    title: str | None = None
    category: str | None = None
    tags: list[str] | None = None
    settlement_timer_seconds: int | None = None
    frequency: str | None = None

    model_config = ConfigDict(extra="ignore")


class TradeModel(BaseModel):
    """Public trade execution record."""
    trade_id: str
    ticker: str
    count: int
    yes_price: int
    no_price: int
    taker_side: str | None = None
    created_time: str | None = None
    ts: int | None = None

    model_config = ConfigDict(extra="ignore")

    def _repr_html_(self) -> str:
        from ._repr import trade_html
        return trade_html(self)


class SettlementModel(BaseModel):
    """Settlement record for a resolved position."""
    ticker: str
    event_ticker: str | None = None
    market_result: str | None = None  # "yes" or "no"
    yes_count: int = 0
    no_count: int = 0
    yes_total_cost: int = 0
    no_total_cost: int = 0
    revenue: int = 0  # Payout in cents
    value: int = 0
    fee_cost: str | None = None  # Dollar string like "0.3200"
    settled_time: str | None = None

    model_config = ConfigDict(extra="ignore")

    @property
    def net_position(self) -> int:
        """Net position: positive = yes, negative = no."""
        return self.yes_count - self.no_count

    @property
    def pnl(self) -> int:
        """Net P&L in cents (revenue - costs - fees)."""
        fee_cents = round(float(self.fee_cost or 0) * 100)
        return self.revenue - self.yes_total_cost - self.no_total_cost - fee_cents

    def _repr_html_(self) -> str:
        from ._repr import settlement_html
        return settlement_html(self)


class QueuePositionModel(BaseModel):
    """Order's position in the queue at its price level."""
    order_id: str
    queue_position: int  # 0-indexed position in queue

    model_config = ConfigDict(extra="ignore")

    def _repr_html_(self) -> str:
        from ._repr import queue_position_html
        return queue_position_html(self)


class OrderGroupModel(BaseModel):
    """Order group for rate-limiting contract matches.

    Order groups limit total contracts matched across all orders in the group
    over a rolling 15-second window. When the limit is hit, all orders in the
    group are cancelled.
    """
    # API returns 'id' in list/get, but 'order_group_id' in create response
    id: str = Field(validation_alias=AliasChoices('id', 'order_group_id'))
    is_auto_cancel_enabled: bool | None = None
    contracts_limit: int | None = None
    contracts_limit_fp: str | None = None
    # Only returned from get_order_group (not list)
    orders: list[str] | None = None

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    def _repr_html_(self) -> str:
        from ._repr import order_group_html
        return order_group_html(self)


# --- Subaccount Models ---

class SubaccountModel(BaseModel):
    """Subaccount info."""
    subaccount_id: str
    subaccount_number: int
    created_time: str | None = None

    model_config = ConfigDict(extra="ignore")


class SubaccountBalanceModel(BaseModel):
    """Balance for a single subaccount."""
    subaccount_id: str
    balance: int  # In cents
    portfolio_value: int | None = None

    model_config = ConfigDict(extra="ignore")


class SubaccountTransferModel(BaseModel):
    """Record of a transfer between subaccounts."""
    transfer_id: str
    from_subaccount_id: str
    to_subaccount_id: str
    amount: int  # In cents
    created_time: str | None = None

    model_config = ConfigDict(extra="ignore")


class ForecastPoint(BaseModel):
    """A single point in forecast percentile history."""
    ts: int  # Unix timestamp
    value: int  # Forecast value in cents

    model_config = ConfigDict(extra="ignore")


class ForecastPercentileHistory(BaseModel):
    """Historical forecast data at various percentiles for an event."""
    event_ticker: str
    percentiles: dict[str, list[ForecastPoint]]  # Maps percentile (e.g., "50") to history

    model_config = ConfigDict(extra="ignore")


# --- Multivariate Event Collection Models ---

class AssociatedEventModel(BaseModel):
    """An event available as a leg in a multivariate event collection."""
    ticker: str
    is_yes_only: bool = False
    size_min: int | None = None
    size_max: int | None = None
    active_quoters: list[str] | None = None

    model_config = ConfigDict(extra="ignore")


class MveCollectionModel(BaseModel):
    """Pydantic model for a multivariate event collection (combo container)."""
    collection_ticker: str
    series_ticker: str | None = None
    title: str | None = None
    description: str | None = None
    open_date: str | None = None
    close_date: str | None = None
    associated_events: list[AssociatedEventModel] | None = None
    is_ordered: bool = False
    size_min: int | None = None
    size_max: int | None = None
    functional_description: str | None = None

    model_config = ConfigDict(extra="ignore")


# --- Communications Models (RFQ / Quotes) ---

class RfqModel(BaseModel):
    """Request for Quote on a multivariate event combo."""
    rfq_id: str = Field(validation_alias=AliasChoices('rfq_id', 'id'))
    market_ticker: str | None = None
    status: str | None = None
    contracts: int | None = None
    target_cost_dollars: str | None = None
    rest_remainder: bool | None = None
    mve_collection_ticker: str | None = None
    mve_selected_legs: list[MveSelectedLeg] | None = None
    created_time: str | None = None
    expiration_time: str | None = None
    user_id: str | None = None

    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class QuoteModel(BaseModel):
    """A quote in response to an RFQ."""
    quote_id: str = Field(validation_alias=AliasChoices('quote_id', 'id'))
    rfq_id: str | None = None
    market_ticker: str | None = None
    status: str | None = None
    yes_bid: str | None = None  # FixedPointDollars
    no_bid: str | None = None  # FixedPointDollars
    rest_remainder: bool | None = None
    created_time: str | None = None
    expiration_time: str | None = None
    user_id: str | None = None

    model_config = ConfigDict(extra="ignore", populate_by_name=True)
