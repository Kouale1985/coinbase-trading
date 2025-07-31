import os
import sys
import asyncio
import base64
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from coinbase.rest import RESTClient
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

# === DEBUG PRINTS: Confirm startup and env ===
print("✅ bot.py loaded", flush=True)

load_dotenv()  # Safe even on Render; does nothing if .env isn't found

API_KEY = os.getenv("COINBASE_API_KEY_ID")
API_SECRET = os.getenv("COINBASE_API_PRIVATE_KEY")

print(f"🔑 COINBASE_API_KEY_ID: {API_KEY}", flush=True)
print(f"🔐 COINBASE_API_PRIVATE_KEY: {API_SECRET[:8]}...", flush=True)

# === Convert base64 Ed25519 key to PEM format ===
def convert_ed25519_to_pem(encoded_key):
    """Convert base64-encoded Ed25519 key to PEM format"""
    try:
        print(f"🔍 Input key length: {len(encoded_key)}", flush=True)
        
        # Strip "ed25519:" prefix if present
        if encoded_key.startswith("ed25519:"):
            encoded_key = encoded_key[len("ed25519:"):]
            print("🔧 Stripped 'ed25519:' prefix", flush=True)
        
        # Clean up any whitespace or newlines
        encoded_key = encoded_key.strip()
        
        # Add base64 padding if needed
        missing_padding = len(encoded_key) % 4
        if missing_padding:
            encoded_key += "=" * (4 - missing_padding)
            print(f"🔧 Added {4 - missing_padding} padding characters", flush=True)
        
        print(f"🔍 Cleaned key length: {len(encoded_key)}", flush=True)
        
        # Decode the base64 key
        raw_bytes = base64.b64decode(encoded_key)
        print(f"🔍 Decoded bytes length: {len(raw_bytes)}", flush=True)
        
        if len(raw_bytes) < 32:
            raise ValueError(f"Key too short: got {len(raw_bytes)} bytes, expected at least 32")
        
        # Use first 32 bytes as the private key
        private_key_bytes = raw_bytes[:32]
        
        # Create Ed25519 private key object
        private_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_key_bytes)
        print("✅ Successfully created Ed25519 private key object", flush=True)
        
        # Convert to PEM format
        pem_key = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        pem_string = pem_key.decode('utf-8')
        print("✅ Successfully converted to PEM format", flush=True)
        print(f"🔍 PEM key starts with: {pem_string[:50]}...", flush=True)
        
        return pem_string
        
    except Exception as e:
        print(f"❌ Error converting key to PEM: {e}", flush=True)
        print(f"🔍 Key sample (first 20 chars): {encoded_key[:20] if encoded_key else 'None'}", flush=True)
        raise

# === Process the API secret ===
if API_SECRET:
    print("🔄 Converting Ed25519 key to PEM format...", flush=True)
    API_SECRET = convert_ed25519_to_pem(API_SECRET)
    print("✅ Key converted to PEM format", flush=True)

# === Raise error if missing ===
if not API_KEY or not API_SECRET:
    raise ValueError("Missing API credentials. Check your .env file or Render environment.")

# === Initialize client ===
print("📡 Initializing REST client...", flush=True)
client = RESTClient(api_key=API_KEY, api_secret=API_SECRET)

# === Config ===
GRANULARITY = 60  # 1 min candles
TRADING_PAIRS = os.getenv("TRADE_PAIRS", "XLM-USD,XRP-USD").split(",")
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
