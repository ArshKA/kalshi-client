from enum import Enum


class Side(str, Enum):
    YES = "yes"
    NO = "no"


class Action(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    LIMIT = "limit"
    MARKET = "market"


class OrderStatus(str, Enum):
    RESTING = "resting"
    CANCELED = "canceled"
    EXECUTED = "executed"  # Order has been fully filled


class MarketStatus(str, Enum):
    """Market status values.

    Query filter values: unopened, open, paused, closed, settled
    Lifecycle values: initialized, inactive, active, closed, determined, disputed, amended, finalized
    """
    # Query filter statuses
    UNOPENED = "unopened"
    OPEN = "open"
    PAUSED = "paused"
    CLOSED = "closed"
    SETTLED = "settled"
    # Lifecycle statuses
    INITIALIZED = "initialized"
    INACTIVE = "inactive"
    ACTIVE = "active"
    DETERMINED = "determined"
    DISPUTED = "disputed"
    AMENDED = "amended"
    FINALIZED = "finalized"


class CandlestickPeriod(int, Enum):
    """Candlestick period intervals in minutes."""

    ONE_MINUTE = 1
    ONE_HOUR = 60
    ONE_DAY = 1440


class TimeInForce(str, Enum):
    """Order time-in-force options."""

    GTC = "good_till_canceled"  # Good till canceled (default)
    IOC = "immediate_or_cancel"  # Immediate or cancel - fill what you can, cancel rest
    FOK = "fill_or_kill"  # Fill or kill - fill entirely or cancel entirely


class SelfTradePrevention(str, Enum):
    """Self-trade prevention behavior."""

    CANCEL_RESTING = "taker_at_cross"  # Cancel resting order on self-cross
    CANCEL_INCOMING = "maker"  # Cancel incoming order on self-cross
