import os
import time
from datetime import datetime, timedelta
from coinbase.rest.market_data import get_candles

TRADING_PAIRS = os.getenv("TRADING_PAIRS", "XLM-USD,XRP-USD,LINK-USD,OP-USD,ARB-USD").split(",")
LOOP_SECONDS = int(os.getenv("TRADE_LOOP_SECONDS", "120"))

def fetch_data():
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(minutes=5)  # adjust if needed

    for pair in TRADING_PAIRS:
        candles = get_candles(
            product_id=pair,
            granularity="ONE_MINUTE",
            start=start_time.isoformat() + "Z",
            end=end_time.isoformat() + "Z"
        )
        print(f"{datetime.now()} | Fetched {len(candles.candles)} candles for {pair}")

def main_loop():
    while True:
        fetch_data()
        time.sleep(LOOP_SECONDS)

if __name__ == "__main__":
    main_loop()
