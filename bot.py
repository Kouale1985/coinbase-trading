import os
import json
import asyncio
from datetime import datetime, timedelta, timezone
from coinbase.rest import RESTClient

# Load CDP API Key from mounted secret file
json_path = "/etc/secrets/cdp_api_key.json"
with open(json_path, "r") as f:
    creds = json.load(f)

API_KEY = creds.get("id")
API_SECRET = creds.get("privateKey")

# Strip "ed25519:" prefix if present
if API_SECRET and API_SECRET.startswith("ed25519:"):
    API_SECRET = API_SECRET[len("ed25519:"):]

if not API_KEY or not API_SECRET:
    raise ValueError("Missing API credentials from JSON secret.")

client = RESTClient(api_key=API_KEY, api_secret=API_SECRET)

# Constants
GRANULARITY = 60  # 1-minute candles
TRADING_PAIRS = os.getenv("TRADING_PAIRS", "XLM-USD,XRP-USD").split(",")
LOOP_SECONDS = int(os.getenv("TRADE_LOOP_SECONDS", "120"))
SIMULATION = os.getenv("SIMULATION", "true").lower() == "true"

async def fetch_candles(pair):
    now = datetime.now(timezone.utc)
    start = now - timedelta(minutes=100)
    candles = await client.get_candles(
        product_id=pair,
        start=start.isoformat(),
        end=now.isoformat(),
        granularity=GRANULARITY
    )
    return candles

async def simulate_trade(pair, candles):
    print(f"📊 Simulating trade for {pair} | Last close: {candles[-1][4]}")

async def run_bot():
    print(f"⏱️ Running bot at {datetime.now(timezone.utc).isoformat()}")
    for pair in TRADING_PAIRS:
        try:
            candles = await fetch_candles(pair)
            print(f"✅ {pair}: Received {len(candles)} candles")
            if SIMULATION:
                await simulate_trade(pair, candles)
        except Exception as e:
            print(f"⚠️ Error processing {pair}: {e}")

async def main_loop():
    print("🔄 Starting trading loop...")
    while True:
        await run_bot()
        await asyncio.sleep(LOOP_SECONDS)

if __name__ == "__main__":
    print("🚀 Launching bot.py...")
    try:
        asyncio.run(main_loop())
    except Exception as e:
        print(f"❌ Fatal error: {e}")
