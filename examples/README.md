# Examples

Runnable examples demonstrating the `pykalshi` library.

## Setup

1. Install the library:
   ```bash
   pip install pykalshi
   ```

2. Create a `.env` file with your Kalshi API credentials:
   ```
   KALSHI_API_KEY_ID=your-key-id
   KALSHI_PRIVATE_KEY_PATH=/path/to/private-key.key
   ```

   Get your API key from [kalshi.com](https://kalshi.com) → Account & Security → API Keys.

## Examples

| File | Description |
|------|-------------|
| `basic_usage.py` | Browse markets, check balance, view positions |
| `stream_orderbook.py` | Real-time WebSocket streaming |
| `place_order.py` | Place, modify, and cancel orders |
| `momentum_bot.py` | Simple momentum trading bot |

## Running

```bash
python examples/basic_usage.py
python examples/stream_orderbook.py
python examples/place_order.py
```

## Demo Environment

For testing without real money, use Kalshi's demo environment. Create credentials at [demo.kalshi.com](https://demo.kalshi.com), then set up `.env`:

```
KALSHI_API_KEY_ID=your-demo-key-id
KALSHI_PRIVATE_KEY_PATH=/path/to/demo-private-key.pem
```

```python
client = KalshiClient.from_env(demo=True)
```

## Ticker Hierarchy

Kalshi organizes contracts as **Series → Events → Markets**. You can read the tickers directly from any Kalshi URL:

```
https://kalshi.com/markets/kxpresperson/pres-person/kxpresperson-28
                        ─────────────  ──────────  ──────────────
                        series_ticker     slug     event_ticker
```

- **Series** (`KXPRESPERSON`) — a category of related events (e.g., "Presidential Person")
- **Event** (`KXPRESPERSON-28`) — a specific question, often with multiple markets
- **Market** (`KXPRESPERSON-28-JOSS`) — a single yes/no contract you can trade

The middle URL segment is a display slug — not used in the API. Market tickers aren't in the URL; find them through the event:

```python
# Top-down
series = client.get_series("KXPRESPERSON")
events = client.get_events(series_ticker="KXPRESPERSON")
event  = client.get_event("KXPRESPERSON-28")
markets = client.get_markets(event_ticker="KXPRESPERSON-28")

# Bottom-up
market = client.get_market("KXPRESPERSON-28-JOSS")
event  = market.get_event()
series = event.get_series()
```

> Tickers are case-insensitive — `"kxpresperson-28"` and `"KXPRESPERSON-28"` both work.
