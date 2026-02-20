from __future__ import annotations
from typing import TYPE_CHECKING
from urllib.parse import urlencode
from .models import RfqModel, QuoteModel
from .dataframe import DataFrameList

if TYPE_CHECKING:
    from .client import KalshiClient


class Communications:
    """RFQ (Request for Quote) and quote operations for combo trading.

    Multivariate event combos trade via the RFQ system rather than
    standard limit orders. The flow is:

    1. Create an RFQ broadcasting your intent to trade a combo.
    2. Market makers respond with two-sided quotes.
    3. Accept a quote to execute the trade.

    Usage:
        # Create an RFQ for a combo market
        rfq = client.communications.create_rfq(
            market_ticker="KXMVE-...",
            contracts=10,
        )

        # List active RFQs
        rfqs = client.communications.get_rfqs(status="active")

        # Respond to an RFQ as a market maker
        quote = client.communications.create_quote(
            rfq_id=rfq.rfq_id,
            yes_bid="0.45",
            no_bid="0.55",
        )
    """

    def __init__(self, client: KalshiClient) -> None:
        self._client = client

    def create_rfq(
        self,
        market_ticker: str,
        *,
        contracts: int | None = None,
        target_cost_dollars: str | None = None,
        rest_remainder: bool = False,
    ) -> RfqModel:
        """Create a Request for Quote.

        Args:
            market_ticker: The combo market ticker to request quotes for.
            contracts: Number of contracts to trade.
            target_cost_dollars: Target cost in dollars (FixedPoint string, e.g. "10.00").
                                 Use this OR contracts, not both.
            rest_remainder: If True, rest any unfilled portion on the orderbook.
        """
        body: dict = {"market_ticker": market_ticker.upper()}
        if contracts is not None:
            body["contracts"] = contracts
        if target_cost_dollars is not None:
            body["target_cost_dollars"] = target_cost_dollars
        if rest_remainder:
            body["rest_remainder"] = True

        response = self._client.post("/communications/rfqs", body)
        return RfqModel.model_validate(response.get("rfq", response))

    def get_rfqs(
        self,
        *,
        market_ticker: str | None = None,
        status: str | None = None,
        mve_collection_ticker: str | None = None,
        limit: int = 100,
        cursor: str | None = None,
        fetch_all: bool = False,
    ) -> DataFrameList[RfqModel]:
        """List RFQs.

        Args:
            market_ticker: Filter by combo market ticker.
            status: Filter by RFQ status (e.g., "active", "expired").
            mve_collection_ticker: Filter by collection ticker.
            limit: Maximum results per page (default 100).
            cursor: Pagination cursor.
            fetch_all: If True, automatically fetch all pages.
        """
        params: dict = {"limit": limit}
        if market_ticker:
            params["market_ticker"] = market_ticker.upper()
        if status:
            params["status"] = status
        if mve_collection_ticker:
            params["mve_collection_ticker"] = mve_collection_ticker
        if cursor:
            params["cursor"] = cursor

        data = self._client.paginated_get("/communications/rfqs", "rfqs", params, fetch_all)
        return DataFrameList(RfqModel.model_validate(r) for r in data)

    def get_rfq(self, rfq_id: str) -> RfqModel:
        """Get a single RFQ by ID."""
        response = self._client.get(f"/communications/rfqs/{rfq_id}")
        return RfqModel.model_validate(response.get("rfq", response))

    def create_quote(
        self,
        rfq_id: str,
        *,
        yes_bid: str | None = None,
        no_bid: str | None = None,
        rest_remainder: bool = False,
    ) -> QuoteModel:
        """Create a quote in response to an RFQ.

        Quotes are two-sided: specify yes_bid, no_bid, or both.
        Prices are in FixedPointDollars (e.g., "0.45").

        Args:
            rfq_id: ID of the RFQ to respond to.
            yes_bid: Your bid price for the YES side (FixedPointDollars).
            no_bid: Your bid price for the NO side (FixedPointDollars).
            rest_remainder: If True, rest any unfilled portion on the orderbook.
        """
        body: dict = {"rfq_id": rfq_id}
        if yes_bid is not None:
            body["yes_bid"] = yes_bid
        if no_bid is not None:
            body["no_bid"] = no_bid
        if rest_remainder:
            body["rest_remainder"] = True

        response = self._client.post("/communications/quotes", body)
        return QuoteModel.model_validate(response.get("quote", response))

    def get_quotes(
        self,
        *,
        creator_user_id: str | None = None,
        rfq_creator_user_id: str | None = None,
        rfq_id: str | None = None,
        market_ticker: str | None = None,
        status: str | None = None,
        limit: int = 100,
        cursor: str | None = None,
        fetch_all: bool = False,
    ) -> DataFrameList[QuoteModel]:
        """List quotes.

        The API requires at least one of creator_user_id or rfq_creator_user_id.

        Args:
            creator_user_id: Filter by quote creator. Required if rfq_creator_user_id not set.
            rfq_creator_user_id: Filter by RFQ creator. Required if creator_user_id not set.
            rfq_id: Filter by RFQ ID.
            market_ticker: Filter by combo market ticker.
            status: Filter by quote status.
            limit: Maximum results per page (default 100).
            cursor: Pagination cursor.
            fetch_all: If True, automatically fetch all pages.
        """
        params: dict = {"limit": limit}
        if creator_user_id:
            params["creator_user_id"] = creator_user_id
        if rfq_creator_user_id:
            params["rfq_creator_user_id"] = rfq_creator_user_id
        if rfq_id:
            params["rfq_id"] = rfq_id
        if market_ticker:
            params["market_ticker"] = market_ticker.upper()
        if status:
            params["status"] = status
        if cursor:
            params["cursor"] = cursor

        data = self._client.paginated_get("/communications/quotes", "quotes", params, fetch_all)
        return DataFrameList(QuoteModel.model_validate(q) for q in data)


class AsyncCommunications(Communications):
    """Async variant of Communications."""

    async def create_rfq(self, market_ticker, *, contracts=None,  # type: ignore[override]
                         target_cost_dollars=None, rest_remainder=False) -> RfqModel:
        body: dict = {"market_ticker": market_ticker.upper()}
        if contracts is not None:
            body["contracts"] = contracts
        if target_cost_dollars is not None:
            body["target_cost_dollars"] = target_cost_dollars
        if rest_remainder:
            body["rest_remainder"] = True
        response = await self._client.post("/communications/rfqs", body)
        return RfqModel.model_validate(response.get("rfq", response))

    async def get_rfqs(self, *, market_ticker=None, status=None,  # type: ignore[override]
                       mve_collection_ticker=None, limit=100, cursor=None,
                       fetch_all=False) -> DataFrameList[RfqModel]:
        params: dict = {"limit": limit}
        if market_ticker:
            params["market_ticker"] = market_ticker.upper()
        if status:
            params["status"] = status
        if mve_collection_ticker:
            params["mve_collection_ticker"] = mve_collection_ticker
        if cursor:
            params["cursor"] = cursor
        data = await self._client.paginated_get("/communications/rfqs", "rfqs", params, fetch_all)
        return DataFrameList(RfqModel.model_validate(r) for r in data)

    async def get_rfq(self, rfq_id: str) -> RfqModel:  # type: ignore[override]
        response = await self._client.get(f"/communications/rfqs/{rfq_id}")
        return RfqModel.model_validate(response.get("rfq", response))

    async def create_quote(self, rfq_id, *, yes_bid=None, no_bid=None,  # type: ignore[override]
                           rest_remainder=False) -> QuoteModel:
        body: dict = {"rfq_id": rfq_id}
        if yes_bid is not None:
            body["yes_bid"] = yes_bid
        if no_bid is not None:
            body["no_bid"] = no_bid
        if rest_remainder:
            body["rest_remainder"] = True
        response = await self._client.post("/communications/quotes", body)
        return QuoteModel.model_validate(response.get("quote", response))

    async def get_quotes(self, *, creator_user_id=None, rfq_creator_user_id=None,  # type: ignore[override]
                         rfq_id=None, market_ticker=None, status=None,
                         limit=100, cursor=None, fetch_all=False) -> DataFrameList[QuoteModel]:
        params: dict = {"limit": limit}
        if creator_user_id:
            params["creator_user_id"] = creator_user_id
        if rfq_creator_user_id:
            params["rfq_creator_user_id"] = rfq_creator_user_id
        if rfq_id:
            params["rfq_id"] = rfq_id
        if market_ticker:
            params["market_ticker"] = market_ticker.upper()
        if status:
            params["status"] = status
        if cursor:
            params["cursor"] = cursor
        data = await self._client.paginated_get("/communications/quotes", "quotes", params, fetch_all)
        return DataFrameList(QuoteModel.model_validate(q) for q in data)
