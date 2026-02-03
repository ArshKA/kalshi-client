# kalshi-api

A typed Python client for the [Kalshi](https://kalshi.com) prediction markets API.

## Features

- **WebSocket streaming** — Real-time price feeds, orderbook deltas, and fill notifications
- **Typed models** — Full Pydantic models with IDE autocomplete and validation
- **Automatic retries** — Exponential backoff for rate limits and transient failures
- **Domain objects** — `Market`, `Order`, `Event` classes with intuitive methods
- **Local orderbook** — `OrderbookManager` maintains state from WebSocket deltas

## Installation

```bash
uv sync && source .venv/bin/activate
uv pip install -e .
```

## Setup

Create a `.env` file with your API credentials from [kalshi.com](https://kalshi.com) → Account & Security → API Keys:

```
KALSHI_API_KEY_ID=your-key-id
KALSHI_PRIVATE_KEY_PATH=/path/to/private-key.key
```

## Quick Start

```python
from kalshi_api import KalshiClient, Action, Side

client = KalshiClient()
user = client.get_user()

# Find markets
markets = client.get_markets(status="open", limit=5)
market = client.get_market("KXBTC-25JAN15-B100000")

# Check balance and place an order
print(f"Balance: ${user.balance.balance / 100:.2f}")

order = user.place_order(
    market,
    action=Action.BUY,
    side=Side.YES,
    count=10,
    price=45  # cents
)

# Cancel if needed
order.cancel()
```

## Core Concepts

### Client & User

`KalshiClient` handles authentication. Call `get_user()` to access your portfolio:

```python
client = KalshiClient()              # Uses .env credentials
client = KalshiClient(demo=True)     # Use demo environment

user = client.get_user()
user.balance                         # BalanceModel with balance, portfolio_value
user.get_positions()                 # Your current positions
user.get_fills()                     # Your trade history
user.get_orders(status="resting")    # Your open orders
```

### Markets

Markets are prediction contracts with YES/NO outcomes:

```python
# Search markets
markets = client.get_markets(series_ticker="KXBTC", status="open")

# Get specific market
market = client.get_market("KXBTC-25JAN15-B100000")
print(market.title, market.yes_bid, market.yes_ask)

# Market data
orderbook = market.get_orderbook()
candles = market.get_candlesticks(
    start_ts=1704067200,
    end_ts=1704153600,
    period=CandlestickPeriod.ONE_HOUR
)
```

### Orders

```python
from kalshi_api import Action, Side, OrderType

# Limit order (default)
order = user.place_order(market, Action.BUY, Side.YES, count=10, price=50)

# Market order
order = user.place_order(
    market, Action.BUY, Side.YES, count=10,
    order_type=OrderType.MARKET
)

# Manage orders
order.cancel()
orders = user.get_orders(status="resting")
```

### Real-time Streaming

Subscribe to live market data via WebSocket:

```python
from kalshi_api import Feed

async def main():
    async with Feed(client) as feed:
        await feed.subscribe_ticker("KXBTC-25JAN15-B100000")
        await feed.subscribe_orderbook("KXBTC-25JAN15-B100000")

        async for msg in feed:
            print(msg)  # TickerMessage, OrderbookSnapshotMessage, etc.
```

## Error Handling

```python
from kalshi_api import (
    KalshiAPIError,
    AuthenticationError,
    InsufficientFundsError,
    ResourceNotFoundError,
    RateLimitError,
)

try:
    user.place_order(...)
except InsufficientFundsError:
    print("Not enough balance")
except RateLimitError:
    print("Slow down")  # Client auto-retries with backoff
except KalshiAPIError as e:
    print(f"API error: {e.status_code} - {e.error_code}")
    if e.retryable:
        # Safe to retry with backoff
        pass
```

## Comparison with Official SDK

The official `kalshi-python` SDK is auto-generated from the OpenAPI spec. This library takes a different approach:

| | kalshi-api | kalshi-python |
|-|------------|---------------|
| WebSocket streaming | ✓ | — |
| Automatic retry/backoff | ✓ | — |
| Rate limiting | ✓ | — |
| Domain objects | ✓ | — |
| Typed exceptions | ✓ | — |

### Example: Streaming orderbook

```python
# kalshi-api: subscribe to real-time updates
feed = client.feed()

@feed.on("orderbook_delta")
def on_book(msg):
    print(f"{msg.market_ticker}: {msg.side} {msg.price} {msg.delta:+d}")

feed.subscribe("orderbook_delta", market_ticker="KXBTC-25JAN15")
feed.start()

# Official SDK: no WebSocket support, must poll
```

### Example: Placing an order with error handling

```python
# kalshi-api: typed exceptions with context
from kalshi_api import InsufficientFundsError, OrderRejectedError

try:
    order = client.portfolio.place_order(
        ticker="KXBTC-25JAN15",
        action=Action.BUY,
        side=Side.YES,
        count=10,
        yes_price=45,
    )
except InsufficientFundsError:
    print("Need more funds")
except OrderRejectedError as e:
    print(f"Rejected: {e.error_code}")  # e.g., "market_closed"

# Official SDK: generic exceptions, manual parsing
```

## Web UI

A local web interface for browsing markets:

```bash
uvicorn web.backend.main:app --reload
# Open http://localhost:8000
```

## Project Structure

```
kalshi_api/          # Python client library
  client.py          # KalshiClient - auth & HTTP
  portfolio.py       # User portfolio operations
  markets.py         # Market class
  orders.py          # Order class
  feed.py            # WebSocket streaming
  models.py          # Pydantic data models
  enums.py           # Action, Side, OrderType, etc.
  exceptions.py      # Error types

web/
  backend/main.py    # FastAPI server
  frontend/          # React UI
```

## Links

- [Kalshi API Reference](https://trading-api.readme.io/reference)
