from pykalshi import KalshiClient

def main():
    try:
        client = KalshiClient.from_env(demo=True)
    except Exception as e:
        print(f"Error initializing client: {e}")
        return

    # Check if KXPRESNOMD-28 is an EVENT
    event_ticker = "KXPRESNOMD-28"
    print(f"Fetching event: {event_ticker}...")
    try:
        event = client.get_event(event_ticker)
        print(f"Found event: {event.title}")
        print("Markets in this event (using get_markets()):")
        markets = event.get_markets()
        for m in markets:
            print(f" - {m.ticker}: {m.title}")
            print(f"   Yes Bid: {m.yes_bid}, Yes Ask: {m.yes_ask}")
    except Exception as e:
        print(f"Failed to fetch event or markets for {event_ticker}: {e}")

if __name__ == "__main__":
    main()
