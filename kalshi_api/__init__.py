"""
Kalshi API Client Library

A clean, modular interface for the Kalshi trading API.
"""

import logging

from .client import KalshiClient
from .portfolio import User
from .models import (
    PositionModel,
    FillModel,
    OrderModel,
    BalanceModel,
    MarketModel,
    OrderbookResponse,
    CandlestickResponse,
    PaginatedResponse,
)

# Set up logging to NullHandler by default to avoid "No handler found" warnings.
logging.getLogger(__name__).addHandler(logging.NullHandler())

__all__ = [
    "KalshiClient",
    "User",
    "PositionModel",
    "FillModel",
    "OrderModel",
    "BalanceModel",
    "MarketModel",
    "OrderbookResponse",
    "CandlestickResponse",
    "PaginatedResponse",
]
