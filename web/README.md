# Kalshi Dashboard

A real-time web dashboard for viewing Kalshi prediction markets. Built with FastAPI and React to demonstrate the `pykalshi` library. Originally intended for debugging the library, but can be modified into a customized dashboard with keybinds for manual trading, a console to evaluate live trading bots, or something else entirely.

## Installation

The web dashboard requires optional dependencies:

```bash
pip install pykalshi[web]
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

