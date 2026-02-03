# kalshi-api

A typed Python client for the [Kalshi](https://kalshi.com) prediction markets API with WebSocket streaming, automatic retries, and ergonomic interfaces.

## Installation

```bash

```

Create a `.env` file with your credentials from [kalshi.com](https://kalshi.com) → Account & Security → API Keys:

```
KALSHI_API_KEY_ID=your-key-id
KALSHI_PRIVATE_KEY_PATH=/path/to/private-key.key
```

## Quick Start

```python
from kalshi_api import KalshiClient, Action, Side

client = KalshiClient()
user = client.get_user()

# Browse markets
markets = client.get_markets(status="open", limit=5)
market = client.get_market("KXBTC-25JAN15-B100000")

# Place an order
order = user.place_order(
    market,
    action=Action.BUY,
    side=Side.YES,
    count=10,
    price=45  # cents
)

order.cancel()  # if needed
```

## Usage

### Portfolio

`KalshiClient` handles authentication. Call `get_user()` to access your portfolio:

```python
client = KalshiClient()              # Uses .env credentials
client = KalshiClient(demo=True)     # Use demo environment

user = client.get_user()
user.get_balance()                   # BalanceModel with balance, portfolio_value
user.get_positions()                 # Your current positions
user.get_fills()                     # Your trade history
user.get_orders(status="resting")    # Your open orders
```

### Markets

```python
# Search markets
markets = client.get_markets(series_ticker="KXBTC", status="open")

# Get a specific market
market = client.get_market("KXBTC-25JAN15-B100000")
print(market.title, market.yes_bid, market.yes_ask)

# Market data
orderbook = market.get_orderbook()
trades = market.get_trades()
```

### Orders

```python
from kalshi_api import Action, Side, OrderType

# Limit order (default)
order = user.place_order(market, Action.BUY, Side.YES, count=10, price=50)

# Market order
order = user.place_order(market, Action.BUY, Side.YES, count=10, order_type=OrderType.MARKET)

order.cancel()
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

### Error Handling

```python
from kalshi_api import InsufficientFundsError, RateLimitError, KalshiAPIError

try:
    user.place_order(...)
except InsufficientFundsError:
    print("Not enough balance")
except RateLimitError:
    pass  # Client auto-retries with backoff
except KalshiAPIError as e:
    print(f"{e.status_code}: {e.error_code}")
```

## Comparison with Official SDK

| Feature | kalshi-api | kalshi-python (official) |
|---------|------------|--------------------------|
| WebSocket streaming | ✓ | — |
| Automatic retry with backoff | ✓ | — |
| Rate limit handling | ✓ | — |
| Domain objects (`Market`, `Order`) | ✓ | — |
| Typed exceptions | ✓ | — |
| Local orderbook management | ✓ | — |
| Pydantic models | ✓ | — |
| Core trading API coverage | ✓ | ✓ |

The official SDK is auto-generated from the OpenAPI spec. This library adds the infrastructure needed for production trading: real-time data, error recovery, and ergonomic interfaces.

## Links

- [Kalshi API Reference](https://trading-api.readme.io/reference)
- [kalshi-python (official SDK)](https://github.com/Kalshi/kalshi-python)
