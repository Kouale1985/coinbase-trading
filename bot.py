import os
import asyncio
import pandas as pd
from coinbase.rest import AdvancedTradeRESTClient
from datetime import datetime

# Load from environment
API_KEY = os.getenv("COINBASE_API_KEY_ID")
API_SECRET = os.getenv("COINBASE_API_PRIVATE_KEY")
TRADING_PAIRS = os.getenv("TRADING_PAIRS", "XLM-USD").split(",")
SIMULATION = os.getenv("SIMULATION", "true").lower() == "true"
LOOP_SECONDS = int(os.getenv("TRADE_LOOP_SECONDS", "120"))

client = AdvancedTradeRESTClient(api_key=API_KEY, api_secret=API_SECRET)

async def fetch_data():
    for pair in TRADING_PAIRS:
        candles = client.get_candles(product_id=pair, granularity="ONE_MINUTE")
        print(f"{datetime.now()} | Fetched {len(candles.candles)} candles for {pair}")

async def main_loop():
    while True:
        await fetch_data()
        await asyncio.sleep(LOOP_SECONDS)

if __name__ == "__main__":
    asyncio.run(main_loop())
