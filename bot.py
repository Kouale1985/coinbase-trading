import os
import sys
import asyncio
import base64
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from coinbase.rest import RESTClient
from strategy import rsi, should_buy, should_sell

# === DEBUG PRINTS: Confirm startup and env ===
print("✅ bot.py loaded", flush=True)

load_dotenv()  # Safe even on Render; does nothing if .env isn't found

API_KEY = os.getenv("COINBASE_API_KEY_ID")
API_SECRET = os.getenv("COINBASE_API_PRIVATE_KEY")

print(f"🔑 COINBASE_API_KEY_ID: {API_KEY}", flush=True)
print(f"🔐 COINBASE_API_PRIVATE_KEY: {API_SECRET[:8]}...", flush=True)

def convert_base64_to_pem(base64_key):
    """Convert base64-encoded private key to PEM format"""
    # Remove ed25519: prefix if present
    if base64_key.startswith("ed25519:"):
        base64_key = base64_key[len("ed25519:"):]
    
    # Add base64 padding if needed
    missing_padding = len(base64_key) % 4
    if missing_padding:
        base64_key += "=" * (4 - missing_padding)
    
    try:
        # Decode base64
        raw_bytes = base64.b64decode(base64_key)
        
        # Ensure we have at least 32 bytes for Ed25519
        if len(raw_bytes) < 32:
            raise ValueError(f"Key too short: got {len(raw_bytes)} bytes")
        
        # Take first 32 bytes for Ed25519 private key
        private_key_bytes = raw_bytes[:32]
        
        # Convert to PEM format
        pem_key = f"""-----BEGIN PRIVATE KEY-----
{base64.b64encode(private_key_bytes).decode('utf-8')}
-----END PRIVATE KEY-----"""
        
        return pem_key
    except Exception as e:
        raise ValueError(f"Failed to convert key to PEM format: {e}")

# === Convert API secret to PEM format ===
if API_SECRET:
    try:
        API_SECRET = convert_base64_to_pem(API_SECRET)
        print("✅ Successfully converted private key to PEM format", flush=True)
    except Exception as e:
        print(f"❌ Failed to convert private key: {e}", flush=True)
        raise

# === Raise error if missing ===
if not API_KEY or not API_SECRET:
    raise ValueError("Missing API credentials. Check your .env file or Render environment.")

# === Initialize client ===
print("📡 Initializing REST client...", flush=True)
client = RESTClient(api_key=API_KEY, api_secret=API_SECRET)

# === Config ===
GRANULARITY = "ONE_MINUTE"  # Use string instead of 60
TRADING_PAIRS = os.getenv("TRADE_PAIRS", "XLM-USD,XRP-USD,LINK-USD,OP-USD,ARB-USD").split(",")
LOOP_SECONDS = int(os.getenv("TRADE_LOOP_SECONDS", "120"))
SIMULATION = os.getenv("SIMULATION", "true").lower() == "true"

# === Trading state ===
portfolio = {
    "USD": 100000,  # starting balance
    "positions": {},
    "total_trades": 0,
    "winning_trades": 0,
    "total_pnl": 0.0
}

# === Fetch candle data ===
async def fetch_candles(pair):
    now = datetime.now(timezone.utc)
    start = now - timedelta(minutes=100)
    
    print(f"🔍 Fetching candles for {pair}:", flush=True)
    print(f"   - start: {start.isoformat()}", flush=True)
    print(f"   - end: {now.isoformat()}", flush=True)
    print(f"   - granularity: {GRANULARITY}", flush=True)
    
    candles = await client.get_candles(
        product_id=pair,
        start=start.isoformat(),
        end=now.isoformat(),
        granularity=GRANULARITY
    )
    
    print(f"✅ {pair}: Received candles response - Type: {type(candles)}", flush=True)
    print(f"   - Candles attribute exists with {len(candles)} items", flush=True)
    
    return candles

# === Calculate RSI and make trading decision ===
def analyze_and_decide(pair, candles):
    if len(candles) < 14:
        print(f"⚠️ {pair}: Not enough data for RSI calculation", flush=True)
        return "HOLD"
    
    # Extract closing prices
    closes = [float(candle.close) for candle in candles]
    current_price = closes[-1]
    
    # Calculate RSI
    rsi_values = rsi(closes)
    current_rsi = rsi_values[-1] if rsi_values else 50
    
    # Make trading decision
    if should_buy(candles):
        action = "BUY"
    elif should_sell(candles):
        action = "SELL"
    else:
        action = "HOLD"
    
    print(f"📊 {pair}: ${current_price:.6f} | RSI: {current_rsi:.2f} | Action: {action}", flush=True)
    
    return action

# === Simulate trading ===
def simulate_trade(pair, action, price):
    if action == "BUY" and portfolio["USD"] > 0:
        # Simulate buying with 10% of available USD
        buy_amount = portfolio["USD"] * 0.1
        quantity = buy_amount / price
        portfolio["USD"] -= buy_amount
        portfolio["positions"][pair] = portfolio["positions"].get(pair, 0) + quantity
        portfolio["total_trades"] += 1
        print(f"💰 [SIM] Bought {quantity:.4f} {pair} at ${price:.6f}", flush=True)
        
    elif action == "SELL" and portfolio["positions"].get(pair, 0) > 0:
        # Simulate selling all holdings
        quantity = portfolio["positions"][pair]
        sell_amount = quantity * price
        portfolio["USD"] += sell_amount
        portfolio["positions"][pair] = 0
        portfolio["total_trades"] += 1
        print(f"💰 [SIM] Sold {quantity:.4f} {pair} at ${price:.6f}", flush=True)

# === Print trading summary ===
def print_summary():
    print(f"📊 TRADING SUMMARY:", flush=True)
    print(f"   💼 Open Positions: {len([p for p in portfolio['positions'].values() if p > 0])}", flush=True)
    print(f"   📈 Total Trades: {portfolio['total_trades']}", flush=True)
    print(f"   🎯 Winning Trades: {portfolio['winning_trades']}/{portfolio['total_trades']}", flush=True)
    print(f"   💰 Total PnL: ${portfolio['total_pnl']:.2f}", flush=True)

# === Core bot logic ===
async def run_bot():
    print(f"⏱️ Running bot at {datetime.now(timezone.utc).isoformat()}", flush=True)
    
    for pair in TRADING_PAIRS:
        try:
            candles = await fetch_candles(pair)
            action = analyze_and_decide(pair, candles)
            
            if SIMULATION and action in ["BUY", "SELL"]:
                current_price = float(candles[-1].close)
                simulate_trade(pair, action, current_price)
                
        except Exception as e:
            print(f"⚠️ Error processing {pair}: {e}", flush=True)
    
    print_summary()

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
