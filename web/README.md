# Kalshi Dashboard

A real-time web dashboard for viewing Kalshi prediction markets. Built with FastAPI and React to demonstrate the `kalshi-api` library.

## Features

- **Live Market Data** - Real-time prices via WebSocket streaming
- **Orderbook Visualization** - Depth chart and order levels
- **Portfolio View** - Positions, balances, and P&L tracking
- **Market Browser** - Search and filter markets by event/series
- **Trade History** - Recent trades feed
- **Price Charts** - Candlestick charts with multiple timeframes

## Installation

The web dashboard requires optional dependencies:

```bash
pip install kalshi-api[web]
```

Or if installing from source:

```bash
pip install -e ".[web]"
```

## Running

From the project root:

```bash
uvicorn web.backend.main:app --reload
```

Then open http://localhost:8000 in your browser.

## Configuration

The dashboard uses the same `.env` credentials as the library:

```
KALSHI_API_KEY_ID=your-key-id
KALSHI_PRIVATE_KEY_PATH=/path/to/private-key.key
```

## Architecture

```
web/
├── backend/
│   └── main.py          # FastAPI server with 25+ REST endpoints
└── frontend/
    ├── index.html       # Entry point
    ├── app.jsx          # Main React app with routing
    ├── utils.js         # Shared utilities
    └── components/
        ├── LandingPage.jsx      # Market browser
        ├── MarketTerminal.jsx   # Single market view
        ├── PortfolioPage.jsx    # User portfolio
        ├── Orderbook.jsx        # Live orderbook
        ├── RecentTrades.jsx     # Trade feed
        ├── SimpleChart.jsx      # Price charts
        └── useMarketFeed.js     # WebSocket hook
```

The frontend uses React 18 and Tailwind CSS via CDN - no build step required.

## Purpose

This dashboard serves as:

1. **Integration test** - Validates the library works end-to-end
2. **Reference implementation** - Shows how to use the API in a real app
3. **Development tool** - Useful for testing during library development

The library (`kalshi_api/`) is the primary product. This dashboard demonstrates its capabilities.
