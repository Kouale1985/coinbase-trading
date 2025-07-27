import json
import time
import textwrap
from datetime import datetime, timedelta, timezone
from coinbase.rest import RESTClient

# Load and convert private key into PEM format
with open("cdp_api_key.json") as f:
    key_data = json.load(f)
    API_KEY = key_data["id"]
    base64_key = key_data["privateKey"]

    # Wrap the key to proper PEM format (64 characters per line)
    wrapped_key = "\n".join(textwrap.wrap(base64_key, 64))
    PEM_KEY = f"-----BEGIN PRIVATE KEY-----\n{wrapped_key}\n-----END PRIVATE KEY-----"

# Initialize client
client = RESTClient(api_key=API_KEY, api_secret=PEM_KEY)

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
