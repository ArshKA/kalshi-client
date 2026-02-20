"""Real-time data feed via WebSocket.

This module provides streaming market data through Kalshi's WebSocket API.
"""

from __future__ import annotations

import asyncio
import itertools
import json
import logging
import threading
import time
from typing import Any, Callable, Union, TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from ._utils import normalize_ticker, normalize_tickers

if TYPE_CHECKING:
    from .client import KalshiClient

logger = logging.getLogger(__name__)

# WebSocket endpoints
DEFAULT_WS_BASE = "wss://api.elections.kalshi.com/trade-api/ws/v2"
DEMO_WS_BASE = "wss://demo-api.kalshi.co/trade-api/ws/v2"
_WS_SIGN_PATH = "/trade-api/ws/v2"


# --- WebSocket Message Models ---


class TickerMessage(BaseModel):
    """Real-time market ticker update.

    Sent when price, volume, or open interest changes for a subscribed market.
    """

    market_ticker: str
    price: int | None = None
    yes_bid: int | None = None
    yes_ask: int | None = None
    volume: int | None = None
    open_interest: int | None = None
    dollar_volume: int | None = None
    dollar_open_interest: int | None = None
    ts: int | None = None

    model_config = ConfigDict(extra="ignore")


class OrderbookSnapshotMessage(BaseModel):
    """Full orderbook state received on initial subscription.

    Contains all current price levels. After this, you'll receive
    OrderbookDeltaMessage for incremental updates.
    """

    market_ticker: str
    yes: list[tuple[int, int]] | None = None  # [(price, quantity), ...]
    no: list[tuple[int, int]] | None = None

    model_config = ConfigDict(extra="ignore")


class OrderbookDeltaMessage(BaseModel):
    """Incremental orderbook update.

    Represents a change at a single price level. Apply to local orderbook state.
    """

    market_ticker: str
    price: int
    delta: int  # Positive = added, negative = removed
    side: str  # "yes" or "no"

    model_config = ConfigDict(extra="ignore")


class TradeMessage(BaseModel):
    """Public trade execution.

    Sent when any trade occurs on subscribed markets.
    """

    market_ticker: str | None = None
    ticker: str | None = None
    trade_id: str | None = None
    count: int | None = None
    yes_price: int | None = None
    no_price: int | None = None
    taker_side: str | None = None
    ts: int | None = None

    model_config = ConfigDict(extra="ignore")


class FillMessage(BaseModel):
    """User fill notification (private channel).

    Sent when your orders are filled.
    """

    trade_id: str | None = None
    ticker: str | None = None
    order_id: str | None = None
    side: str | None = None
    action: str | None = None
    count: int | None = None
    yes_price: int | None = None
    no_price: int | None = None
    is_taker: bool | None = None
    ts: int | None = None

    model_config = ConfigDict(extra="ignore")


class PositionMessage(BaseModel):
    """Real-time position update (private channel).

    Sent when your position in a market changes (after fills settle).
    Includes realized P&L and current exposure.
    """

    ticker: str
    position: int | None = None  # Net contracts (positive = yes, negative = no)
    market_exposure: int | None = None  # Current exposure in cents
    realized_pnl: int | None = None  # Realized P&L in cents
    total_traded: int | None = None  # Total contracts traded
    resting_orders_count: int | None = None  # Open orders count
    fees_paid: int | None = None  # Fees paid in cents
    ts: int | None = None

    model_config = ConfigDict(extra="ignore")


class MarketLifecycleMessage(BaseModel):
    """Market lifecycle state change (public channel).

    Sent when a market's status changes (open, closed, settled, etc.).
    """

    market_ticker: str
    status: str | None = None
    result: str | None = None  # Settlement result ("yes" or "no")
    ts: int | None = None

    model_config = ConfigDict(extra="ignore")


class OrderGroupUpdateMessage(BaseModel):
    """Order group lifecycle update (private channel).

    Sent when an order group's status changes (triggered, canceled, etc.).
    """

    order_group_id: str
    status: str | None = None  # "active", "triggered", "canceled"
    ts: int | None = None

    model_config = ConfigDict(extra="ignore")


# Type alias for orderbook messages (handlers receive either type)
OrderbookMessage = Union[OrderbookSnapshotMessage, OrderbookDeltaMessage]

# Maps message "type" field to model class
_MESSAGE_MODELS: dict[str, type[BaseModel]] = {
    "ticker": TickerMessage,
    "orderbook_snapshot": OrderbookSnapshotMessage,
    "orderbook_delta": OrderbookDeltaMessage,
    "trade": TradeMessage,
    "fill": FillMessage,
    "market_position": PositionMessage,
    "market_lifecycle": MarketLifecycleMessage,
    "order_group_update": OrderGroupUpdateMessage,
}

# Maps message types to channel name for handler lookup
_TYPE_TO_CHANNEL: dict[str, str] = {
    "orderbook_snapshot": "orderbook_delta",
    "orderbook_delta": "orderbook_delta",
    "ticker": "ticker",
    "trade": "trade",
    "fill": "fill",
    "market_position": "market_positions",
    "market_lifecycle": "market_lifecycle",
    "order_group_update": "order_group_updates",
}


def _parse_message(raw: str | bytes) -> tuple[str | None, str | None, Any, dict]:
    """Parse a raw WebSocket message into components.

    Shared by Feed and AsyncFeed. Handles JSON parsing, type extraction,
    channel resolution, and Pydantic model validation.

    Returns:
        (msg_type, channel, parsed_payload, raw_data)
        msg_type is None for unparseable messages.
        channel falls back to msg_type for unknown types.
    """
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None, None, None, {}

    msg_type = data.get("type")
    if not msg_type:
        return None, None, None, data

    payload = data.get("msg", data)
    channel = _TYPE_TO_CHANNEL.get(msg_type, msg_type)

    model_cls = _MESSAGE_MODELS.get(msg_type)
    if model_cls and isinstance(payload, dict):
        try:
            parsed = model_cls.model_validate(payload)
        except Exception:
            parsed = payload
    else:
        parsed = payload

    return msg_type, channel, parsed, data


class Feed:
    """Real-time streaming data feed via WebSocket.

    Provides a clean interface to Kalshi's WebSocket API with automatic
    reconnection, typed message models, and callback-based handling.

    Usage:
        feed = client.feed()

        @feed.on("ticker")
        def handle_ticker(msg: TickerMessage):
            print(f"{msg.market_ticker}: {msg.yes_bid}/{msg.yes_ask}")

        @feed.on("orderbook_delta")
        def handle_orderbook(msg: OrderbookMessage):
            if isinstance(msg, OrderbookSnapshotMessage):
                # Initialize local orderbook
                pass
            else:
                # Apply delta
                pass

        feed.subscribe("ticker", market_ticker="KXBTC-26JAN")
        feed.subscribe("orderbook_delta", market_ticker="KXBTC-26JAN")

        feed.start()  # Runs in background thread
        # ... do other work ...
        feed.stop()

        # Or use as context manager:
        with client.feed() as feed:
            feed.on("ticker", my_handler)
            feed.subscribe("ticker", market_ticker="KXBTC-26JAN")
            time.sleep(60)

    Available channels:
        - "ticker": Market price/volume updates (public)
        - "trade": Public trade executions (public)
        - "orderbook_delta": Orderbook snapshots and deltas (requires auth)
        - "fill": Your order fills (requires auth, no market filter)
        - "market_positions": Real-time position updates with P&L (requires auth, no market filter)
        - "market_lifecycle": Market state changes (public)
        - "order_group_updates": Order group lifecycle changes (requires auth)
    """

    def __init__(self, client: KalshiClient) -> None:
        """Initialize the feed.

        Args:
            client: Authenticated KalshiClient instance.
        """
        self._client = client
        self._handlers: dict[str, list[Callable]] = {}
        self._active_subs: list[dict] = []
        self._sids: dict[int, dict] = {}  # sid -> subscription params
        self._pending_subs: dict[int, dict] = {}  # cmd id -> params (awaiting confirmation)
        self._ws: Any = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._running = False
        self._cmd_id_counter = itertools.count(1)  # Thread-safe counter
        self._connected = threading.Event()
        self._lock = threading.Lock()
        self._metrics_lock = threading.Lock()

        # Latency and health tracking (protected by _metrics_lock)
        self._connected_at: float | None = None
        self._last_message_at: float | None = None
        self._last_server_ts: int | None = None  # Server timestamp in ms
        self._message_count: int = 0
        self._reconnect_count: int = 0

        # Determine WS URL from client's API base
        self._ws_url = DEMO_WS_BASE if "demo" in client.api_base else DEFAULT_WS_BASE

    def on(
        self, channel: str, handler: Callable | None = None
    ) -> Callable:
        """Register a handler for a channel.

        Can be used as a decorator or called directly:

            @feed.on("ticker")
            def handle(msg: TickerMessage):
                ...

            # or
            feed.on("ticker", my_handler)

        Args:
            channel: Channel name ("ticker", "orderbook_delta", "trade", "fill", "market_positions").
            handler: Optional handler function. If None, returns a decorator.

        Returns:
            The handler function (for decorator chaining).
        """
        if handler is not None:
            self._handlers.setdefault(channel, []).append(handler)
            return handler

        def decorator(fn: Callable) -> Callable:
            self._handlers.setdefault(channel, []).append(fn)
            return fn

        return decorator

    def subscribe(
        self,
        channel: str,
        *,
        market_ticker: str | None = None,
        market_tickers: list[str] | None = None,
    ) -> None:
        """Subscribe to a channel.

        Args:
            channel: Channel name ("ticker", "orderbook_delta", "trade", "fill", "market_positions").
            market_ticker: Filter to a single market.
            market_tickers: Filter to multiple markets.

        Note:
            - For "fill" and "market_positions" channels, market filters are ignored
              (you get all your fills/positions).
            - Can be called before or after start(). If called after, subscription
              is sent immediately.
        """
        params: dict[str, Any] = {"channels": [channel]}
        if market_ticker is not None:
            params["market_ticker"] = market_ticker.upper()
        if market_tickers is not None:
            params["market_tickers"] = normalize_tickers(market_tickers)

        with self._lock:
            self._active_subs.append(params)

        # Send immediately if connected
        if self._loop and self._connected.is_set():
            asyncio.run_coroutine_threadsafe(
                self._subscribe_and_track(params), self._loop
            )

    async def _subscribe_and_track(self, params: dict) -> None:
        """Send subscribe command and track the cmd id for sid mapping."""
        cmd_id = await self._send_cmd("subscribe", params)
        with self._lock:
            self._pending_subs[cmd_id] = params

    def unsubscribe(
        self,
        channel: str,
        *,
        market_ticker: str | None = None,
        market_tickers: list[str] | None = None,
    ) -> None:
        """Unsubscribe from a channel.

        Args:
            channel: Channel name.
            market_ticker: Single market to unsubscribe from.
            market_tickers: Multiple markets to unsubscribe from.
        """
        target: dict[str, Any] = {"channels": [channel]}
        if market_ticker is not None:
            target["market_ticker"] = market_ticker.upper()
        if market_tickers is not None:
            target["market_tickers"] = normalize_tickers(market_tickers)

        sids_to_remove: list[int] = []
        with self._lock:
            # Find matching sids for connected unsubscribe
            for sid, params in list(self._sids.items()):
                if params == target:
                    sids_to_remove.append(sid)
                    del self._sids[sid]

            # Always remove from active subs (works offline too)
            self._active_subs = [s for s in self._active_subs if s != target]

        if sids_to_remove and self._loop and self._connected.is_set():
            asyncio.run_coroutine_threadsafe(
                self._send_cmd("unsubscribe", {"sids": sids_to_remove}), self._loop
            )

    def start(self) -> None:
        """Start the feed in a background thread.

        Blocks briefly (up to 10s) until the initial connection is established.
        If connection fails, the feed continues retrying in the background.
        """
        with self._lock:
            if self._running:
                return
            self._running = True
            self._connected.clear()
            self._thread = threading.Thread(
                target=self._run, name="kalshi-feed", daemon=True
            )
            self._thread.start()
        self._connected.wait(timeout=10)

    def stop(self) -> None:
        """Stop the feed and disconnect."""
        with self._lock:
            if not self._running:
                return
            self._running = False

        # Close the WebSocket connection gracefully
        if self._ws and self._loop and self._loop.is_running():
            async def close_ws():
                try:
                    await self._ws.close()
                except Exception:
                    pass
            future = asyncio.run_coroutine_threadsafe(close_ws(), self._loop)
            try:
                future.result(timeout=2)
            except Exception:
                pass

        # Stop the event loop
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)

        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        self._connected.clear()
        self._connected_at = None

    @property
    def is_connected(self) -> bool:
        """Whether the WebSocket is currently connected."""
        return self._connected.is_set()

    @property
    def latency_ms(self) -> float | None:
        """Estimated latency in milliseconds based on last message timestamp.

        Returns None if no messages with timestamps have been received.
        This measures the difference between the server's timestamp and
        when we received the message locally. Assumes clocks are synchronized.
        """
        with self._metrics_lock:
            if self._last_server_ts is None or self._last_message_at is None:
                return None
            local_ms = self._last_message_at * 1000
            return local_ms - self._last_server_ts

    @property
    def messages_received(self) -> int:
        """Total number of messages received since feed started."""
        with self._metrics_lock:
            return self._message_count

    @property
    def uptime_seconds(self) -> float | None:
        """Seconds since connection was established. None if not connected."""
        with self._metrics_lock:
            if self._connected_at is None or not self.is_connected:
                return None
            return time.time() - self._connected_at

    @property
    def seconds_since_last_message(self) -> float | None:
        """Seconds since last message was received. None if no messages yet."""
        with self._metrics_lock:
            if self._last_message_at is None:
                return None
            return time.time() - self._last_message_at

    @property
    def reconnect_count(self) -> int:
        """Number of times the feed has reconnected (0 on first connection)."""
        with self._metrics_lock:
            return self._reconnect_count

    def _run(self) -> None:
        """Background thread entry point."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._connect_loop())
        except Exception as e:
            logger.error("Feed loop crashed: %s", e)
        finally:
            # Cancel any pending tasks before closing
            pending = asyncio.all_tasks(self._loop)
            for task in pending:
                task.cancel()
            if pending:
                self._loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True)
                )
            self._loop.close()
            self._loop = None

    async def _connect_loop(self) -> None:
        """Main connection loop with auto-reconnect."""
        try:
            import websockets
        except ImportError:
            raise ImportError(
                "websockets is required for Feed. Install with: pip install websockets"
            )

        backoff = 0.5
        max_backoff = 30

        while self._running:
            try:
                headers = self._auth_headers()
                async with websockets.connect(
                    self._ws_url,
                    additional_headers=headers,
                    ping_interval=20,
                    ping_timeout=10,
                ) as ws:
                    self._ws = ws
                    backoff = 0.5  # Reset on successful connect

                    # Track connection time
                    with self._metrics_lock:
                        if self._connected_at is not None:
                            self._reconnect_count += 1
                        self._connected_at = time.time()

                    # Replay all active subscriptions (sids reset on reconnect)
                    with self._lock:
                        self._sids.clear()
                        self._pending_subs.clear()
                        subs = list(self._active_subs)
                    for params in subs:
                        await self._subscribe_and_track(params)

                    self._connected.set()
                    logger.info("Feed connected to %s", self._ws_url)

                    async for raw_msg in ws:
                        self._dispatch(raw_msg)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self._connected.clear()
                self._ws = None
                if not self._running:
                    break
                logger.warning(
                    "Feed disconnected (%s), reconnecting in %.1fs",
                    type(e).__name__,
                    backoff,
                )
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)

        self._connected.clear()
        self._ws = None

    def _auth_headers(self) -> dict[str, str]:
        """Generate authentication headers for WebSocket handshake."""
        timestamp, signature = self._client._sign_request("GET", _WS_SIGN_PATH)
        return {
            "KALSHI-ACCESS-KEY": self._client.api_key_id,
            "KALSHI-ACCESS-SIGNATURE": signature,
            "KALSHI-ACCESS-TIMESTAMP": timestamp,
        }

    def _next_id(self) -> int:
        """Get next command ID (thread-safe)."""
        return next(self._cmd_id_counter)

    async def _send_cmd(self, cmd: str, params: dict) -> int:
        """Send a command over the WebSocket. Returns the command ID."""
        cmd_id = self._next_id()
        if self._ws:
            msg = json.dumps({"id": cmd_id, "cmd": cmd, "params": params})
            await self._ws.send(msg)
            logger.debug("Sent %s: %s", cmd, msg)
        return cmd_id

    def _dispatch(self, raw: str | bytes) -> None:
        """Parse incoming message and dispatch to handlers."""
        receive_time = time.time()
        with self._metrics_lock:
            self._last_message_at = receive_time
            self._message_count += 1

        msg_type, channel, parsed, data = _parse_message(raw)
        if msg_type is None:
            if not data:
                logger.warning("Malformed message: %.200s", raw)
            return

        # Track subscription IDs from server confirmations
        if msg_type == "subscribed":
            inner = data.get("msg", {})
            sid = inner.get("sid") if isinstance(inner, dict) else None
            if sid is not None:
                with self._lock:
                    params = self._pending_subs.pop(data.get("id"), None)
                    if params is not None:
                        self._sids[sid] = params
            return

        # Extract server timestamp if present (in milliseconds)
        payload = data.get("msg", data)
        if isinstance(payload, dict):
            ts = payload.get("ts")
            if ts is not None:
                with self._metrics_lock:
                    self._last_server_ts = ts

        handlers = self._handlers.get(channel)
        if not handlers:
            return

        for handler in handlers:
            try:
                handler(parsed)
            except Exception:
                logger.exception("Handler error on channel %s", channel)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()

    def __repr__(self) -> str:
        status = "connected" if self.is_connected else "disconnected"
        n = len(self._active_subs)
        latency = self.latency_ms
        latency_str = f" latency={latency:.1f}ms" if latency is not None else ""
        return f"<Feed {status} subs={n} msgs={self._message_count}{latency_str}>"
