import os
import sys
import asyncio
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from coinbase.rest import RESTClient
from coinbase.rest.types.product_types import Granularity

# === DEBUG PRINTS: Confirm startup and env ===
print("✅ bot.py loaded", flush=True)

load_dotenv()  # Safe even on Render; does nothing if .env isn't found

API_KEY = os.getenv("COINBASE_API_KEY_ID")
API_SECRET = os.getenv("COINBASE_API_PRIVATE_KEY")

print(f"🔑 COINBASE_API_KEY_ID: {API_KEY}", flush=True)
print(f"🔐 COINBASE_API_PRIVATE_KEY: {API_SECRET[:8]}...", flush=True)

# === Strip "ed25519:" prefix if needed ===
if API_SECRET and API_SECRET.startswith("ed25519:"):
    API_SECRET = API_SECRET[len("ed25519:"):]

# === Raise error if missing ===
if not API_KEY or not API_SECRET:
    raise ValueError("Missing API credentials. Check your .env file or Render environment.")

# === Initialize client ===
print("📡 Initializing REST client...", flush=True)
client = RESTClient(api_key=API_KEY, api_secret=API_SECRET)

# === Config ===
GRANULARITY = Granularity.ONE_MINUTE  # Use the enum instead of 60
TRADING_PAIRS = os.getenv("TRADE_PAIRS", "XLM-USD,XRP-USD,LINK-USD,OP-USD,ARB-USD").split(",")
LOOP_SECONDS = int(os.getenv("TRADE_LOOP_SECONDS", "120"))
SIMULATION = os.getenv("SIMULATION", "true").lower() == "true"

# === Fetch candle data ===
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

# === Simulate a trade (mock) ===
async def simulate_trade(pair, candles):
    print(f"📊 Simulating trade for {pair} | Last close: {candles[-1][4]}", flush=True)

# === Core bot logic ===
async def run_bot():
    print(f"⏱️ Running bot at {datetime.now(timezone.utc).isoformat()}", flush=True)
    for pair in TRADING_PAIRS:
        try:
            candles = await fetch_candles(pair)
            print(f"✅ {pair}: Received {len(candles)} candles", flush=True)
            if SIMULATION:
                await simulate_trade(pair, candles)
        except Exception as e:
            print(f"⚠️ Error processing {pair}: {e}", flush=True)

# === Main loop ===
async def main_loop():
    print("🔄 Starting trading loop...", flush=True)
    while True:
        await run_bot()
        await asyncio.sleep(LOOP_SECONDS)

# === Entry point ===
if __name__ == "__main__":
    print("🚀 Launching bot.py...", flush=True)
    try:
        asyncio.run(main_loop())
    except Exception as e:
        print(f"❌ Fatal error: {e}", flush=True)
        sys.exit(1)
