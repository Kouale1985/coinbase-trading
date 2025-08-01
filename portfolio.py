from datetime import datetime, timezone
from constants import (
    STARTING_BALANCE_USD, MAX_POSITIONS, MAX_EXPOSURE, CASH_BUFFER,
    MAX_PER_TRADE, MIN_TRADE_SIZE, RISK_PER_TRADE,
    TIER_1_EXIT_PERCENTAGE, TIER_2_EXIT_PERCENTAGE, TIER_3_HOLD_PERCENTAGE,
    TRAILING_STOP_ACTIVATION_PCT, TRAILING_STOP_DISTANCE_PCT
)

class PositionTracker:
    """Enhanced position tracker with tiered exit system"""
    
    def __init__(self):
        self.positions = {}  # {pair: position_dict}
        self.trade_history = []
        self.total_pnl = 0.0
        self.cash_balance = STARTING_BALANCE_USD
        self.starting_balance = STARTING_BALANCE_USD
        
    def calculate_total_balance(self, current_prices=None):
        """Calculate total portfolio value (cash + positions)"""
        if current_prices is None:
            # Fallback to entry prices if current prices not provided
            position_value = sum(
                pos["entry_price"] * pos["total_quantity"] for pos in self.positions.values()
            )
        else:
            # Use current market prices for accurate portfolio value
            position_value = sum(
                current_prices.get(pair, pos["entry_price"]) * pos["total_quantity"] 
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
        """Open a new position with tiered exit tracking"""
        quantity, reason = self.calculate_position_size(price, atr_value)
        
        if quantity <= 0:
            print(f"⚠️ Cannot open position for {pair}: {reason}", flush=True)
            return False
            
        trade_value = quantity * price
        
        # Check if we have enough cash
        if trade_value > self.cash_balance:
            print(f"⚠️ Insufficient cash for {pair}: Need ${trade_value:.2f}, have ${self.cash_balance:.2f}", flush=True)
            return False
            
        # Execute the trade with tiered tracking
        self.positions[pair] = {
            "entry_price": price,
            "total_quantity": quantity,
            "remaining_quantity": quantity,
            "entry_value": trade_value,
            "position_value": trade_value,
            "timestamp": datetime.now(timezone.utc),
            "unrealized_pnl": 0.0,
            "highest_price": price,  # For trailing stop
            "tier_1_sold": False,
            "tier_2_sold": False,
            "trailing_stop_active": False,
            "trailing_stop_price": None
        }
        
        # Update cash balance
        self.cash_balance -= trade_value
        
        total_balance = self.calculate_total_balance()
        print(f"🟢 OPENED POSITION: {pair} | Entry: ${price:.6f} | Qty: {quantity:.6f} | Value: ${trade_value:.2f}", flush=True)
        print(f"   💰 Cash: ${self.cash_balance:.2f} | Total Balance: ${total_balance:.2f} | Positions: {len(self.positions)}/{MAX_POSITIONS}", flush=True)
        return True
    
    def execute_tier_exit(self, pair, current_price, tier, reason):
        """Execute a tiered exit (sell portion of position)"""
        if pair not in self.positions:
            return 0.0
            
        position = self.positions[pair]
        
        # Calculate quantity to sell based on tier
        if tier == 1 and not position["tier_1_sold"]:
            sell_quantity = position["total_quantity"] * TIER_1_EXIT_PERCENTAGE
            position["tier_1_sold"] = True
        elif tier == 2 and not position["tier_2_sold"]:
            sell_quantity = position["total_quantity"] * TIER_2_EXIT_PERCENTAGE  
            position["tier_2_sold"] = True
        else:
            return 0.0  # Tier already executed or invalid
            
        # Update remaining quantity
        position["remaining_quantity"] -= sell_quantity
        
        # Calculate PnL for this tier
        entry_price = position["entry_price"]
        sale_proceeds = current_price * sell_quantity
        tier_pnl = (current_price - entry_price) * sell_quantity
        
        # Record tier trade
        trade = {
            "pair": pair,
            "type": f"TIER_{tier}_EXIT",
            "entry_price": entry_price,
            "exit_price": current_price,
            "quantity": sell_quantity,
            "pnl_usd": tier_pnl,
            "pnl_percent": ((current_price - entry_price) / entry_price) * 100,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc)
        }
        
        self.trade_history.append(trade)
        self.total_pnl += tier_pnl
        self.cash_balance += sale_proceeds
        
        # Check if position is fully closed
        if position["remaining_quantity"] <= 0.001:  # Account for floating point precision
            del self.positions[pair]
            
        total_balance = self.calculate_total_balance()
        profit_emoji = "💰" if tier_pnl > 0 else "📉"
        print(f"🎯 TIER_{tier}_EXIT: {pair} | Exit: ${current_price:.6f} | {profit_emoji} PnL: ${tier_pnl:.2f}", flush=True)
        print(f"   💰 Sale Proceeds: ${sale_proceeds:.2f} | Cash: ${self.cash_balance:.2f} | Total: ${total_balance:.2f}", flush=True)
        
        return tier_pnl
        
    def close_position(self, pair, exit_price, reason="SELL"):
        """Close an entire position (remaining quantity)"""
        if pair not in self.positions:
            print(f"⚠️ No position to close for {pair}", flush=True)
            return 0.0
            
        position = self.positions[pair]
        entry_price = position["entry_price"]
        quantity = position["remaining_quantity"]
        
        # Calculate sale proceeds and PnL
        sale_proceeds = exit_price * quantity
        pnl_usd = (exit_price - entry_price) * quantity
        pnl_percent = ((exit_price - entry_price) / entry_price) * 100
        
        # Record trade
        trade = {
            "pair": pair,
            "type": "FULL_EXIT",
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
        
    def update_position(self, pair, current_price):
        """Update position with current price and trailing stop logic"""
        if pair not in self.positions:
            return
            
        position = self.positions[pair]
        entry_price = position["entry_price"]
        remaining_quantity = position["remaining_quantity"]
        
        # Update position value and unrealized PnL
        position_value = current_price * remaining_quantity
        unrealized_pnl = (current_price - entry_price) * remaining_quantity
        
        position["position_value"] = position_value
        position["unrealized_pnl"] = unrealized_pnl
        
        # Update highest price for trailing stop
        if current_price > position["highest_price"]:
            position["highest_price"] = current_price
            
        # Check if trailing stop should be activated
        gain_pct = (current_price - entry_price) / entry_price
        if gain_pct >= TRAILING_STOP_ACTIVATION_PCT and not position["trailing_stop_active"]:
            position["trailing_stop_active"] = True
            position["trailing_stop_price"] = current_price * (1 - TRAILING_STOP_DISTANCE_PCT)
            print(f"📈 TRAILING STOP ACTIVATED for {pair}: ${position['trailing_stop_price']:.6f}", flush=True)
            
        # Update trailing stop price if active
        if position["trailing_stop_active"]:
            new_stop_price = position["highest_price"] * (1 - TRAILING_STOP_DISTANCE_PCT)
            if new_stop_price > position["trailing_stop_price"]:
                position["trailing_stop_price"] = new_stop_price
                
    def check_trailing_stop(self, pair, current_price):
        """Check if trailing stop should trigger"""
        if pair not in self.positions:
            return False
            
        position = self.positions[pair]
        
        if position["trailing_stop_active"] and position["trailing_stop_price"]:
            return current_price <= position["trailing_stop_price"]
            
        return False
        
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
                position_value = pos["entry_price"] * pos["remaining_quantity"]
                percentage = (position_value / total_balance) * 100
                tier_status = ""
                if pos.get("tier_1_sold"):
                    tier_status += "T1✅ "
                if pos.get("tier_2_sold"):
                    tier_status += "T2✅ "
                if pos.get("trailing_stop_active"):
                    tier_status += f"Trail@${pos.get('trailing_stop_price', 0):.6f}"
                    
                print(f"      {pair}: ${pos['entry_price']:.6f} | Remaining: {pos['remaining_quantity']:.6f} | Value: ${position_value:.2f} ({percentage:.1f}%) | {tier_status}", flush=True)
                print(f"              Unrealized: ${unrealized:.2f} | Highest: ${pos.get('highest_price', 0):.6f}", flush=True)

class SignalThrottle:
    """Signal throttling to prevent overtrading"""
    
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