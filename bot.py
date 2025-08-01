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

from coinbase.rest import RESTClient
from strategy import should_buy, should_sell, rsi, enhanced_should_buy, enhanced_should_sell, get_atr_stop_loss, ema, macd, atr
from config import CONFIG

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
            current_prices.get(pair, pos["entry_price"]) * pos["quantity"] 
            for pair, pos in position_tracker.positions.items()
        )
        total_balance = position_tracker.calculate_total_balance(current_prices)
    else:
        position_value = sum(
            pos["entry_price"] * pos["quantity"] for pos in position_tracker.positions.values()
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
        "winning_trades": len([t for t in position_tracker.trade_history if t.get('pnl', 0) > 0]),
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
        entry_value = position["entry_price"] * position["quantity"]
        current_price = current_prices.get(pair, position["entry_price"]) if current_prices else position["entry_price"]
        position_value = current_price * position["quantity"]
        unrealized_pnl = position_value - entry_value
        
        positions_data.append({
            "pair": pair,
            "entry_price": position["entry_price"],
            "current_price": current_price,
            "quantity": position["quantity"],
            "entry_value": entry_value,
            "position_value": position_value,
            "unrealized_pnl": unrealized_pnl,
            "entry_time": position.get("timestamp", position.get("entry_time", ""))
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
    
    with open('data/trade_history.json', 'w') as f:
        json.dump(position_tracker.trade_history, f, indent=2)

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
            # Skip fetch to avoid conflicts - force push will override remote
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

# === Professional Portfolio Management Constants ===
STARTING_BALANCE_USD = 1000  # UPDATE THIS TO YOUR ACTUAL USD BALANCE
MAX_POSITIONS = 4                   # Don't hold more than 4 trades at once
MAX_EXPOSURE = 0.75                 # Use up to 75% of total balance
CASH_BUFFER = 0.25                  # Keep at least 25% cash free
MAX_PER_TRADE = 0.25                # No more than 25% per trade
MIN_TRADE_SIZE = 50                 # Don't enter trades smaller than this
RISK_PER_TRADE = 0.02               # 2% risk per trade for position sizing

# TODO: Add real account balance query
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

# === Position Tracking Class with Portfolio Management ===
class PositionTracker:
    def __init__(self):
        self.positions = {}  # {pair: {"entry_price": price, "quantity": qty, "timestamp": time}}
        self.trade_history = []
        self.total_pnl = 0.0
        self.cash_balance = STARTING_BALANCE_USD
        self.starting_balance = STARTING_BALANCE_USD
        
    def calculate_total_balance(self, current_prices=None):
        """Calculate total portfolio value (cash + positions)"""
        if current_prices is None:
            # Fallback to entry prices if current prices not provided
            position_value = sum(
                pos["entry_price"] * pos["quantity"] for pos in self.positions.values()
            )
        else:
            # Use current market prices for accurate portfolio value
            position_value = sum(
                current_prices.get(pair, pos["entry_price"]) * pos["quantity"] 
                for pair, pos in self.positions.items()
            )
        return self.cash_balance + position_value
        
    def calculate_position_size(self, price, atr_value=None):
        """
        Calculate optimal position size based on portfolio management rules
        """
        total_balance = self.calculate_total_balance()
        
        # Check max positions limit
        if len(self.positions) >= MAX_POSITIONS:
            return 0, "Max positions reached"
        
        # Calculate current exposure
        used_exposure = total_balance - self.cash_balance
        available_exposure = MAX_EXPOSURE * total_balance - used_exposure
        
        # Max allowed per trade
        max_trade_usd = min(available_exposure, MAX_PER_TRADE * total_balance)
        
        # Check minimum trade size
        if max_trade_usd < MIN_TRADE_SIZE:
            return 0, f"Trade size too small: ${max_trade_usd:.2f} < ${MIN_TRADE_SIZE}"
        
        # Check cash availability
        if max_trade_usd > self.cash_balance:
            max_trade_usd = self.cash_balance
        
        # Optional: ATR-based position sizing for risk management
        if atr_value and atr_value > 0:
            stop_loss_pct = 1.5 * atr_value / price
            if stop_loss_pct > 0:
                risk_usd = total_balance * RISK_PER_TRADE
                risk_based_position_usd = risk_usd / stop_loss_pct
                max_trade_usd = min(max_trade_usd, risk_based_position_usd)
        
        quantity = max_trade_usd / price
        return quantity, f"Position size: ${max_trade_usd:.2f} ({quantity:.6f} units)"
        
    def open_position(self, pair, price, atr_value=None):
        """Open a new position with professional position sizing"""
        quantity, reason = self.calculate_position_size(price, atr_value)
        
        if quantity <= 0:
            print(f"⚠️ Cannot open position for {pair}: {reason}", flush=True)
            return False
            
        trade_value = quantity * price
        
        # Check if we have enough cash
        if trade_value > self.cash_balance:
            print(f"⚠️ Insufficient cash for {pair}: Need ${trade_value:.2f}, have ${self.cash_balance:.2f}", flush=True)
            return False
            
        # Execute the trade
        self.positions[pair] = {
            "entry_price": price,
            "quantity": quantity,
            "entry_value": trade_value,
            "position_value": trade_value,  # Will be updated with current prices
            "timestamp": datetime.now(timezone.utc),
            "unrealized_pnl": 0.0
        }
        
        # Update cash balance
        self.cash_balance -= trade_value
        
        total_balance = self.calculate_total_balance()
        print(f"🟢 OPENED POSITION: {pair} | Entry: ${price:.6f} | Qty: {quantity:.6f} | Value: ${trade_value:.2f}", flush=True)
        print(f"   💰 Cash: ${self.cash_balance:.2f} | Total Balance: ${total_balance:.2f} | Positions: {len(self.positions)}/{MAX_POSITIONS}", flush=True)
        return True
        
    def close_position(self, pair, exit_price, reason="SELL"):
        """Close an existing position and calculate PnL"""
        if pair not in self.positions:
            print(f"⚠️ No position to close for {pair}", flush=True)
            return 0.0
            
        position = self.positions[pair]
        entry_price = position["entry_price"]
        quantity = position["quantity"]
        
        # Calculate sale proceeds
        sale_proceeds = exit_price * quantity
        
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
        
        # Update cash balance with sale proceeds
        self.cash_balance += sale_proceeds
        
        total_balance = self.calculate_total_balance()
        
        # Log the trade
        profit_emoji = "💰" if pnl_usd > 0 else "📉"
        print(f"🔴 CLOSED POSITION: {pair} | Exit: ${exit_price:.6f} | {profit_emoji} PnL: ${pnl_usd:.2f} ({pnl_percent:+.2f}%)", flush=True)
        print(f"   💰 Sale Proceeds: ${sale_proceeds:.2f} | Cash: ${self.cash_balance:.2f} | Total: ${total_balance:.2f}", flush=True)
        
        return pnl_usd
        
    def update_unrealized_pnl(self, pair, current_price):
        """Update unrealized PnL and position value for open position"""
        if pair in self.positions:
            position = self.positions[pair]
            entry_price = position["entry_price"]
            quantity = position["quantity"]
            position_value = current_price * quantity
            unrealized_pnl = (current_price - entry_price) * quantity
            
            position["position_value"] = position_value
            position["unrealized_pnl"] = unrealized_pnl
            
    def get_position_status(self, pair):
        """Get current position status"""
        return self.positions.get(pair, None)
        
    def print_summary(self):
        """Print comprehensive portfolio summary"""
        open_positions = len(self.positions)
        total_trades = len(self.trade_history)
        winning_trades = len([t for t in self.trade_history if t["pnl_usd"] > 0])
        
        total_balance = self.calculate_total_balance()
        position_value = total_balance - self.cash_balance
        cash_percentage = (self.cash_balance / total_balance) * 100 if total_balance > 0 else 0
        exposure_percentage = (position_value / total_balance) * 100 if total_balance > 0 else 0
        total_return = ((total_balance - self.starting_balance) / self.starting_balance) * 100
        
        print(f"\n📊 PORTFOLIO SUMMARY:", flush=True)
        print(f"   💰 Starting Balance: ${self.starting_balance:.2f}", flush=True)
        print(f"   💰 Current Cash: ${self.cash_balance:.2f} ({cash_percentage:.1f}%)", flush=True)
        print(f"   📈 Position Value: ${position_value:.2f} ({exposure_percentage:.1f}%)", flush=True)
        print(f"   💰 Total Balance: ${total_balance:.2f}", flush=True)
        print(f"   📊 Total Return: {total_return:+.2f}%", flush=True)
        print(f"   📈 Realized PnL: ${self.total_pnl:.2f}", flush=True)
        
        print(f"\n📊 TRADING STATISTICS:", flush=True)
        print(f"   💼 Open Positions: {open_positions}/{MAX_POSITIONS}", flush=True)
        print(f"   📈 Total Trades: {total_trades}", flush=True)
        print(f"   🎯 Winning Trades: {winning_trades}/{total_trades}" + (f" ({winning_trades/total_trades*100:.1f}%)" if total_trades > 0 else ""), flush=True)
        
        print(f"\n📊 RISK MANAGEMENT:", flush=True)
        print(f"   💰 Available Cash: ${self.cash_balance:.2f}", flush=True)
        print(f"   📊 Portfolio Exposure: {exposure_percentage:.1f}% (max {MAX_EXPOSURE*100:.0f}%)", flush=True)
        print(f"   📊 Max Per Trade: {MAX_PER_TRADE*100:.0f}% (${total_balance * MAX_PER_TRADE:.0f})", flush=True)
        print(f"   📊 Min Trade Size: ${MIN_TRADE_SIZE}", flush=True)
        
        if self.positions:
            print(f"\n📋 OPEN POSITIONS:", flush=True)
            for pair, pos in self.positions.items():
                unrealized = pos.get("unrealized_pnl", 0)
                position_value = pos["entry_price"] * pos["quantity"]
                percentage = (position_value / total_balance) * 100
                print(f"      {pair}: ${pos['entry_price']:.6f} | Value: ${position_value:.2f} ({percentage:.1f}%) | Unrealized: ${unrealized:.2f}", flush=True)

# === Signal Throttling Class ===
class SignalThrottle:
    def __init__(self, throttle_minutes=15):
        self.last_signals = {}  # pair -> timestamp
        self.throttle_seconds = throttle_minutes * 60
        
    def can_signal(self, pair):
        """Check if enough time has passed since last signal for this pair"""
        now = datetime.now(timezone.utc).timestamp()
        
        if pair not in self.last_signals:
            return True
            
        time_since_last = now - self.last_signals[pair]
        return time_since_last >= self.throttle_seconds
    
    def record_signal(self, pair):
        """Record that a signal was generated for this pair"""
        self.last_signals[pair] = datetime.now(timezone.utc).timestamp()
        
    def get_throttle_status(self, pair):
        """Get human-readable throttle status"""
        if pair not in self.last_signals:
            return "✅ Ready"
            
        now = datetime.now(timezone.utc).timestamp()
        time_since_last = now - self.last_signals[pair]
        time_remaining = self.throttle_seconds - time_since_last
        
        if time_remaining <= 0:
            return "✅ Ready"
        else:
            minutes_remaining = int(time_remaining / 60)
            return f"⏳ {minutes_remaining}m remaining"

# Initialize position tracker and signal throttle
position_tracker = PositionTracker()
signal_throttle = SignalThrottle(throttle_minutes=15)  # 15-minute throttle per pair

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

# Tier-1 High-Volume Cryptocurrency Pairs (Liquid, Less Manipulation Risk)
TIER_1_PAIRS = [
    "BTC-USD", "ETH-USD", "XRP-USD", "ADA-USD", "SOL-USD",
    "DOGE-USD", "DOT-USD", "AVAX-USD", "MATIC-USD", "LINK-USD",
    "UNI-USD", "LTC-USD", "ATOM-USD", "XLM-USD", "ALGO-USD",
    "VET-USD", "ICP-USD", "FIL-USD", "ETC-USD",  # Removed TRX-USD
    "OP-USD", "ARB-USD"  # Keep your current pairs
]

# Allow environment override or use tier-1 default
TRADING_PAIRS = os.getenv("TRADE_PAIRS", ",".join(TIER_1_PAIRS)).split(",")

LOOP_SECONDS = int(os.getenv("TRADE_LOOP_SECONDS", "120"))
SIMULATION = os.getenv("SIMULATION", "true").lower() == "true"

print(f"📋 Trading pairs ({len(TRADING_PAIRS)} total): {TRADING_PAIRS[:5]}..." if len(TRADING_PAIRS) > 5 else f"📋 Trading pairs: {TRADING_PAIRS}", flush=True)
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
    print("📊 Each BUY order will use calculated position size", flush=True)
    print("⚠️ Make sure you have sufficient funds in your account", flush=True)
    print("🔍 All trades will appear in your Coinbase account", flush=True)
    print("📱 Check Coinbase Pro → Orders & Portfolio tabs", flush=True)
else:
    print("✅ Safe mode: Only analyzing signals, no real trades", flush=True)

# === Fetch candle data ===
def fetch_candles(pair):
    """Fetch candle data for the specified pair"""
    try:
        now = datetime.now(timezone.utc)
        # Fetch 200+ candles for proper RSI initialization (1000 minutes = ~16.7 hours for 5-min candles)
        # This ensures proper Wilder's RSI smoothing that matches Coinbase UI
        start = now - timedelta(minutes=1000)
        
        # Convert to Unix timestamps (seconds since epoch)
        start_unix = int(start.timestamp())
        end_unix = int(now.timestamp())
        
        print(f"🕐 Fetching {GRANULARITY} candles for {pair} from {start.isoformat()} to {now.isoformat()}", flush=True)
        print(f"   📊 Unix timestamps: start={start_unix}, end={end_unix}, granularity={GRANULARITY}", flush=True)
        print(f"   📈 Data window: ~200 candles for proper RSI initialization", flush=True)
        
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
            can_buy, buy_reason = enhanced_should_buy(candles, pair, config, current_price)
            
            if can_buy:
                # Check signal throttling before proceeding
                if not signal_throttle.can_signal(pair):
                    throttle_status = signal_throttle.get_throttle_status(pair)
                    action = "HOLD"
                    reason = f"Signal throttled: {throttle_status} (prevents overtrading)"
                else:
                    # Additional rebuy zone check from config
                    if current_price <= rebuy_zone:
                        action = "BUY"
                        reason = f"Enhanced buy signal: {buy_reason}"
                        # Record the signal to start throttle timer
                        signal_throttle.record_signal(pair)
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
                # Get ATR value for position sizing
                if hasattr(candles, 'candles') and candles.candles:
                    candle_data = candles.candles
                else:
                    candle_data = candles
                    
                try:
                    closes = [float(c.close) for c in candle_data]
                    highs = [float(c.high) for c in candle_data]
                    lows = [float(c.low) for c in candle_data]
                    from strategy import atr
                    current_atr = atr(highs, lows, closes)
                except:
                    current_atr = None
                
                success = position_tracker.open_position(pair, current_price, current_atr)
                if success:
                    print(f"🧪 SIMULATION - BUY executed for {pair} at ${current_price:.6f}", flush=True)
            elif action.startswith("SELL"):
                pnl = position_tracker.close_position(pair, current_price, reason=action)
                print(f"🧪 SIMULATION - {action} executed for {pair} at ${current_price:.6f}", flush=True)
        else:
            # Real trading execution
            if action == "BUY":
                print(f"🚨 LIVE TRADING - BUY signal for {pair} at ${current_price:.6f}", flush=True)
                try:
                    # Get ATR value for position sizing
                    if hasattr(candles, 'candles') and candles.candles:
                        candle_data = candles.candles
                    else:
                        candle_data = candles
                        
                    try:
                        closes = [float(c.close) for c in candle_data]
                        highs = [float(c.high) for c in candle_data]
                        lows = [float(c.low) for c in candle_data]
                        from strategy import atr
                        current_atr = atr(highs, lows, closes)
                    except:
                        current_atr = None
                    
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
                        print(f"✅ BUY ORDER PLACED: {order_result.order_id}", flush=True)
                        position_tracker.open_position(pair, current_price, current_atr)
                    
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
    signals_data = []
    
    for pair in TRADING_PAIRS:
        try:
            print(f"\n🔄 Processing {pair}...", flush=True)
            candles = fetch_candles(pair)
            
            # Collect signal data for dashboard
            if candles and hasattr(candles, 'candles') and candles.candles:
                candle_data = candles.candles
                current_price = float(candle_data[-1].close)
                config = CONFIG.get(pair, CONFIG["DEFAULT"])
                
                # Get technical indicators
                closes = [float(c.close) for c in candle_data]
                highs = [float(c.high) for c in candle_data]
                lows = [float(c.low) for c in candle_data]
                
                current_rsi = rsi(closes, exclude_current=True)
                ema_50 = ema(closes, 50)
                macd_line, signal_line, _ = macd(closes)
                current_atr = atr(highs, lows, closes)
                
                # Get buy/sell analysis
                can_buy, buy_reason = enhanced_should_buy(candles, pair, config, current_price)
                throttle_status = signal_throttle.get_throttle_status(pair)
                
                signal_data = {
                    "pair": pair,
                    "price": current_price,
                    "rsi": current_rsi,
                    "ema_50": ema_50,
                    "ema_uptrend": bool(ema_50 and current_price > ema_50),
                    "macd_line": macd_line,
                    "signal_line": signal_line,
                    "macd_bullish": bool(macd_line and signal_line and macd_line > signal_line),
                    "atr": current_atr,
                    "volatility_ratio": current_atr / current_price if current_atr else None,
                    "can_buy": bool(can_buy),
                    "buy_reason": buy_reason,
                    "throttle_status": throttle_status,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                signals_data.append(signal_data)
            
            analyze_and_trade(pair, candles) # Remove await
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
    print("🚀 Launching bot.py...", flush=True)
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        print("\n👋 Bot shutdown completed", flush=True)
    except Exception as e:
        print(f"💥 Fatal error: {e}", flush=True)
        sys.exit(1)
