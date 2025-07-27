import os
import asyncio
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from coinbase.rest import RESTClient
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
import base64

# Load environment variables from .env or environment
load_dotenv()

API_KEY = os.getenv("COINBASE_API_KEY")
RAW_SECRET = os.getenv("COINBASE_API_SECRET")

# --- Ed25519 Key Parsing ---
if RAW_SECRET.startswith("ed25519:"):
    RAW_SECRET = RAW_SECRET.replace("ed25519:", "")

try:
    private_bytes = base64.b64decode(RAW_SECRET)
    private_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_bytes)
    API_SECRET = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption()
    ).hex()
except Exception as e:
    raise ValueError(f"Failed to parse Ed25519 private key: {e}")

client = RESTClient(api_key=API_KEY, api_secret=API_SECRET)

# Constants
GRANULARITY = 60  # 1-minute candles
TRADING_PAIRS = ["XLM-USD", "XRP-USD", "LINK-USD", "OP-USD", "ARB-USD"]

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

async def run_bot():
    print(f"--- Running bot at {datetime.now(timezone.utc).isoformat()} ---")
    for pair in TRADING_PAIRS:
        try:
            candles = await fetch_candles(pair)
            print(f"✅ {pair}: Received {len(candles)} candles")
        except Exception as e:
            print(f"⚠️ Error processing {pair}: {e}")

async def main_loop():
    while True:
        await run_bot()
        await asyncio.sleep(120)

if __name__ == "__main__":
    asyncio.run(main_loop())
