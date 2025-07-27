import json
import time
from datetime import datetime, timedelta, timezone
from coinbase.rest import RESTClient

# Load credentials from the JSON file
with open("cdp_api_key.json") as f:
    key_data = json.load(f)
    API_KEY = key_data["id"]
    API_SECRET = key_data["privateKey"]  # Already properly formatted PEM

# Initialize Coinbase client
client = RESTClient(api_key=API_KEY, api_secret=API_SECRET)

TRADING_PAIRS = ["XLM-USD", "XRP-USD", "LINK-USD", "OP-USD", "ARB-USD"]

def fetch_data():
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(minutes=5)

    for pair in TRADING_PAIRS:
        candles = client.get_candles(
            product_id=pair,
            start=start_time.isoformat(),
            end=end_time.isoformat(),
            granularity="ONE_MINUTE"
        )
        print(f"{datetime.now()} | {pair}: {len(candles.candles)} candles")

def main_loop():
    while True:
        fetch_data()
        time.sleep(120)

if __name__ == "__main__":
    main_loop()
