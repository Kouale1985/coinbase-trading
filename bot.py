import os
import asyncio
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from coinbase.rest import RESTClient

# Load environment variables from .env (optional for local dev)
load_dotenv()

# --- Load API credentials ---
API_KEY = os.getenv("COINBASE_API_KEY_ID")
API_SECRET = os.getenv("COINBASE_API_PRIVATE_KEY")

# Strip "ed25519:" prefix if present
if API_SECRET and API_SECRET.startswith("ed25519:"):
    API_SECRET = API_SECRET[len("ed25519:"):]

# Check for missing credentials
if not API_KEY or not API_SECRET:
    raise ValueError("Missing API credentials. Check your .env file or Render environment.")

# Initialize Coinbase REST client
client = RESTClient(api_key=API_KEY, api_secret=API_SECRET)

# --- Bot Configuration ---
GRANULARITY = 60  # 1-minute candles
TRADING_PAIRS = os.getenv("TRADE_PAIRS", "XLM-USD,XRP-USD").split(",")
LOOP_SECONDS = int(os.getenv("TRADE_LOOP_SECONDS", "120"))
SIMULATION = os.getenv("SIMULATION", "true").lower() == "true"

# --- Fetch historical candles ---
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

# --- Simulate trade (for now) ---
async def simulate_trade(pair, candles):
    print(f"📊 Simulating trade for {pair} | Last close: {candles[-1][4]}")

# --- Run trading logic ---
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

# --- Loop every N seconds ---
async def main_loop():
    print("🔄 Starting trading loop...")
    while True:
        await run_bot()
        await asyncio.sleep(LOOP_SECONDS)

# --- Entry point ---
if __name__ == "__main__":
    print("🚀 Launching bot.py...")
    try:
        asyncio.run(main_loop())
    except Exception as e:
        print(f"❌ Fatal error: {e}")
