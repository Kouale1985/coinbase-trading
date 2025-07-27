import json
import time
import asyncio
from datetime import datetime, timedelta, timezone

from coinbase.rest import RESTClient
from strategy import should_buy, should_sell  # you must define this in strategy.py
from trade_simulator import simulate_trade   # you must define this in trade_simulator.py

import logging

# Setup logging format to see timestamps and messages
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')

# Load secrets
with open("cdp_api_key.json") as f:
    secret = json.load(f)

API_KEY = secret["id"]
API_SECRET = secret["privateKey"]

client = RESTClient(api_key=API_KEY, api_secret=API_SECRET)

TRADING_PAIRS = ["XLM-USD", "XRP-USD", "LINK-USD", "OP-USD", "ARB-USD"]
GRANULARITY = "ONE_MINUTE"

async def fetch_candles(pair):
    now = datetime.now(timezone.utc)
    start = now - timedelta(minutes=100)

    logging.info(f"🔄 Fetching candles for {pair} from {start.isoformat()} to {now.isoformat()}")

    try:
        candles = await client.get_candles(
            product_id=pair,
            start=start.isoformat(),
            end=now.isoformat(),
            granularity=GRANULARITY
        )
        logging.info(f"✅ {pair}: {len(candles.candles)} candles fetched")
        return candles
    except Exception as e:
        logging.error(f"❌ Failed to fetch candles for {pair}: {e}")
        return None

async def process_pair(pair):
    try:
        candles = await fetch_candles(pair)
        if not candles or len(candles) < 20:
            print(f"{pair} - Not enough data.")
            return

        if should_buy(candles):
            print(f"🟢 BUY signal for {pair}")
            simulate_trade(pair, "buy", candles[-1].close)
        elif should_sell(candles):
            print(f"🔴 SELL signal for {pair}")
            simulate_trade(pair, "sell", candles[-1].close)
        else:
            print(f"⚪ HOLD signal for {pair}")
    except Exception as e:
        print(f"⚠️ Error processing {pair}: {e}")

async def run_bot():
    while True:
        print(f"\n--- Running bot at {datetime.now().isoformat()} ---")
        tasks = [process_pair(pair) for pair in TRADING_PAIRS]
        await asyncio.gather(*tasks)
        await asyncio.sleep(120)

if __name__ == "__main__":
    asyncio.run(run_bot())
