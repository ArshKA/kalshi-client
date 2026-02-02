class KalshiError(Exception):
    """Base exception for all Kalshi API errors."""


class KalshiAPIError(KalshiError):
    """Raised when the API returns a non-200 response."""

    def __init__(self, status_code: int, message: str, error_code: str | None = None):
        super().__init__(f"{status_code}: {message} ({error_code})")
        self.status_code = status_code
        self.message = message
        self.error_code = error_code


class AuthenticationError(KalshiAPIError):
    """Raised when authentication fails (401/403)."""


class InsufficientFundsError(KalshiAPIError):
    """Raised when the order cannot be placed due to insufficient funds."""


class ResourceNotFoundError(KalshiAPIError):
    """Raised when a resource (market, order) is not found (404)."""


class RateLimitError(KalshiAPIError):
    """Raised when rate limit retries are exhausted (429)."""
