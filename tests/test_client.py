import pytest
from kalshi_api.exceptions import (
    AuthenticationError,
    InsufficientFundsError,
    ResourceNotFoundError,
    KalshiAPIError,
)


def test_auth_headers_generated(client, mock_response):
    """Verify headers include signature."""
    client._session.request.return_value = mock_response({})

    client.get("/test")

    call_args = client._session.request.call_args
    headers = call_args.kwargs["headers"]
    assert "KALSHI-ACCESS-KEY" in headers
    assert "KALSHI-ACCESS-SIGNATURE" in headers
    assert headers["KALSHI-ACCESS-KEY"] == "fake_key"


def test_handle_success(client, mock_response):
    """Verify successful response returns JSON."""
    client._session.request.return_value = mock_response({"data": "ok"})
    resp = client.get("/test")
    assert resp == {"data": "ok"}


def test_handle_401_raises_auth_error(client, mock_response):
    """Verify 401 raises AuthenticationError."""
    client._session.request.return_value = mock_response(
        {"message": "Unauthorized"}, status_code=401
    )
    with pytest.raises(AuthenticationError):
        client.get("/test")


def test_handle_404_raises_not_found(client, mock_response):
    """Verify 404 raises ResourceNotFoundError."""
    client._session.request.return_value = mock_response(
        {"message": "Not Found"}, status_code=404
    )
    with pytest.raises(ResourceNotFoundError):
        client.get("/test")


def test_insufficient_funds_error(client, mock_response):
    """Verify specific error code raises InsufficientFundsError."""
    client._session.request.return_value = mock_response(
        {"code": "insufficient_funds", "message": "No money"}, status_code=400
    )
    with pytest.raises(InsufficientFundsError):
        client.post("/orders", {})

    # Test alternate code "insufficient_balance"
    client._session.request.return_value = mock_response(
        {"code": "insufficient_balance"}, status_code=400
    )
    with pytest.raises(InsufficientFundsError):
        client.post("/orders", {})


def test_api_error_stores_message(client, mock_response):
    """Verify KalshiAPIError stores the message attribute."""
    client._session.request.return_value = mock_response(
        {"message": "Something went wrong", "code": "bad_request"}, status_code=400
    )
    with pytest.raises(KalshiAPIError) as exc_info:
        client.get("/test")
    assert exc_info.value.message == "Something went wrong"
    assert exc_info.value.status_code == 400
    assert exc_info.value.error_code == "bad_request"
