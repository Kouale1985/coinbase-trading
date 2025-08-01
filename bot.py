import os
import sys
import asyncio
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import json

from coinbase.rest import RESTClient
from strategy import should_buy, should_sell, rsi, enhanced_should_buy, enhanced_should_sell, get_atr_stop_loss, ema, macd, atr
from config import CONFIG

# === Core Trading Functions ===

# === Professional Portfolio Management Constants ===
STARTING_BALANCE_USD = 1000  # UPDATE THIS TO YOUR ACTUAL USD BALANCE
MAX_POSITIONS = 4                   # Don't hold more than 4 trades at once
MAX_EXPOSURE = 0.75                 # Use up to 75% of total balance
CASH_BUFFER = 0.25                  # Keep at least 25% cash free
MAX_PER_TRADE = 0.25                # No more than 25% per trade
MIN_TRADE_SIZE = 50                 # Don't enter trades smaller than this
RISK_PER_TRADE = 0.02               # 2% risk per trade for position sizing

# TODO: Add real account balance query
# def get_real_account_balance():
#     """Query actual USD balance from Coinbase account"""
#     try:
#         accounts = client.get_accounts()
#         for account in accounts.accounts:
#             if account.currency == "USD":
#                 return float(account.available_balance.value)
#     except Exception:
#         return STARTING_BALANCE_USD

# === Position Tracker Class ===
class PositionTracker:
    def __init__(self):
        self.positions = {}  # Enhanced tiered position tracking
        self.trade_history = []
        self.total_pnl = 0.0
        self.cash_balance = STARTING_BALANCE_USD
        self.starting_balance = STARTING_BALANCE_USD
        
    def calculate_total_balance(self):
        """Calculate total portfolio value (cash + positions)"""
        position_value = sum(
            pos["entry_price"] * pos["current_quantity"] for pos in self.positions.values()
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
            
        # Execute the trade with enhanced tiered tracking
        self.positions[pair] = {
            "entry_price": price,
            "original_quantity": quantity,
            "current_quantity": quantity,
            "tier_1_sold": 0.0,
            "tier_2_sold": 0.0,
            "tier_1_executed": False,
            "tier_2_executed": False,
            "highest_price": price,
            "trailing_stop_price": None,
            "timestamp": datetime.now(timezone.utc),
            "unrealized_pnl": 0.0
        }
        
        # Update cash balance
        self.cash_balance -= trade_value
        
        total_balance = self.calculate_total_balance()
        print(f"🟢 OPENED POSITION: {pair} | Entry: ${price:.6f} | Qty: {quantity:.6f} | Value: ${trade_value:.2f}", flush=True)
        print(f"   💰 Cash: ${self.cash_balance:.2f} | Total Balance: ${total_balance:.2f} | Positions: {len(self.positions)}/{MAX_POSITIONS}", flush=True)
        return True
    
    def partial_close_position(self, pair, exit_price, percentage, tier_name, reason="PARTIAL_SELL"):
        """Close a percentage of an existing position (for tiered exits)"""
        if pair not in self.positions:
            print(f"⚠️ No position to partially close for {pair}", flush=True)
            return 0.0
            
        position = self.positions[pair]
        entry_price = position["entry_price"]
        current_quantity = position["current_quantity"]
        
        # Calculate quantity to sell (percentage of original position)
        original_quantity = position["original_quantity"]
        sell_quantity = original_quantity * percentage
        
        # Ensure we don't sell more than we have
        if sell_quantity > current_quantity:
            sell_quantity = current_quantity
            
        # Calculate sale proceeds
        sale_proceeds = exit_price * sell_quantity
        
        # Calculate PnL for this partial sale
        pnl_usd = (exit_price - entry_price) * sell_quantity
        pnl_percent = ((exit_price - entry_price) / entry_price) * 100
        
        # Record trade
        trade = {
            "pair": pair,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "quantity": sell_quantity,
            "pnl_usd": pnl_usd,
            "pnl_percent": pnl_percent,
            "reason": f"{reason} ({tier_name})",
            "timestamp": datetime.now(timezone.utc),
            "partial_exit": True,
            "tier": tier_name
        }
        
        self.trade_history.append(trade)
        self.total_pnl += pnl_usd
        
        # Update position quantities
        position["current_quantity"] -= sell_quantity
        
        # Mark tier as executed
        if tier_name == "TIER_1":
            position["tier_1_sold"] = sell_quantity
            position["tier_1_executed"] = True
        elif tier_name == "TIER_2":
            position["tier_2_sold"] = sell_quantity
            position["tier_2_executed"] = True
        
        # Update cash balance
        self.cash_balance += sale_proceeds
        
        # Determine status emoji
        profit_emoji = "📈" if pnl_usd >= 0 else "📉"
        
        print(f"🟡 PARTIAL CLOSE ({tier_name}): {pair} | Exit: ${exit_price:.6f} | Qty: {sell_quantity:.6f} | {profit_emoji} PnL: ${pnl_usd:.2f} ({pnl_percent:+.2f}%)", flush=True)
        print(f"   💰 Cash: ${self.cash_balance:.2f} | Remaining: {position['current_quantity']:.6f} ({(position['current_quantity']/original_quantity)*100:.1f}% of original)", flush=True)
        
        # If position fully closed, remove it
        if position["current_quantity"] <= 0.0001:  # Small threshold for floating point precision
            del self.positions[pair]
            print(f"   🔴 Position fully closed for {pair}", flush=True)
            
        return pnl_usd
        
    def close_position(self, pair, exit_price, reason="SELL"):
        """Close remaining position completely and calculate PnL"""
        if pair not in self.positions:
            print(f"⚠️ No position to close for {pair}", flush=True)
            return 0.0
            
        position = self.positions[pair]
        entry_price = position["entry_price"]
        quantity = position["current_quantity"]  # Use remaining quantity
        
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
        """Update unrealized PnL for open position and handle trailing stops"""
        if pair in self.positions:
            position = self.positions[pair]
            entry_price = position["entry_price"]
            current_quantity = position["current_quantity"]
            unrealized_pnl = (current_price - entry_price) * current_quantity
            position["unrealized_pnl"] = unrealized_pnl
            
            # Update highest price and trailing stop
            self.update_highest_price_and_trailing_stop(pair, current_price)
    
    def update_highest_price_and_trailing_stop(self, pair, current_price):
        """Update highest price and calculate trailing stop for tiered exits"""
        if pair not in self.positions:
            return
            
        position = self.positions[pair]
        
        # Update highest price if current price is higher
        if current_price > position["highest_price"]:
            position["highest_price"] = current_price
            
        # Calculate trailing stop (3% below highest price, but only after tier 2)
        if position["tier_2_executed"]:
            trailing_stop_percentage = 0.03  # 3% trailing stop
            position["trailing_stop_price"] = position["highest_price"] * (1 - trailing_stop_percentage)
        else:
            position["trailing_stop_price"] = None
            
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
        
        # Enhanced trade statistics
        partial_trades = len([t for t in self.trade_history if t.get("partial_exit", False)])
        full_trades = total_trades - partial_trades
        tier_1_trades = len([t for t in self.trade_history if t.get("tier") == "TIER_1"])
        tier_2_trades = len([t for t in self.trade_history if t.get("tier") == "TIER_2"])
        
        print(f"\n📊 TRADING STATISTICS:", flush=True)
        print(f"   💼 Open Positions: {open_positions}/{MAX_POSITIONS}", flush=True)
        print(f"   📈 Total Trades: {total_trades} (Full: {full_trades}, Partial: {partial_trades})", flush=True)
        print(f"   🎯 Winning Trades: {winning_trades}/{total_trades}" + (f" ({winning_trades/total_trades*100:.1f}%)" if total_trades > 0 else ""), flush=True)
        print(f"   🎯 Tiered Exits: T1: {tier_1_trades} | T2: {tier_2_trades}", flush=True)
        
        print(f"\n📊 RISK MANAGEMENT:", flush=True)
        print(f"   💰 Available Cash: ${self.cash_balance:.2f}", flush=True)
        print(f"   📊 Portfolio Exposure: {exposure_percentage:.1f}% (max {MAX_EXPOSURE*100:.0f}%)", flush=True)
        print(f"   📊 Max Per Trade: {MAX_PER_TRADE*100:.0f}% (${total_balance * MAX_PER_TRADE:.0f})", flush=True)
        print(f"   📊 Min Trade Size: ${MIN_TRADE_SIZE}", flush=True)
        
        if self.positions:
            print(f"\n📋 OPEN POSITIONS:", flush=True)
            for pair, pos in self.positions.items():
                unrealized = pos.get("unrealized_pnl", 0)
                position_value = pos["entry_price"] * pos["current_quantity"]
                percentage = (position_value / total_balance) * 100
                
                # Tiered status
                original_qty = pos["original_quantity"]
                current_qty = pos["current_quantity"]
                remaining_pct = (current_qty / original_qty) * 100
                tier_1_status = "✅" if pos["tier_1_executed"] else "⏳"
                tier_2_status = "✅" if pos["tier_2_executed"] else "⏳"
                trailing_active = "🔄" if pos.get("trailing_stop_price") else "⏸️"
                
                print(f"      {pair}: ${pos['entry_price']:.6f} | Value: ${position_value:.2f} ({percentage:.1f}%) | Unrealized: ${unrealized:.2f}", flush=True)
                print(f"         🎯 Tiers: T1 {tier_1_status} | T2 {tier_2_status} | Trail {trailing_active} | Remaining: {remaining_pct:.1f}% | Peak: ${pos['highest_price']:.6f}", flush=True)

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

# === Tiered Exit Strategy Logic ===
def check_tiered_exits(position, current_price, tier_1_target, tier_2_target):
    """
    Check tiered exit conditions and return appropriate action
    
    Tier 1: Sell 30% at tier_1_target (e.g., +10%)
    Tier 2: Sell 30% at tier_2_target (e.g., +20%) 
    Tier 3: Keep 40% with trailing stop (3% below peak)
    """
    entry_price = position["entry_price"]
    tier_1_executed = position["tier_1_executed"]
    tier_2_executed = position["tier_2_executed"]
    trailing_stop_price = position.get("trailing_stop_price")
    
    # Calculate target prices
    tier_1_price = entry_price * tier_1_target
    tier_2_price = entry_price * tier_2_target
    
    # Check Tier 1 exit (30% at +10%)
    if not tier_1_executed and current_price >= tier_1_price:
        return "SELL_TIER_1", f"Tier 1 target reached: ${current_price:.6f} >= ${tier_1_price:.6f} (+{((tier_1_target-1)*100):.0f}%) - Selling 30%"
    
    # Check Tier 2 exit (30% at +20%)
    if tier_1_executed and not tier_2_executed and current_price >= tier_2_price:
        return "SELL_TIER_2", f"Tier 2 target reached: ${current_price:.6f} >= ${tier_2_price:.6f} (+{((tier_2_target-1)*100):.0f}%) - Selling 30%"
    
    # Check Tier 3 trailing stop (remaining 40%)
    if tier_2_executed and trailing_stop_price and current_price <= trailing_stop_price:
        return "SELL_TIER_3", f"Trailing stop triggered: ${current_price:.6f} <= ${trailing_stop_price:.6f} - Selling remaining 40%"
    
    # No exit conditions met
    if tier_2_executed:
        return "HOLD", f"Trailing stop active at ${trailing_stop_price:.6f}" if trailing_stop_price else "Waiting for trailing stop setup"
    elif tier_1_executed:
        return "HOLD", f"Waiting for Tier 2 at ${tier_2_price:.6f} (+{((tier_2_target-1)*100):.0f}%)"
    else:
        return "HOLD", f"Waiting for Tier 1 at ${tier_1_price:.6f} (+{((tier_1_target-1)*100):.0f}%)"

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
            
            # Get tiered exit configuration
            tier_1_target = config.get("tier_1_target", config["take_profit_1"])
            tier_2_target = config.get("tier_2_target", config["take_profit_2"])
            
            # Priority 1: Check ATR-based stop loss (emergency exit)
            should_sell_enhanced, sell_action, sell_reason = enhanced_should_sell(candles, current_price, entry_price)
            
            if should_sell_enhanced:
                action = "SELL_ALL"
                reason = f"Emergency exit: {sell_reason}"
            else:
                # Priority 2: Tiered Exit Strategy
                action, reason = check_tiered_exits(current_position, current_price, tier_1_target, tier_2_target)
                
            # Show position status with tiered information
            original_qty = current_position["original_quantity"]
            current_qty = current_position["current_quantity"]
            remaining_pct = (current_qty / original_qty) * 100
            tier_1_status = "✅" if current_position["tier_1_executed"] else "⏳"
            tier_2_status = "✅" if current_position["tier_2_executed"] else "⏳"
            trailing_active = "🔄" if current_position.get("trailing_stop_price") else "⏸️"
                    
            # Show position status
            pnl_percent = ((current_price - entry_price) / entry_price) * 100
            pnl_emoji = "📈" if unrealized >= 0 else "📉"
            
            # Show comprehensive position status
            atr_stop = get_atr_stop_loss(candles, entry_price)
            highest_price = current_position["highest_price"]
            trailing_stop = current_position.get("trailing_stop_price")
            
            print(f"   💼 Position: Entry ${entry_price:.6f} | {pnl_emoji} Unrealized: ${unrealized:.2f} ({pnl_percent:+.2f}%) | Remaining: {remaining_pct:.1f}%", flush=True)
            print(f"   📊 Tiers: T1 {tier_1_status} | T2 {tier_2_status} | Trail {trailing_active} | Peak: ${highest_price:.6f}", flush=True)
            if trailing_stop:
                print(f"   🛡️ Trailing Stop: ${trailing_stop:.6f} | ATR Stop: ${atr_stop:.6f}" if atr_stop else f"   🛡️ Trailing Stop: ${trailing_stop:.6f}", flush=True)
            elif atr_stop:
                print(f"   🛡️ ATR Stop: ${atr_stop:.6f}", flush=True)
        
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
                # Handle different sell types in simulation
                if action == "SELL_TIER_1":
                    pnl = position_tracker.partial_close_position(pair, current_price, 0.30, "TIER_1", reason="TIER_1_PROFIT")
                    print(f"🧪 SIMULATION - TIER 1 exit executed (30%) for {pair} at ${current_price:.6f}", flush=True)
                elif action == "SELL_TIER_2":
                    pnl = position_tracker.partial_close_position(pair, current_price, 0.30, "TIER_2", reason="TIER_2_PROFIT")
                    print(f"🧪 SIMULATION - TIER 2 exit executed (30%) for {pair} at ${current_price:.6f}", flush=True)
                elif action == "SELL_TIER_3":
                    pnl = position_tracker.close_position(pair, current_price, reason="TIER_3_TRAILING")
                    print(f"🧪 SIMULATION - TIER 3 trailing exit executed (remaining) for {pair} at ${current_price:.6f}", flush=True)
                elif action == "SELL_ALL":
                    pnl = position_tracker.close_position(pair, current_price, reason=action)
                    print(f"🧪 SIMULATION - Emergency exit executed (100%) for {pair} at ${current_price:.6f}", flush=True)
                else:
                    # Fallback for legacy sell actions
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
                        # Calculate quantity based on sell type
                        if action == "SELL_TIER_1":
                            # Sell 30% of original position
                            quantity = current_position["original_quantity"] * 0.30
                            print(f"📊 TIER 1 EXIT - Selling 30% of original position: {quantity:.6f}", flush=True)
                        elif action == "SELL_TIER_2":
                            # Sell 30% of original position
                            quantity = current_position["original_quantity"] * 0.30
                            print(f"📊 TIER 2 EXIT - Selling 30% of original position: {quantity:.6f}", flush=True)
                        else:
                            # Sell all remaining (SELL_TIER_3, SELL_ALL, or legacy)
                            quantity = current_position["current_quantity"]
                            print(f"📊 FULL EXIT - Selling remaining position: {quantity:.6f}", flush=True)
                        
                        # Execute the sell order
                        order_result = client.market_order_sell(
                            client_order_id=f"sell_{pair}_{int(datetime.now().timestamp())}",
                            product_id=pair,
                            base_size=str(quantity)
                        )
                        print(f"✅ SELL ORDER PLACED: {order_result.order_id}", flush=True)
                        
                        # Update position tracker
                        if action == "SELL_TIER_1":
                            position_tracker.partial_close_position(pair, current_price, 0.30, "TIER_1", reason="TIER_1_PROFIT")
                        elif action == "SELL_TIER_2":
                            position_tracker.partial_close_position(pair, current_price, 0.30, "TIER_2", reason="TIER_2_PROFIT")
                        else:
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
    # try:
    #     export_portfolio_data(position_tracker)
    #     export_positions_data(position_tracker)
    #     export_signals_data(signals_data)
    #     export_trade_history(position_tracker)
    #     commit_data_to_github()
    # except Exception as e:
    #     print(f"⚠️ Error exporting dashboard data: {e}", flush=True)
    
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
