"""Internal utilities."""


def normalize_ticker(ticker: str | None) -> str | None:
    """Uppercase a ticker string, passing through None."""
    return ticker.upper() if ticker else None


def normalize_tickers(tickers: list[str] | None) -> list[str] | None:
    """Uppercase a list of ticker strings, passing through None."""
    return [t.upper() for t in tickers] if tickers else None
