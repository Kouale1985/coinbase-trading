import os
import sys
import asyncio
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import json
from io import StringIO
import base64
import subprocess
import tempfile
import time

from coinbase.rest import RESTClient
from trading_strategy import enhanced_should_buy, enhanced_should_sell, execute_sell_action
from indicators import calculate_all_indicators
from portfolio import PositionTracker, SignalThrottle
from constants import *

# === Dashboard Data Export Functions ===
def ensure_data_directory():
    """Ensure data directory exists for dashboard exports"""
    if not os.path.exists('data'):
        os.makedirs('data')

def export_portfolio_data(position_tracker, current_prices=None):
    """Export portfolio summary data with encoding"""
    # Calculate position values using current prices if available
    if current_prices:
        position_value = sum(
            current_prices.get(pair, pos["entry_price"]) * pos["total_quantity"] 
            for pair, pos in position_tracker.positions.items()
        )
        total_balance = position_tracker.calculate_total_balance(current_prices)
    else:
        position_value = sum(
            pos["entry_price"] * pos["total_quantity"] for pos in position_tracker.positions.values()
        )
        total_balance = position_tracker.calculate_total_balance()
    
    portfolio_data = {
        "starting_balance": STARTING_BALANCE_USD,
        "current_cash": position_tracker.cash_balance,
        "position_value": position_value,
        "total_balance": total_balance,
        "total_return_pct": ((total_balance - STARTING_BALANCE_USD) / STARTING_BALANCE_USD) * 100,
        "realized_pnl": position_tracker.total_pnl,
        "open_positions": len(position_tracker.positions),
        "max_positions": MAX_POSITIONS,
        "total_trades": len(position_tracker.trade_history),
        "winning_trades": len([t for t in position_tracker.trade_history if t.get('pnl_usd', 0) > 0]),
        "portfolio_exposure": (position_value / total_balance) * 100 if total_balance > 0 else 0,
        "max_exposure": MAX_EXPOSURE * 100,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    try:
        ensure_data_directory()
        # Encode the data
        json_str = json.dumps(portfolio_data, indent=2)
        encoded_data = base64.b64encode(json_str.encode()).decode()
        
        # Use obscure filename
        with open('data/p_data.json', 'w') as f:
            json.dump(portfolio_data, f, indent=2)
        print(f"📊 Portfolio data exported and encoded", flush=True)
    except Exception as e:
        print(f"⚠️ Error exporting portfolio data: {e}", flush=True)

def export_positions_data(position_tracker, current_prices=None):
    """Export current positions for dashboard"""
    ensure_data_directory()
    
    positions_data = []
    for pair, position in position_tracker.positions.items():
        entry_value = position["entry_price"] * position["total_quantity"]
        current_price = current_prices.get(pair, position["entry_price"]) if current_prices else position["entry_price"]
        position_value = current_price * position["remaining_quantity"]
        unrealized_pnl = position_value - (position["entry_price"] * position["remaining_quantity"])
        
        positions_data.append({
            "pair": pair,
            "entry_price": position["entry_price"],
            "current_price": current_price,
            "total_quantity": position["total_quantity"],
            "remaining_quantity": position["remaining_quantity"],
            "entry_value": entry_value,
            "position_value": position_value,
            "unrealized_pnl": unrealized_pnl,
            "entry_time": position.get("timestamp", "").isoformat() if hasattr(position.get("timestamp", ""), 'isoformat') else str(position.get("timestamp", "")),
            "tier_1_sold": position.get("tier_1_sold", False),
            "tier_2_sold": position.get("tier_2_sold", False),
            "trailing_stop_active": position.get("trailing_stop_active", False),
            "trailing_stop_price": position.get("trailing_stop_price", 0)
        })
    
    with open('data/positions.json', 'w') as f:
        json.dump(positions_data, f, indent=2)

def export_signals_data(signals_data):
    """Export current market signals for dashboard"""
    ensure_data_directory()
    
    with open('data/signals.json', 'w') as f:
        json.dump(signals_data, f, indent=2)

def export_trade_history(position_tracker):
    """Export trade history for dashboard"""
    ensure_data_directory()
    
    # Convert trade history with proper timestamp formatting
    formatted_history = []
    for trade in position_tracker.trade_history:
        formatted_trade = trade.copy()
        if hasattr(trade.get('timestamp', ''), 'isoformat'):
            formatted_trade['timestamp'] = trade['timestamp'].isoformat()
        formatted_history.append(formatted_trade)
    
    with open('data/trade_history.json', 'w') as f:
        json.dump(formatted_history, f, indent=2)

def commit_data_to_github():
    """
    Commit the exported data files to GitHub
    This allows Streamlit to read the data from GitHub raw URLs
    """
    try:
        # Configure git if not already done
        subprocess.run(['git', 'config', 'user.email', 'bot@tradingbot.com'], 
                      capture_output=True, text=True, check=False)
        subprocess.run(['git', 'config', 'user.name', 'Trading Bot'], 
                      capture_output=True, text=True, check=False)
        
        # Configure git remote with token for pushing
        github_token = os.getenv('GITHUB_TOKEN')
        if github_token:
            # Set up remote origin with authentication
            remote_url = f"https://{github_token}@github.com/Kouale1985/dashboard.git"
            
            # Remove existing origin if it exists, then add new one
            subprocess.run(['git', 'remote', 'remove', 'origin'], 
                          capture_output=True, text=True, check=False)
            subprocess.run(['git', 'remote', 'add', 'origin', remote_url], 
                          capture_output=True, text=True, check=False)
            
            # Ensure we're on main branch and sync with remote
            subprocess.run(['git', 'checkout', '-B', 'main'], 
                          capture_output=True, text=True, check=False)
            print("📤 Configured for force push to override remote conflicts")
            print(f"🔧 Git remote configured with GitHub token")
        
        # Add the data files (create directory first if needed)
        if os.path.exists('data'):
            subprocess.run(['git', 'add', 'data/'], capture_output=True, text=True, check=True)
        else:
            print("📁 Data directory doesn't exist yet, skipping git add")
        
        # Create commit message with timestamp
        now = datetime.now(timezone.utc)
        commit_msg = f"🤖 Bot data update: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        
        # Commit the changes
        result = subprocess.run(['git', 'commit', '-m', commit_msg], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            # Push to GitHub (force push to resolve conflicts)
            push_result = subprocess.run(['git', 'push', '--force', 'origin', 'main'], capture_output=True, text=True)
            if push_result.returncode == 0:
                print(f"✅ Data successfully committed and pushed to GitHub")
                return True
            else:
                print(f"⚠️ Git push failed: {push_result.stderr}")
                print(f"📊 Continuing with local data export (dashboard will use cached data)")
                return False
        else:
            # No changes to commit (data unchanged)
            if "nothing to commit" in result.stdout:
                print("📊 No data changes since last commit")
                return True
            else:
                print(f"⚠️ Git commit failed: {result.stderr}")
                return False
                
    except subprocess.CalledProcessError as e:
        print(f"❌ Git operation failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Error in GitHub sync: {e}")
        return False

def get_real_account_balance():
    """Query actual USD balance from Coinbase account"""
    try:
        accounts = client.get_accounts()
        if hasattr(accounts, 'accounts'):
            for account in accounts.accounts:
                if account.currency == "USD":
                    return float(account.available_balance.value)
        else:
            # Handle different response format
            for account in accounts:
                if account.get('currency') == "USD":
                    return float(account.get('available_balance', {}).get('value', 0))
        
        print("⚠️ USD account not found, using default balance", flush=True)
        return STARTING_BALANCE_USD
    except Exception as e:
        print(f"⚠️ Error fetching real account balance: {e}", flush=True)
        print("📊 Using configured starting balance instead", flush=True)
        return STARTING_BALANCE_USD

# Initialize position tracker and signal throttle
position_tracker = PositionTracker()
signal_throttle = SignalThrottle(throttle_minutes=SIGNAL_THROTTLE_MINUTES)

# === DEBUG PRINTS: Confirm startup and env ===
print("✅ bot.py loaded with modular structure", flush=True)

load_dotenv()  # Safe even on Render; does nothing if .env isn't found

API_KEY = os.getenv("COINBASE_API_KEY_ID")
API_SECRET = os.getenv("COINBASE_API_PRIVATE_KEY")

print(f"🔑 COINBASE_API_KEY_ID: {API_KEY}", flush=True)
print(f"🔐 COINBASE_API_PRIVATE_KEY: {API_SECRET[:30]}..." if API_SECRET else "🔐 COINBASE_API_PRIVATE_KEY: None", flush=True)

# === Raise error if missing ===
if not API_KEY or not API_SECRET:
    raise ValueError("Missing API credentials. Check your .env file or Render environment.")

# === Initialize REST Client with ECDSA Key Support ===
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

# Allow environment override or use tier-1 default
TRADING_PAIRS = os.getenv("TRADE_PAIRS", ",".join(TIER_1_PAIRS)).split(",")

LOOP_SECONDS = int(os.getenv("TRADE_LOOP_SECONDS", str(LOOP_SECONDS_DEFAULT)))
SIMULATION = os.getenv("SIMULATION", "true").lower() == "true"

print(f"📋 Trading pairs ({len(TRADING_PAIRS)} total): {TRADING_PAIRS[:5]}..." if len(TRADING_PAIRS) > 5 else f"📋 Trading pairs: {TRADING_PAIRS}", flush=True)
print(f"⚙️ Loop interval: {LOOP_SECONDS} seconds", flush=True)
print(f"🧪 Simulation mode: {SIMULATION}", flush=True)

print("🚀 Advanced Coinbase Trading Bot with Dynamic ATR Strategy", flush=True)
print("📊 Using 5-minute candles with tiered exit system:", flush=True)
print("   • Dynamic ATR-based targets (no static configs)", flush=True)  
print("   • Tiered exits: 30% at TP1, 30% at TP2, 40% trailing", flush=True)
print("   • Professional risk management and position sizing", flush=True)
print("   • Improved error handling and modular structure", flush=True)

if not SIMULATION:
    print("🚨 WARNING: LIVE TRADING MODE ENABLED! 🚨", flush=True)
    print("💰 Real money will be used for trades!", flush=True)
    print("📊 Each BUY order will use calculated position size", flush=True)
    print("⚠️ Make sure you have sufficient funds in your account", flush=True)
    print("🔍 All trades will appear in your Coinbase account", flush=True)
    print("📱 Check Coinbase Pro → Orders & Portfolio tabs", flush=True)
else:
    print("✅ Safe mode: Only analyzing signals, no real trades", flush=True)

def fetch_current_price(pair):
    """Fetch real-time current price for more accurate analysis"""
    try:
        # Get current market data (real-time ticker)
        ticker = client.get_product(product_id=pair)
        if hasattr(ticker, 'price'):
            return float(ticker.price)
        elif hasattr(ticker, 'quote_increment'):
            # Fallback: use latest trade data
            trades = client.get_public_trades(product_id=pair, limit=1)
            if trades and len(trades.trades) > 0:
                return float(trades.trades[0].price)
    except Exception as e:
        print(f"⚠️ Error fetching current price for {pair}: {e}", flush=True)
    return None

# === Fetch candle data ===
def fetch_candles(pair):
    """Fetch candle data for the specified pair"""
    try:
        now = datetime.now(timezone.utc)
        # Fetch enough candles for proper indicator initialization
        start = now - timedelta(minutes=CANDLE_FETCH_MINUTES)
        
        # Convert to Unix timestamps (seconds since epoch)
        start_unix = int(start.timestamp())
        end_unix = int(now.timestamp())
        
        print(f"🕐 Fetching {GRANULARITY} candles for {pair} from {start.isoformat()} to {now.isoformat()}", flush=True)
        
        candles = client.get_candles(
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
    """Analyze candles and execute trading logic with dynamic ATR targets"""
    try:
        # Get current price from latest candle
        if hasattr(candles, 'candles') and candles.candles:
            candle_data = candles.candles
        else:
            candle_data = candles
            
        # Use real-time price if available, fallback to candle close
        real_time_price = fetch_current_price(pair)
        current_price = real_time_price if real_time_price else float(candle_data[-1].close)
        
        if real_time_price:
            print(f"💰 Using real-time price: ${current_price:.6f} (vs candle close: ${float(candle_data[-1].close):.6f})", flush=True)
        
        # Get current position
        current_position = position_tracker.get_position_status(pair)
        action = "HOLD"
        reason = ""
        
        if current_position is None:
            # No position - use enhanced buy logic with dynamic targets
            can_buy, buy_reason = enhanced_should_buy(candles, pair, current_price)
            
            if can_buy:
                # Check signal throttling before proceeding
                if not signal_throttle.can_signal(pair):
                    throttle_status = signal_throttle.get_throttle_status(pair)
                    action = "HOLD"
                    reason = f"Signal throttled: {throttle_status} (prevents overtrading)"
                else:
                    action = "BUY"
                    reason = f"Enhanced buy signal: {buy_reason}"
                    # Record the signal to start throttle timer
                    signal_throttle.record_signal(pair)
            else:
                action = "HOLD" 
                reason = f"Buy filters failed: {buy_reason}"
                
        else:
            # Have position - update and check sell conditions with new tiered system
            entry_price = current_position["entry_price"]
            
            # Enhanced sell logic with tiered exits
            should_sell_enhanced, sell_action, sell_reason = enhanced_should_sell(
                candles, current_price, entry_price, position_tracker, pair
            )
            
            if should_sell_enhanced:
                action = sell_action
                reason = sell_reason
            else:
                action = "HOLD"
                reason = sell_reason
                    
            # Show position status
            remaining_qty = current_position.get("remaining_quantity", current_position.get("quantity", 0))
            unrealized = current_position.get("unrealized_pnl", 0)
            pnl_percent = ((current_price - entry_price) / entry_price) * 100
            pnl_emoji = "📈" if unrealized >= 0 else "📉"
            
            tier_status = ""
            if current_position.get("tier_1_sold"):
                tier_status += "T1✅ "
            if current_position.get("tier_2_sold"):
                tier_status += "T2✅ "
            if current_position.get("trailing_stop_active"):
                tier_status += f"Trail@${current_position.get('trailing_stop_price', 0):.6f}"
            
            print(f"   💼 Position: Entry ${entry_price:.6f} | Remaining: {remaining_qty:.6f} | {pnl_emoji} PnL: ${unrealized:.2f} ({pnl_percent:+.2f}%)", flush=True)
            if tier_status:
                print(f"   🎯 Status: {tier_status}", flush=True)
        
        print(f"📊 {pair}: ${current_price:.6f} | Action: {action}", flush=True)
        print(f"   🔍 Reason: {reason}", flush=True)
        
        # Execute trades
        if SIMULATION:
            if action == "BUY":
                # Get indicators for position sizing
                indicators = calculate_all_indicators(candle_data)
                current_atr = indicators.get('atr')
                
                success = position_tracker.open_position(pair, current_price, current_atr)
                if success:
                    print(f"🧪 SIMULATION - BUY executed for {pair} at ${current_price:.6f}", flush=True)
                    
            elif action.startswith("TIER") or action.startswith("SELL"):
                pnl = execute_sell_action(action, pair, current_price, position_tracker)
                print(f"🧪 SIMULATION - {action} executed for {pair} at ${current_price:.6f}", flush=True)
        else:
            # Real trading execution
            if action == "BUY":
                print(f"🚨 LIVE TRADING - BUY signal for {pair} at ${current_price:.6f}", flush=True)
                try:
                    # Get indicators for position sizing
                    indicators = calculate_all_indicators(candle_data)
                    current_atr = indicators.get('atr')
                    
                    # Calculate position size using portfolio management
                    quantity, sizing_reason = position_tracker.calculate_position_size(current_price, current_atr)
                    
                    if quantity <= 0:
                        print(f"⚠️ Cannot place order: {sizing_reason}", flush=True)
                    else:
                        trade_value = quantity * current_price
                        order_result = client.market_order_buy(
                            client_order_id=f"buy_{pair}_{int(datetime.now().timestamp())}",
                            product_id=pair,
                            quote_size=str(trade_value)
                        )
                        print(f"✅ BUY ORDER PLACED: {order_result.order.order_id}", flush=True)
                        position_tracker.open_position(pair, current_price, current_atr)
                    
                except Exception as e:
                    print(f"❌ BUY ORDER FAILED for {pair}: {e}", flush=True)
                    
            elif action.startswith("TIER") or action.startswith("SELL"):
                print(f"🚨 LIVE TRADING - {action} signal for {pair} at ${current_price:.6f}", flush=True)
                try:
                    current_position = position_tracker.get_position_status(pair)
                    if current_position:
                        if action.startswith("TIER"):
                            # Execute tiered exit
                            pnl = execute_sell_action(action, pair, current_price, position_tracker)
                            print(f"✅ {action} executed with PnL: ${pnl:.2f}", flush=True)
                        else:
                            # Full exit
                            remaining_qty = current_position.get("remaining_quantity", current_position.get("quantity", 0))
                            order_result = client.market_order_sell(
                                client_order_id=f"sell_{pair}_{int(datetime.now().timestamp())}",
                                product_id=pair,
                                base_size=str(remaining_qty)
                            )
                            print(f"✅ SELL ORDER PLACED: {order_result.order.order_id}", flush=True)
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
    signals_data = []
    
    for pair in TRADING_PAIRS:
        try:
            print(f"\n🔄 Processing {pair}...", flush=True)
            candles = fetch_candles(pair)
            
            # Collect signal data for dashboard
            if candles and hasattr(candles, 'candles') and candles.candles:
                candle_data = candles.candles
                # Use real-time price for dashboard data too
                real_time_price = fetch_current_price(pair)
                current_price = real_time_price if real_time_price else float(candle_data[-1].close)
                
                # Get technical indicators
                indicators = calculate_all_indicators(candle_data)
                
                # Get buy/sell analysis
                can_buy, buy_reason = enhanced_should_buy(candles, pair, current_price)
                throttle_status = signal_throttle.get_throttle_status(pair)
                
                signal_data = {
                    "pair": pair,
                    "price": current_price,
                    "rsi": indicators.get('rsi'),
                    "ema_50": indicators.get('ema_50'),
                    "ema_uptrend": bool(indicators.get('ema_50') and current_price > indicators.get('ema_50')),
                    "macd_line": indicators.get('macd_line'),
                    "signal_line": indicators.get('signal_line'),
                    "macd_bullish": bool(indicators.get('macd_line') and indicators.get('signal_line') and indicators.get('macd_line') > indicators.get('signal_line')),
                    "atr": indicators.get('atr'),
                    "volatility_ratio": indicators.get('atr') / current_price if indicators.get('atr') else None,
                    "can_buy": bool(can_buy),
                    "buy_reason": buy_reason,
                    "throttle_status": throttle_status,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                signals_data.append(signal_data)
            
            analyze_and_trade(pair, candles)
        except Exception as e:
            print(f"⚠️ Error processing {pair}: {e}", flush=True)
    
    # Export all data for dashboard
    try:
        # Collect current prices for accurate portfolio valuation
        current_prices = {signal["pair"]: signal["price"] for signal in signals_data}
        
        export_portfolio_data(position_tracker, current_prices)
        export_positions_data(position_tracker, current_prices)
        export_signals_data(signals_data)
        export_trade_history(position_tracker)
        commit_data_to_github()
    except Exception as e:
        print(f"⚠️ Error exporting dashboard data: {e}", flush=True)
    
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
    print("🚀 Launching modular trading bot...", flush=True)
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        print("\n👋 Bot shutdown completed", flush=True)
    except Exception as e:
        print(f"💥 Fatal error: {e}", flush=True)
        sys.exit(1)