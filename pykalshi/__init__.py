"""
Kalshi API Client Library

A clean, modular interface for the Kalshi trading API.
"""

import logging

from .client import KalshiClient
from .events import Event
from .markets import Market, Series
from .mve import MveCollection
from .orders import Order
from .portfolio import Portfolio
from .exchange import Exchange
from .api_keys import APIKeys
from .communications import Communications
from .feed import (
    Feed,
    TickerMessage,
    OrderbookSnapshotMessage,
    OrderbookDeltaMessage,
    OrderbookMessage,
    TradeMessage,
    FillMessage,
    PositionMessage,
    MarketLifecycleMessage,
    OrderGroupUpdateMessage,
)
from .enums import (
    Side,
    Action,
    OrderType,
    OrderStatus,
    MarketStatus,
    CandlestickPeriod,
    TimeInForce,
    SelfTradePrevention,
    PositionCountFilter,
)
from .models import (
    PositionModel,
    FillModel,
    OrderModel,
    BalanceModel,
    MarketModel,
    EventModel,
    OrderbookResponse,
    CandlestickResponse,
    ExchangeStatus,
    Announcement,
    APILimits,
    APIKey,
    GeneratedAPIKey,
    SeriesModel,
    TradeModel,
    SettlementModel,
    QueuePositionModel,
    OrderGroupModel,
    SubaccountModel,
    SubaccountBalanceModel,
    SubaccountTransferModel,
    ForecastPercentileHistory,
    MveSelectedLeg,
    MveCollectionModel,
    AssociatedEventModel,
    RfqModel,
    QuoteModel,
)
from .orderbook import OrderbookManager
from .rate_limiter import RateLimiter, NoOpRateLimiter
from .dataframe import to_dataframe, DataFrameList
from .exceptions import (
    KalshiError,
    KalshiAPIError,
    AuthenticationError,
    InsufficientFundsError,
    ResourceNotFoundError,
    RateLimitError,
    OrderRejectedError,
)

# Set up logging to NullHandler by default to avoid "No handler found" warnings.
logging.getLogger(__name__).addHandler(logging.NullHandler())

__all__ = [
    # Client
    "KalshiClient",
    # Domain objects
    "Event",
    "Market",
    "Series",
    "MveCollection",
    "Order",
    "Portfolio",
    "Exchange",
    "APIKeys",
    "Communications",
    # Feed (WebSocket)
    "Feed",
    "TickerMessage",
    "OrderbookSnapshotMessage",
    "OrderbookDeltaMessage",
    "OrderbookMessage",
    "TradeMessage",
    "FillMessage",
    "PositionMessage",
    "MarketLifecycleMessage",
    "OrderGroupUpdateMessage",
    # Enums
    "Side",
    "Action",
    "OrderType",
    "OrderStatus",
    "MarketStatus",
    "CandlestickPeriod",
    "TimeInForce",
    "SelfTradePrevention",
    "PositionCountFilter",
    # Models
    "PositionModel",
    "FillModel",
    "OrderModel",
    "BalanceModel",
    "MarketModel",
    "EventModel",
    "OrderbookResponse",
    "CandlestickResponse",
    "ExchangeStatus",
    "Announcement",
    "APILimits",
    "APIKey",
    "GeneratedAPIKey",
    "SeriesModel",
    "TradeModel",
    "SettlementModel",
    "QueuePositionModel",
    "OrderGroupModel",
    "ForecastPercentileHistory",
    # MVE & Communications Models
    "MveSelectedLeg",
    "MveCollectionModel",
    "AssociatedEventModel",
    "RfqModel",
    "QuoteModel",
    # Utilities
    "OrderbookManager",
    "RateLimiter",
    "NoOpRateLimiter",
    "to_dataframe",
    "DataFrameList",
    # Subaccount Models
    "SubaccountModel",
    "SubaccountBalanceModel",
    "SubaccountTransferModel",
    # Exceptions
    "KalshiError",
    "KalshiAPIError",
    "AuthenticationError",
    "InsufficientFundsError",
    "ResourceNotFoundError",
    "RateLimitError",
    "OrderRejectedError",
]
