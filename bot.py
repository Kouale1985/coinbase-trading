import os
import time
from datetime import datetime, timedelta, timezone
from coinbase.rest.rest_client import RESTClient

API_KEY = os.getenv("COINBASE_API_KEY_ID")
API_SECRET = os.getenv("COINBASE_API_PRIVATE_KEY")

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
