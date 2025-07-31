import os
import sys
import asyncio
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from coinbase.rest import RESTClient

# Import strategy and config modules
from strategy import should_buy, should_sell, rsi, enhanced_should_buy, enhanced_should_sell, get_atr_stop_loss
from config import CONFIG

# === Position Tracking Class ===
class PositionTracker:
    def __init__(self):
        self.positions = {}  # {pair: {"entry_price": price, "quantity": qty, "timestamp": time}}
        self.trade_history = []
        self.total_pnl = 0.0
        
    def open_position(self, pair, price, quantity=None):
        """Open a new position"""
        if quantity is None:
            quantity = 10.00 / price  # $10 worth of crypto
            
        self.positions[pair] = {
            "entry_price": price,
            "quantity": quantity,
            "timestamp": datetime.now(timezone.utc),
            "unrealized_pnl": 0.0
        }
        print(f"🟢 OPENED POSITION: {pair} | Entry: ${price:.6f} | Qty: {quantity:.6f}", flush=True)
        
    def close_position(self, pair, exit_price, reason="SELL"):
        """Close an existing position and calculate PnL"""
        if pair not in self.positions:
            print(f"⚠️ No position to close for {pair}", flush=True)
            return 0.0
            
        position = self.positions[pair]
        entry_price = position["entry_price"]
        quantity = position["quantity"]
        
        # Calculate PnL
        pnl_usd = (exit_price - entry_price) * quantity
        pnl_percent = ((exit_price - entry_price) / entry_price) * 100
        
        # Record trade
        trade = {
            "pair": pair,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "quantity": quantity,
            "pnl_usd": pnl_usd,
            "pnl_percent": pnl_percent,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc)
        }
        
        self.trade_history.append(trade)
        self.total_pnl += pnl_usd
        
        # Remove from open positions
        del self.positions[pair]
        
        # Log the trade
        profit_emoji = "💰" if pnl_usd > 0 else "📉"
        print(f"🔴 CLOSED POSITION: {pair} | Exit: ${exit_price:.6f} | {profit_emoji} PnL: ${pnl_usd:.2f} ({pnl_percent:+.2f}%)", flush=True)
        
        return pnl_usd
        
    def update_unrealized_pnl(self, pair, current_price):
        """Update unrealized PnL for open position"""
        if pair in self.positions:
            position = self.positions[pair]
            entry_price = position["entry_price"]
            quantity = position["quantity"]
            unrealized_pnl = (current_price - entry_price) * quantity
            position["unrealized_pnl"] = unrealized_pnl
            
    def get_position_status(self, pair):
        """Get current position status"""
        return self.positions.get(pair, None)
        
    def print_summary(self):
        """Print trading summary"""
        open_positions = len(self.positions)
        total_trades = len(self.trade_history)
        winning_trades = len([t for t in self.trade_history if t["pnl_usd"] > 0])
        
        print(f"\n📊 TRADING SUMMARY:", flush=True)
        print(f"   💼 Open Positions: {open_positions}", flush=True)
        print(f"   📈 Total Trades: {total_trades}", flush=True)
        print(f"   🎯 Winning Trades: {winning_trades}/{total_trades}" + (f" ({winning_trades/total_trades*100:.1f}%)" if total_trades > 0 else ""), flush=True)
        print(f"   💰 Total PnL: ${self.total_pnl:.2f}", flush=True)
        
        if self.positions:
            print(f"   📋 Open Positions:", flush=True)
            for pair, pos in self.positions.items():
                unrealized = pos.get("unrealized_pnl", 0)
                print(f"      {pair}: ${pos['entry_price']:.6f} | Unrealized: ${unrealized:.2f}", flush=True)

# Initialize position tracker
position_tracker = PositionTracker()

# === DEBUG PRINTS: Confirm startup and env ===
print("✅ bot.py loaded", flush=True)

load_dotenv()  # Safe even on Render; does nothing if .env isn't found

API_KEY = os.getenv("COINBASE_API_KEY_ID")
API_SECRET = os.getenv("COINBASE_API_PRIVATE_KEY")

print(f"🔑 COINBASE_API_KEY_ID: {API_KEY}", flush=True)
print(f"🔐 COINBASE_API_PRIVATE_KEY: {API_SECRET[:30]}..." if API_SECRET else "🔐 COINBASE_API_PRIVATE_KEY: None", flush=True)

# === Raise error if missing ===
if not API_KEY or not API_SECRET:
    raise ValueError("Missing API credentials. Check your .env file or Render environment.")

# === Initialize REST Client with ECDSA Key Support ===
import json
from io import StringIO

client = None

# Try Secret File First (Render Secret Files)
if os.path.exists('cdp_api_key.json'):
    print("🔍 Found local cdp_api_key.json file, reading it", flush=True)
    try:
        with open('cdp_api_key.json', 'r') as f:
            local_key_data = json.load(f)
        
        print(f"🔍 Local file structure detected", flush=True)
        print(f"🔍 Key type: {'ECDSA' if local_key_data.get('privateKey', '').startswith('-----BEGIN EC PRIVATE KEY-----') else 'Ed25519' if 'ed25519:' in local_key_data.get('privateKey', '') else 'Unknown'}", flush=True)
        
        # The new ECDSA format should work directly with the SDK
        key_file_obj = StringIO(json.dumps(local_key_data))
        client = RESTClient(key_file=key_file_obj)
        print("✅ REST client initialized successfully using local ECDSA key file", flush=True)
        
    except Exception as e:
        print(f"❌ Error with local file: {e}", flush=True)
        client = None

# Try Environment Variables if no secret file or file failed
if client is None:
    print("📂 Using environment variables for REST client", flush=True)
    try:
        # Construct the proper JSON structure for ECDSA keys
        key_file_content = {
            "name": API_KEY,
            "privateKey": API_SECRET
        }
        
        print(f"🔍 Environment key type: {'ECDSA' if API_SECRET.startswith('-----BEGIN EC PRIVATE KEY-----') else 'Ed25519' if 'ed25519:' in API_SECRET else 'Unknown'}", flush=True)
        print(f"🔍 Key name format: {'Organization format' if API_KEY.startswith('organizations/') else 'Simple ID'}", flush=True)
        
        # Create in-memory file object
        key_file_obj = StringIO(json.dumps(key_file_content))
        
        # Try different initialization approaches
        try:
            client = RESTClient(key_file=key_file_obj)
            print("✅ REST client initialized with key_file approach", flush=True)
        except Exception as key_file_error:
            print(f"❌ key_file approach failed: {key_file_error}", flush=True)
            
            # Try direct API key approach as fallback
            try:
                client = RESTClient(api_key=API_KEY, api_secret=API_SECRET)
                print("✅ REST client initialized with direct API key approach", flush=True)
            except Exception as direct_error:
                print(f"❌ Direct API approach also failed: {direct_error}", flush=True)
                raise Exception(f"All client initialization methods failed. key_file: {key_file_error}, direct: {direct_error}")
        
    except Exception as e:
        print(f"❌ Error initializing REST client: {e}", flush=True)
        raise

# Verify client is ready
if client is None:
    raise Exception("Failed to initialize REST client with any method")

print("🎯 REST client ready for trading operations", flush=True)

# Test the client with a simple API call
print("🧪 Testing REST client with a simple API call...", flush=True)
try:
    # Try to get account info or list products to verify the connection
    test_result = client.get_products(limit=1)
    print(f"✅ REST client test successful - API connection verified", flush=True)
except Exception as test_error:
    print(f"❌ REST client test failed: {test_error}", flush=True)
    print("🔧 This suggests an issue with your API credentials or key format", flush=True)
    print("💡 Check that your Render environment variables match your ECDSA key format", flush=True)
    raise Exception(f"Client test failed: {test_error}")

# === Config ===
GRANULARITY = "FIVE_MINUTE"  # Changed from ONE_MINUTE for better signal quality with multi-filter strategy
TRADING_PAIRS = os.getenv("TRADE_PAIRS", "XLM-USD,XRP-USD,LINK-USD,OP-USD,ARB-USD").split(",")
LOOP_SECONDS = int(os.getenv("TRADE_LOOP_SECONDS", "120"))
SIMULATION = os.getenv("SIMULATION", "true").lower() == "true"

print(f"📋 Trading pairs: {TRADING_PAIRS}", flush=True)
print(f"⚙️ Loop interval: {LOOP_SECONDS} seconds", flush=True)
print(f"🧪 Simulation mode: {SIMULATION}", flush=True)

print("🚀 Advanced Coinbase Trading Bot with Multi-Filter Strategy", flush=True)
print("📊 Using 5-minute candles for optimal signal quality:", flush=True)
print("   • Smoother RSI + MACD = fewer false signals", flush=True)  
print("   • Better trend confirmation with 50 EMA", flush=True)
print("   • Improved ATR calculations for stop-loss", flush=True)
print("   • Reduced noise while capturing intraday moves", flush=True)

if not SIMULATION:
    print("🚨 WARNING: LIVE TRADING MODE ENABLED! 🚨", flush=True)
    print("💰 Real money will be used for trades!", flush=True)
    print("📊 Each BUY order will use $10 USD", flush=True)
    print("⚠️ Make sure you have sufficient funds in your account", flush=True)
else:
    print("✅ Safe mode: Only analyzing signals, no real trades", flush=True)

# === Fetch candle data ===
def fetch_candles(pair):
    """Fetch candle data for the specified pair"""
    try:
        now = datetime.now(timezone.utc)
        # Fetch 5 hours of 5-minute candles (60 candles) for better indicator accuracy
        start = now - timedelta(hours=5)
        
        # Convert to Unix timestamps (seconds since epoch)
        start_unix = int(start.timestamp())
        end_unix = int(now.timestamp())
        
        print(f"🕐 Fetching {GRANULARITY} candles for {pair} from {start.isoformat()} to {now.isoformat()}", flush=True)
        print(f"   📊 Unix timestamps: start={start_unix}, end={end_unix}, granularity={GRANULARITY}", flush=True)
        
        candles = client.get_candles(  # Remove await
            product_id=pair,
            start=start_unix,
            end=end_unix,
            granularity=GRANULARITY
        )
        return candles
    except Exception as e:
        print(f"❌ Error fetching candles for {pair}: {e}", flush=True)
        raise

# === Analyze and execute trading strategy ===
def analyze_and_trade(pair, candles):
    """Analyze candles and execute trading logic with enhanced filters"""
    try:
        config = CONFIG.get(pair, CONFIG["DEFAULT"])
        take_profit_1 = config["take_profit_1"]
        take_profit_2 = config["take_profit_2"] 
        rebuy_zone = config["rebuy_zone"]
        stop_loss_pct = config["stop_loss_pct"]
        
        # Get current price from latest candle
        if hasattr(candles, 'candles') and candles.candles:
            candle_data = candles.candles
        else:
            candle_data = candles
            
        current_price = float(candle_data[-1].close)
        
        # Get current position
        current_position = position_tracker.get_position_status(pair)
        action = "HOLD"
        reason = ""
        
        if current_position is None:
            # No position - use enhanced buy logic
            can_buy, buy_reason = enhanced_should_buy(candles, current_price)
            
            if can_buy:
                # Additional rebuy zone check from config
                if current_price <= rebuy_zone:
                    action = "BUY"
                    reason = f"Enhanced buy signal: {buy_reason}"
                else:
                    action = "HOLD"
                    reason = f"Price above rebuy zone: ${current_price:.6f} > ${rebuy_zone:.6f}"
            else:
                action = "HOLD" 
                reason = f"Buy filters failed: {buy_reason}"
                
        else:
            # Have position - update unrealized PnL and check sell conditions
            position_tracker.update_unrealized_pnl(pair, current_price)
            unrealized = current_position["unrealized_pnl"]
            entry_price = current_position["entry_price"]
            
            # Enhanced sell logic
            should_sell_enhanced, sell_action, sell_reason = enhanced_should_sell(candles, current_price, entry_price)
            
            if should_sell_enhanced:
                action = sell_action
                reason = sell_reason
            else:
                # Check traditional take profit levels
                if current_price >= take_profit_2:
                    action = "SELL (TP2)"
                    reason = f"Take profit 2 reached: ${current_price:.6f} >= ${take_profit_2:.6f}"
                elif current_price >= take_profit_1:
                    action = "SELL (TP1)" 
                    reason = f"Take profit 1 reached: ${current_price:.6f} >= ${take_profit_1:.6f}"
                else:
                    action = "HOLD"
                    reason = sell_reason
                    
            # Show position status
            pnl_percent = ((current_price - entry_price) / entry_price) * 100
            pnl_emoji = "📈" if unrealized >= 0 else "📉"
            
            # Show ATR stop loss level
            atr_stop = get_atr_stop_loss(candles, entry_price)
            stop_info = f" | ATR Stop: ${atr_stop:.6f}" if atr_stop else ""
            
            print(f"   💼 Position: Entry ${entry_price:.6f} | {pnl_emoji} Unrealized: ${unrealized:.2f} ({pnl_percent:+.2f}%){stop_info}", flush=True)
        
        print(f"📊 {pair}: ${current_price:.6f} | Action: {action}", flush=True)
        print(f"   🔍 Reason: {reason}", flush=True)
        
        # Execute trades
        if SIMULATION:
            if action == "BUY":
                position_tracker.open_position(pair, current_price)
                print(f"🧪 SIMULATION - BUY executed for {pair} at ${current_price:.6f}", flush=True)
            elif action.startswith("SELL"):
                pnl = position_tracker.close_position(pair, current_price, reason=action)
                print(f"🧪 SIMULATION - {action} executed for {pair} at ${current_price:.6f}", flush=True)
        else:
            # Real trading execution
            if action == "BUY":
                print(f"🚨 LIVE TRADING - BUY signal for {pair} at ${current_price:.6f}", flush=True)
                try:
                    order_result = client.market_order_buy(
                        client_order_id=f"buy_{pair}_{int(datetime.now().timestamp())}",
                        product_id=pair,
                        quote_size="10.00"
                    )
                    print(f"✅ BUY ORDER PLACED: {order_result.order_id}", flush=True)
                    position_tracker.open_position(pair, current_price)
                    
                except Exception as e:
                    print(f"❌ BUY ORDER FAILED for {pair}: {e}", flush=True)
                    
            elif action.startswith("SELL"):
                print(f"🚨 LIVE TRADING - {action} signal for {pair} at ${current_price:.6f}", flush=True)
                try:
                    current_position = position_tracker.get_position_status(pair)
                    if current_position:
                        quantity = current_position["quantity"]
                        order_result = client.market_order_sell(
                            client_order_id=f"sell_{pair}_{int(datetime.now().timestamp())}",
                            product_id=pair,
                            base_size=str(quantity)
                        )
                        print(f"✅ SELL ORDER PLACED: {order_result.order_id}", flush=True)
                        position_tracker.close_position(pair, current_price, reason=action)
                    else:
                        print(f"⚠️ No position to sell for {pair}", flush=True)
                        
                except Exception as e:
                    print(f"❌ SELL ORDER FAILED for {pair}: {e}", flush=True)
                    
    except Exception as e:
        print(f"📊 {pair}: Error in analysis - {e}", flush=True)

# === Bot execution ===
async def run_bot():
    """Run the bot for all trading pairs"""
    for pair in TRADING_PAIRS:
        try:
            print(f"\n🔄 Processing {pair}...", flush=True)
            candles = fetch_candles(pair)
            analyze_and_trade(pair, candles) # Remove await
        except Exception as e:
            print(f"⚠️ Error processing {pair}: {e}", flush=True)
    
    # Print trading summary after analyzing all pairs
    position_tracker.print_summary()

# === Main loop ===
async def main_loop():
    """Main trading loop"""
    print("🔄 Starting trading loop...", flush=True)
    while True:
        try:
            print(f"\n⏱️ Running bot at {datetime.now(timezone.utc).isoformat()}", flush=True)
            await run_bot()
            print(f"⏸️ Waiting {LOOP_SECONDS} seconds until next analysis...", flush=True)
            await asyncio.sleep(LOOP_SECONDS)
        except KeyboardInterrupt:
            print("\n🛑 Bot stopped by user", flush=True)
            break
        except Exception as e:
            print(f"❌ Error in main loop: {e}", flush=True)
            print(f"🔄 Retrying in {LOOP_SECONDS} seconds...", flush=True)
            await asyncio.sleep(LOOP_SECONDS)

# === Entry point ===
if __name__ == "__main__":
    print("🚀 Launching bot.py...", flush=True)
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        print("\n👋 Bot shutdown completed", flush=True)
    except Exception as e:
        print(f"💥 Fatal error: {e}", flush=True)
        sys.exit(1)
