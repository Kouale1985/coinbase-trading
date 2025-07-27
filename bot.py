import asyncio
import os
import time
import pandas as pd
from dotenv import load_dotenv
from config import CONFIG
from coinbase.rest import MarketDataAPI
from coinbase.auth import APIKeyConfig
from coinbase.utils import calculate_macd, calculate_rsi, calculate_atr

load_dotenv()

# Load environment variables
SIMULATION = os.getenv("SIMULATION", "true").lower() == "true"
TRADE_PAIRS = os.getenv("TRADE_PAIRS", "XLM-USD,XRP-USD").split(",")
LOOP_INTERVAL = int(os.getenv("TRADE_LOOP_SECONDS", 120))

# API Key config for CDP (Ed25519)
api_key_id = os.getenv("COINBASE_API_KEY_ID")
private_key = os.getenv("COINBASE_API_PRIVATE_KEY")
auth = APIKeyConfig(api_key_id=api_key_id, private_key=private_key)

# Market Data API
md = MarketDataAPI(auth=auth)

# Logging
LOG_FILE = "trades.csv"
if not os.path.exists(LOG_FILE):
    pd.DataFrame(columns=["timestamp", "pair", "action", "price", "signal"]).to_csv(LOG_FILE, index=False)

def log_trade(pair, action, price, signal):
    ts = pd.Timestamp.utcnow().isoformat()
    row = {"timestamp": ts, "pair": pair, "action": action, "price": price, "signal": signal}
    df = pd.DataFrame([row])
    df.to_csv(LOG_FILE, mode="a", header=False, index=False)
    print(f"[{ts}] {pair}: {action.upper()} at ${price:.4f} | Signal: {signal}")

async def analyze_and_trade(pair):
    try:
        candles = md.get_candles_product_trades(product_id=pair, granularity="ONE_MINUTE")
        if not candles or "candles" not in candles:
            print(f"No data for {pair}")
            return

        closes = [float(c["close"]) for c in reversed(candles["candles"])]
        highs = [float(c["high"]) for c in reversed(candles["candles"])]
        lows = [float(c["low"]) for c in reversed(candles["candles"])]

        if len(closes) < 50:
            print(f"Not enough data for {pair}")
            return

        rsi = calculate_rsi(closes)
        macd, signal_line = calculate_macd(closes)
        atr = calculate_atr(highs, lows, closes)

        price = closes[-1]
        cfg = CONFIG[pair]
        signal = "HOLD"

        # ENTRY
        if rsi < 30 and macd > signal_line:
            signal = "BUY"
            log_trade(pair, "buy", price, signal)

        # EXIT - Take profit tier 1
        elif price >= cfg["take_profit_1"]:
            signal = "SELL (TP1)"
            log_trade(pair, "sell", price, signal)

        # EXIT - Take profit tier 2
        elif price >= cfg["take_profit_2"]:
            signal = "SELL (TP2)"
            log_trade(pair, "sell", price, signal)

        # EXIT - Stop loss
        elif price <= (1 - cfg["stop_loss_pct"]) * cfg["rebuy_zone"]:
            signal = "SELL (STOP)"
            log_trade(pair, "sell", price, signal)

        else:
            print(f"{pair} | Price: ${price:.4f} | RSI: {rsi:.2f} | MACD: {macd:.4f} | ATR: {atr:.4f}")

    except Exception as e:
        print(f"Error analyzing {pair}: {str(e)}")

async def main_loop():
    while True:
        print(f"\n🔁 Starting loop at {pd.Timestamp.utcnow().isoformat()} UTC")
        tasks = [analyze_and_trade(pair) for pair in TRADE_PAIRS]
        await asyncio.gather(*tasks)
        print(f"⏳ Sleeping {LOOP_INTERVAL} sec...\n")
        await asyncio.sleep(LOOP_INTERVAL)

if __name__ == "__main__":
    asyncio.run(main_loop())
