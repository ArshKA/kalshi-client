"""Integration tests for pykalshi.

These tests run against the Kalshi Demo API. They require credentials
to be set in environment variables:

    KALSHI_DEMO_API_KEY_ID: Demo API key ID
    KALSHI_DEMO_PRIVATE_KEY_PATH: Path to demo private key file

Run all integration tests:
    pytest tests/integration/ -v

Run specific category:
    pytest tests/integration/test_feed.py -v

Skip integration tests:
    pytest tests/ --ignore=tests/integration/
"""
