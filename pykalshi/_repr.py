"""Jupyter/IPython display representations.

This module contains all HTML rendering logic, keeping domain classes clean.
Functions are only called when objects are displayed in Jupyter notebooks.
"""

from __future__ import annotations

from html import escape
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .markets import Market, Series
    from .orders import Order
    from .events import Event
    from .models import (
        BalanceModel, PositionModel, FillModel, OrderbookResponse,
        SettlementModel, TradeModel, ExchangeStatus, Announcement,
        APILimits, APIKey, QueuePositionModel, OrderGroupModel,
    )


# --- Styling ---
# Minimal inline CSS with kl- prefix to avoid conflicts
_STYLES = """\
<style>
.kl{font-family:system-ui,-apple-system,sans-serif;font-size:13px;line-height:1.4}
.kl table{border-collapse:collapse;margin:4px 0}
.kl td,.kl th{padding:4px 10px 4px 0;text-align:left;vertical-align:top}
.kl th{color:#6b7280;font-weight:500;white-space:nowrap}
.kl .m{font-family:ui-monospace,monospace;font-size:12px}
.kl .g{color:#16a34a}
.kl .r{color:#dc2626}
.kl .y{color:#ca8a04}
.kl .d{color:#6b7280}
.kl .pill{display:inline-block;padding:1px 6px;border-radius:4px;font-size:11px;font-weight:500}
.kl .pill-green{background:#dcfce7;color:#166534}
.kl .pill-red{background:#fee2e2;color:#991b1b}
.kl .pill-yellow{background:#fef9c3;color:#854d0e}
.kl .pill-gray{background:#f3f4f6;color:#374151}
.kl .bar-wrap{display:block;margin-top:2px;line-height:0}
.kl .bar-bg{background:#e5e7eb;border-radius:2px;height:3px;width:80px;display:inline-block}
.kl .bar-fill{display:block;height:100%;border-radius:2px;min-width:2px}
.kl .bar-green{background:#86efac}
.kl .bar-yellow{background:#fde047}
.kl .spread-wrap{display:block;margin-top:2px;line-height:0}
.kl .spread-track{background:#f3f4f6;border-radius:2px;height:3px;width:100px;position:relative;display:inline-block}
.kl .spread-bid{position:absolute;height:100%;background:#86efac;border-radius:2px 0 0 2px;left:0}
.kl .spread-ask{position:absolute;height:100%;background:#fca5a5;border-radius:0 2px 2px 0;right:0}
.kl .depth-bar{background:#e5e7eb;border-radius:1px;height:4px;width:40px;display:inline-block;vertical-align:middle;margin-left:6px}
.kl .depth-yes{background:#86efac}
.kl .depth-no{background:#fca5a5}
</style>"""


# --- Configuration ---
KALSHI_BASE_URL = "https://kalshi.com"


# --- Link helpers ---
# Kalshi URL structure:
#   - Series page: /markets/{series_ticker}
#   - Market page: /events/{event_ticker}?contract={market_ticker}
# Note: Direct event URLs (/events/{event_ticker}) don't work without a slug,
# so event links point to the series page instead.

def _link(display: str, url: str) -> str:
    """Render a clickable link."""
    return f'<a href="{url}" target="_blank" class="m" style="color:inherit;text-decoration:none;border-bottom:1px dashed #9ca3af">{escape(display)}</a>'


def _plain(text: str) -> str:
    """Render plain monospace text (non-clickable)."""
    return f'<span class="m">{escape(text)}</span>'


def _market_url(market_ticker: str, event_ticker: str) -> str:
    """Build URL for a specific market contract."""
    return f"{KALSHI_BASE_URL}/events/{event_ticker}?contract={market_ticker}"


def _series_url(series_ticker: str) -> str:
    """Build URL for a series page."""
    return f"{KALSHI_BASE_URL}/markets/{series_ticker}"


def _derive_event_ticker(market_ticker: str) -> str | None:
    """Derive event ticker from market ticker by removing the last segment.

    e.g., KXNCAAMBTOTAL-26FEB04OKLAUK-136 -> KXNCAAMBTOTAL-26FEB04OKLAUK
    """
    return market_ticker.rsplit("-", 1)[0] if "-" in market_ticker else None


def _ticker_link(ticker: str, event_ticker: str | None = None) -> str:
    """Render market ticker as link. Derives event_ticker if not provided."""
    event = event_ticker or _derive_event_ticker(ticker)
    if event:
        return _link(ticker, _market_url(ticker, event))
    return _plain(ticker)


def _event_link(event_ticker: str, series_ticker: str | None = None) -> str:
    """Render event ticker as link (points to series page)."""
    if series_ticker:
        return _link(event_ticker, _series_url(series_ticker))
    return _plain(event_ticker)


def _series_link(series_ticker: str) -> str:
    """Render series ticker as link."""
    return _link(series_ticker, _series_url(series_ticker))


def _cents(v: int | None, as_dollars: bool = False) -> str:
    """Format cents as currency. Use as_dollars=True for $X.XX format."""
    if v is None:
        return "—"
    if as_dollars:
        return f"${v / 100:,.2f}"
    return f"{v}¢"


def _num(v: int | None) -> str:
    """Format number with commas."""
    if v is None:
        return "—"
    return f"{v:,}"


def _status_pill(status: str | None) -> str:
    """Render status as a colored pill."""
    if status is None:
        return "—"
    s = status.lower()
    safe_status = escape(status)
    if s in ("active", "open", "resting"):
        return f'<span class="pill pill-green">{safe_status}</span>'
    if s in ("closed", "canceled", "cancelled"):
        return f'<span class="pill pill-red">{safe_status}</span>'
    if s in ("settled", "filled", "executed"):
        return f'<span class="pill pill-yellow">{safe_status}</span>'
    return f'<span class="pill pill-gray">{safe_status}</span>'


def _side_pill(action: str | None, side: str | None) -> str:
    """Render action/side as colored pills (always uppercase)."""
    parts = []
    if action:
        cls = "pill-green" if action.lower() == "buy" else "pill-red"
        parts.append(f'<span class="pill {cls}">{escape(action.upper())}</span>')
    if side:
        parts.append(f'<span class="pill pill-gray">{escape(side.upper())}</span>')
    return " ".join(parts) if parts else "—"


def _result_pill(result: str | None) -> str:
    """Render market result as uppercase pill."""
    if result is None:
        return "—"
    r = escape(result.upper())
    cls = "pill-green" if r == "YES" else "pill-red" if r == "NO" else "pill-gray"
    return f'<span class="pill {cls}">{r}</span>'


def _pnl(v: int | None) -> str:
    """Format P&L with color."""
    if v is None:
        return "—"
    cls = "g" if v >= 0 else "r"
    sign = "+" if v > 0 else ""
    return f'<span class="{cls}">{sign}${v / 100:,.2f}</span>'


def _row(label: str, value: str, mono: bool = False) -> str:
    """Generate a table row."""
    cls = ' class="m"' if mono else ""
    return f"<tr><th>{label}</th><td{cls}>{value}</td></tr>"


def _mono_id(id: str, max_len: int = 16) -> str:
    """Render an ID in monospace, truncated if needed."""
    safe_id = escape(id)
    if len(id) > max_len:
        return f'<span class="m">{escape(id[:max_len])}...</span>'
    return f'<span class="m">{safe_id}</span>'


def _progress_bar(filled: int, total: int, color: str = "green") -> str:
    """Render a progress bar on its own line."""
    if total == 0:
        return ""
    pct = max(1, min(100, filled / total * 100))  # min 1% so bar is visible
    return f'<span class="bar-wrap"><span class="bar-bg"><span class="bar-fill bar-{color}" style="width:{pct:.0f}%"></span></span></span>'


def _spread_viz(bid: int | None, ask: int | None) -> str:
    """Render a visual bid/ask spread indicator (0-100 scale) on its own line."""
    if bid is None or ask is None:
        return ""
    # bid and ask are in cents (0-100)
    bid_pct = bid
    ask_pct = 100 - ask  # ask from right side
    return f'<span class="spread-wrap"><span class="spread-track"><span class="spread-bid" style="width:{bid_pct}%"></span><span class="spread-ask" style="width:{ask_pct}%"></span></span></span>'


def _depth_bar(quantity: int, max_qty: int, cls: str = "depth-yes") -> str:
    """Render a depth bar inline."""
    if max_qty == 0:
        return ""
    pct = min(100, quantity / max_qty * 100)
    width = max(3, int(pct * 0.4))  # scale to max 40px
    return f'<span class="depth-bar {cls}" style="width:{width}px"></span>'


def _format_time(ts: str | None) -> str:
    """Format ISO timestamp to human-readable."""
    if not ts:
        return "—"
    try:
        # Handle ISO format: 2024-01-15T14:30:00Z
        from datetime import datetime
        if "T" in ts:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            return dt.strftime("%b %d, %H:%M")
        return ts
    except Exception:
        return ts


def _wrap(content: str) -> str:
    """Wrap content with styles and container."""
    return f'{_STYLES}<div class="kl">{content}</div>'


# --- Domain object renderers ---

def market_html(m: Market) -> str:
    """Render Market as HTML table."""
    status = m.status.value if m.status else None
    spread_viz = ""
    if m.yes_bid is not None and m.yes_ask is not None:
        spread_viz = _spread_viz(m.yes_bid, m.yes_ask)

    rows = [
        _row("Ticker", _ticker_link(m.ticker, m.event_ticker)),
        _row("Status", _status_pill(status)),
        _row("YES", f"{_cents(m.yes_bid)} / {_cents(m.yes_ask)}{spread_viz}"),
        _row("Last", _cents(m.last_price)),
        _row("Volume", _num(m.volume)),
        _row("Open Int", _num(m.open_interest)),
    ]

    if m.title:
        rows.insert(1, _row("Title", f'<span class="d">{escape(m.title)}</span>'))

    if m.result:
        rows.append(_row("Result", _result_pill(m.result)))

    if m.close_time:
        rows.append(_row("Closes", _format_time(m.close_time)))

    return _wrap(f"<table>{''.join(rows)}</table>")


def series_html(s: Series) -> str:
    """Render Series as HTML table."""
    category = f'<span class="pill pill-gray">{escape(s.category)}</span>' if s.category else "—"

    rows = [
        _row("Ticker", _series_link(s.ticker)),
        _row("Title", escape(s.title) if s.title else "—"),
        _row("Category", category),
    ]

    # Show tags if present
    tags = getattr(s, 'tags', None)
    if tags:
        tag_pills = " ".join(f'<span class="pill pill-gray">{escape(t)}</span>' for t in tags[:5])
        rows.append(_row("Tags", tag_pills))

    return _wrap(f"<table>{''.join(rows)}</table>")


def order_html(o: Order) -> str:
    """Render Order as HTML table."""
    status = o.status.value if o.status else None
    action = o.action.value if o.action else None
    side = o.side.value if o.side else None

    filled = o.fill_count or 0
    total = o.initial_count or 0
    fill_str = f"{filled}/{total}"
    if total > 0:
        pct = filled / total * 100
        fill_str += f" ({pct:.0f}%)"
        bar_color = "green" if pct == 100 else "yellow"
        fill_str += _progress_bar(filled, total, bar_color)

    price = o.yes_price if o.yes_price is not None else o.no_price

    rows = [
        _row("Order ID", _mono_id(o.order_id)),
        _row("Ticker", _ticker_link(o.ticker)),
        _row("Side", _side_pill(action, side)),
        _row("Price", _cents(price)),
        _row("Filled", fill_str),
        _row("Status", _status_pill(status)),
    ]

    if o.created_time:
        rows.append(_row("Created", _format_time(o.created_time)))

    return _wrap(f"<table>{''.join(rows)}</table>")


def event_html(e: Event) -> str:
    """Render Event as HTML table."""
    # Use checkmark/cross instead of Yes/No to avoid confusion with YES/NO sides
    exclusive = '<span class="g">✓</span>' if e.mutually_exclusive else '<span class="d">✗</span>'
    category = f'<span class="pill pill-gray">{escape(e.category)}</span>' if e.category else "—"

    rows = [
        _row("Event", _event_link(e.event_ticker, e.series_ticker)),
        _row("Series", _series_link(e.series_ticker)),
        _row("Title", escape(e.title) if e.title else "—"),
        _row("Category", category),
        _row("Exclusive", exclusive),
    ]
    return _wrap(f"<table>{''.join(rows)}</table>")


# --- Pydantic model renderers ---

def balance_html(b: BalanceModel) -> str:
    """Render BalanceModel as HTML table."""
    rows = [
        _row("Balance", _cents(b.balance, as_dollars=True)),
        _row("Portfolio", _cents(b.portfolio_value, as_dollars=True)),
    ]
    return _wrap(f"<table>{''.join(rows)}</table>")


def position_html(p: PositionModel) -> str:
    """Render PositionModel as HTML table."""
    pos_str = f"{abs(p.position)}"
    if p.position > 0:
        side_pill = '<span class="pill pill-green">YES</span>'
    elif p.position < 0:
        side_pill = '<span class="pill pill-red">NO</span>'
    else:
        side_pill = "—"

    rows = [
        _row("Ticker", _ticker_link(p.ticker)),
        _row("Position", f"{pos_str} {side_pill}"),
        _row("Exposure", _cents(p.market_exposure, as_dollars=True)),
        _row("Realized P&L", _pnl(p.realized_pnl)),
    ]
    return _wrap(f"<table>{''.join(rows)}</table>")


def fill_html(f: FillModel) -> str:
    """Render FillModel as HTML table."""
    action = f.action.value if f.action else None
    side = f.side.value if f.side else None

    # Use Taker/Maker instead of Yes/No to avoid confusion with YES/NO sides
    if f.is_taker is True:
        role = '<span class="pill pill-yellow">Taker</span>'
    elif f.is_taker is False:
        role = '<span class="pill pill-gray">Maker</span>'
    else:
        role = "—"

    rows = [
        _row("Trade ID", _mono_id(f.trade_id)),
        _row("Ticker", _ticker_link(f.ticker)),
        _row("Side", _side_pill(action, side)),
        _row("Count", _num(f.count)),
        _row("Price", _cents(f.yes_price)),
        _row("Role", role),
    ]
    return _wrap(f"<table>{''.join(rows)}</table>")


def orderbook_html(ob: OrderbookResponse) -> str:
    """Render OrderbookResponse as HTML."""
    spread = ob.spread
    mid = ob.mid
    imbalance = ob.imbalance

    spread_viz = ""
    if ob.best_yes_bid is not None and ob.best_yes_ask is not None:
        spread_viz = _spread_viz(ob.best_yes_bid, ob.best_yes_ask)

    rows = [
        _row("Best Bid", _cents(ob.best_yes_bid)),
        _row("Best Ask", _cents(ob.best_yes_ask)),
        _row("Spread", f"{spread}¢{spread_viz}" if spread is not None else "—"),
        _row("Mid", f"{mid:.1f}¢" if mid is not None else "—"),
        _row("Imbalance", f"{imbalance:+.2f}" if imbalance is not None else "—"),
    ]

    # Show top 5 levels each side with depth bars
    yes_levels = ob.yes_levels[:5] if ob.yes_levels else []
    no_levels = ob.no_levels[:5] if ob.no_levels else []

    depth_html = ""
    if yes_levels or no_levels:
        max_yes = max((l.quantity for l in yes_levels), default=1)
        max_no = max((l.quantity for l in no_levels), default=1)
        max_qty = max(max_yes, max_no)

        depth_rows = []
        for i in range(max(len(yes_levels), len(no_levels))):
            yes = yes_levels[i] if i < len(yes_levels) else None
            no = no_levels[i] if i < len(no_levels) else None
            yes_str = f"{yes.price}¢ × {yes.quantity}{_depth_bar(yes.quantity, max_qty, 'depth-yes')}" if yes else ""
            no_str = f"{no.price}¢ × {no.quantity}{_depth_bar(no.quantity, max_qty, 'depth-no')}" if no else ""
            depth_rows.append(f"<tr><td>{yes_str}</td><td>{no_str}</td></tr>")
        depth_html = f'<table style="margin-top:8px"><tr><th>YES Bids</th><th>NO Bids</th></tr>{"".join(depth_rows)}</table>'

    return _wrap(f"<table>{''.join(rows)}</table>{depth_html}")


# --- Additional model renderers ---

def settlement_html(s: SettlementModel) -> str:
    """Render SettlementModel as HTML table."""
    # Show position with formatted pills
    pos_parts = []
    if s.yes_count > 0:
        pos_parts.append(f'{s.yes_count} <span class="pill pill-green">YES</span>')
    if s.no_count > 0:
        pos_parts.append(f'{s.no_count} <span class="pill pill-red">NO</span>')
    position_str = " ".join(pos_parts) if pos_parts else "—"

    rows = [
        _row("Ticker", _ticker_link(s.ticker, s.event_ticker)),
        _row("Result", _result_pill(s.market_result)),
        _row("Position", position_str),
        _row("Revenue", _cents(s.revenue, as_dollars=True)),
        _row("P&L", _pnl(s.pnl)),
    ]

    if s.settled_time:
        rows.append(_row("Settled", _format_time(s.settled_time)))

    return _wrap(f"<table>{''.join(rows)}</table>")


def trade_html(t: TradeModel) -> str:
    """Render TradeModel as HTML table."""
    taker = t.taker_side.upper() if t.taker_side else None
    taker_cls = "pill-green" if taker == "YES" else "pill-red" if taker == "NO" else "pill-gray"
    taker_str = f'<span class="pill {taker_cls}">{taker}</span>' if taker else "—"

    rows = [
        _row("Trade ID", _mono_id(t.trade_id)),
        _row("Ticker", _ticker_link(t.ticker)),
        _row("Taker", taker_str),
        _row("Count", _num(t.count)),
        _row("Price", f"YES {_cents(t.yes_price)} / NO {_cents(t.no_price)}"),
    ]

    if t.created_time:
        rows.append(_row("Time", _format_time(t.created_time)))

    return _wrap(f"<table>{''.join(rows)}</table>")


def exchange_status_html(e: ExchangeStatus) -> str:
    """Render ExchangeStatus as HTML."""
    exchange_pill = _status_pill("active" if e.exchange_active else "closed")
    trading_pill = _status_pill("active" if e.trading_active else "closed")

    rows = [
        _row("Exchange", exchange_pill),
        _row("Trading", trading_pill),
    ]
    return _wrap(f"<table>{''.join(rows)}</table>")


def announcement_html(a: Announcement) -> str:
    """Render Announcement as HTML."""
    rows = [
        _row("Title", f"<strong>{escape(a.title)}</strong>"),
    ]

    if a.body:
        # Truncate long bodies
        body = a.body[:200] + "..." if len(a.body) > 200 else a.body
        rows.append(_row("Body", f'<span class="d">{escape(body)}</span>'))

    if a.type:
        rows.append(_row("Type", f'<span class="pill pill-gray">{escape(a.type)}</span>'))

    if a.delivery_time:
        rows.append(_row("Time", _format_time(a.delivery_time)))

    return _wrap(f"<table>{''.join(rows)}</table>")


def api_limits_html(a: APILimits) -> str:
    """Render APILimits as HTML table."""
    rows = []

    if a.usage_tier:
        rows.append(_row("Tier", f'<span class="pill pill-gray">{escape(a.usage_tier)}</span>'))

    if a.read_limit is not None:
        rows.append(_row("Read Limit", _num(a.read_limit)))

    if a.write_limit is not None:
        rows.append(_row("Write Limit", _num(a.write_limit)))

    return _wrap(f"<table>{''.join(rows)}</table>") if rows else _wrap("<em>No limits info</em>")


def api_key_html(k: APIKey) -> str:
    """Render APIKey as HTML table."""
    rows = [
        _row("ID", _mono_id(k.id)),
    ]

    if k.name:
        rows.append(_row("Name", escape(k.name)))

    if k.scopes:
        scope_pills = " ".join(f'<span class="pill pill-gray">{escape(s)}</span>' for s in k.scopes)
        rows.append(_row("Scopes", scope_pills))

    if k.created_time:
        rows.append(_row("Created", _format_time(k.created_time)))

    if k.last_used:
        rows.append(_row("Last Used", _format_time(k.last_used)))

    return _wrap(f"<table>{''.join(rows)}</table>")


def queue_position_html(q: QueuePositionModel) -> str:
    """Render QueuePositionModel as HTML table."""
    pos_display = f"#{q.queue_position + 1}"
    pos_class = "g" if q.queue_position < 3 else "y" if q.queue_position < 10 else "d"

    rows = [
        _row("Order ID", _mono_id(q.order_id)),
        _row("Queue", f'<span class="{pos_class}">{pos_display}</span>'),
    ]
    return _wrap(f"<table>{''.join(rows)}</table>")


def order_group_html(g: OrderGroupModel) -> str:
    """Render OrderGroupModel as HTML table."""
    rows = [
        _row("Group ID", _mono_id(g.id)),
    ]

    if g.contracts_limit is not None:
        rows.append(_row("Contracts Limit", _num(g.contracts_limit)))

    if g.orders:
        rows.append(_row("Orders", f'{len(g.orders)} linked'))

    return _wrap(f"<table>{''.join(rows)}</table>")


