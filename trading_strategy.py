from indicators import calculate_all_indicators, get_dynamic_targets, get_atr_stop_loss
from constants import (
    RSI_OVERSOLD_THRESHOLD, RSI_SUPER_OVERSOLD_THRESHOLD, RSI_OVERBOUGHT_THRESHOLD,
    MAX_VOLATILITY_RATIO, ATR_STOP_LOSS_MULTIPLIER
)

def enhanced_should_buy(candles, pair, current_price):
    """
    Enhanced buy signal with dynamic ATR-based targets instead of static config
    """
    try:
        # Extract candle data
        if hasattr(candles, 'candles') and candles.candles:
            candle_data = candles.candles
        else:
            candle_data = candles
            
        if len(candle_data) < 50:
            print(f"⚠️ Insufficient data for {pair}: {len(candle_data)} candles")
            return False, "Insufficient data"
        
        # Calculate all indicators at once
        indicators = calculate_all_indicators(candle_data)
        
        current_rsi = indicators['rsi']
        ema_50 = indicators['ema_50']
        macd_line = indicators['macd_line']
        signal_line = indicators['signal_line']
        current_atr = indicators['atr']
        
        if not all([current_rsi, ema_50, macd_line, signal_line, current_atr]):
            return False, "Indicator calculation failed"
        
        # Debug logging
        print(f"🔍 RSI: {current_rsi:.2f} | EMA-50: {ema_50:.6f} | MACD: {macd_line:.6f} | ATR: {current_atr:.6f}")
        
        # EMA trend check
        ema_uptrend = current_price > ema_50
        print(f"📈 EMA Trend: {'✅ Bullish' if ema_uptrend else '❌ Bearish'} (Price: ${current_price:.6f} vs EMA: ${ema_50:.6f})")
        
        # MACD momentum check
        macd_bullish = macd_line > signal_line
        print(f"🔁 MACD: {'✅ Bullish' if macd_bullish else '❌ Bearish'} (Line: {macd_line:.6f} vs Signal: {signal_line:.6f})")
        
        # ATR volatility check
        volatility_ratio = current_atr / current_price
        volatility_ok = volatility_ratio < MAX_VOLATILITY_RATIO
        print(f"⚠️ Volatility: {volatility_ratio*100:.2f}% {'✅ OK' if volatility_ok else '❌ Too High'} (Max: {MAX_VOLATILITY_RATIO*100:.1f}%)")
        
        # Calculate dynamic targets
        tp1_price, tp2_price = get_dynamic_targets(current_price, current_atr)
        stop_loss_price = current_price - (ATR_STOP_LOSS_MULTIPLIER * current_atr)
        
        print(f"🎯 Dynamic Targets: TP1: ${tp1_price:.6f} | TP2: ${tp2_price:.6f} | Stop: ${stop_loss_price:.6f}")
        
        # Enhanced buy conditions with dynamic adjustments
        rsi_oversold = current_rsi < RSI_OVERSOLD_THRESHOLD
        super_oversold = current_rsi < RSI_SUPER_OVERSOLD_THRESHOLD
        
        # Main buy conditions
        basic_conditions = (
            rsi_oversold and 
            ema_uptrend and 
            volatility_ok
        )
        
        # Enhanced condition: allow super oversold entries even with bearish MACD
        emergency_oversold = (
            super_oversold and 
            ema_uptrend and 
            volatility_ok
        )
        
        # Final buy decision
        should_buy = (basic_conditions and macd_bullish) or emergency_oversold
        
        # Detailed reason logging
        if not should_buy:
            if not rsi_oversold:
                reason = f"RSI not oversold: {current_rsi:.2f}"
            elif not ema_uptrend:
                reason = f"Price below 50 EMA: ${current_price:.6f} <= ${ema_50:.6f}"
            elif not macd_bullish and not super_oversold:
                reason = f"MACD bearish and RSI not super oversold: {current_rsi:.2f}"
            elif not volatility_ok:
                reason = f"Volatility too high: {volatility_ratio*100:.2f}%"
            else:
                reason = "Multiple filter failures"
        else:
            if emergency_oversold:
                reason = f"Emergency oversold entry: RSI {current_rsi:.2f} < {RSI_SUPER_OVERSOLD_THRESHOLD}"
            else:
                reason = f"All enhanced filters passed: RSI {current_rsi:.2f}, EMA trend ✅, MACD ✅"
        
        return should_buy, reason
        
    except Exception as e:
        print(f"❌ Error in enhanced_should_buy for {pair}: {e}")
        return False, f"Error: {str(e)}"

def enhanced_should_sell(candles, current_price, entry_price, position_tracker, pair):
    """
    Enhanced sell logic with tiered exits and trailing stops
    """
    try:
        if hasattr(candles, 'candles') and candles.candles:
            candle_data = candles.candles
        else:
            candle_data = candles
            
        if not candle_data or len(candle_data) < 15:
            return False, "HOLD", "Insufficient data"
        
        # Calculate indicators
        indicators = calculate_all_indicators(candle_data)
        current_rsi = indicators['rsi']
        current_atr = indicators['atr']
        
        # Get position status
        position = position_tracker.get_position_status(pair)
        if not position:
            return False, "HOLD", "No position found"
            
        # Update position with current price (for trailing stops)
        position_tracker.update_position(pair, current_price)
        
        # Calculate dynamic targets based on current ATR
        tp1_price, tp2_price = get_dynamic_targets(entry_price, current_atr)
        
        print(f"🔍 SELL Check - RSI: {current_rsi:.2f} | TP1: ${tp1_price:.6f} | TP2: ${tp2_price:.6f}")
        
        # Check for RSI overbought
        if current_rsi and current_rsi > RSI_OVERBOUGHT_THRESHOLD:
            return True, "SELL (RSI)", f"RSI overbought: {current_rsi:.2f}"
        
        # Check for ATR-based stop loss
        if current_atr and entry_price:
            atr_stop_loss = entry_price - (ATR_STOP_LOSS_MULTIPLIER * current_atr)
            if current_price <= atr_stop_loss:
                return True, "SELL (ATR STOP)", f"ATR stop triggered: ${current_price:.6f} <= ${atr_stop_loss:.6f}"
        
        # Check for trailing stop
        if position_tracker.check_trailing_stop(pair, current_price):
            return True, "SELL (TRAILING STOP)", f"Trailing stop triggered at ${current_price:.6f}"
        
        # Check for tiered exits
        if tp1_price and not position.get("tier_1_sold", False):
            if current_price >= tp1_price:
                return True, "TIER_1_EXIT", f"Dynamic TP1 reached: ${current_price:.6f} >= ${tp1_price:.6f}"
                
        if tp2_price and not position.get("tier_2_sold", False):
            if current_price >= tp2_price:
                return True, "TIER_2_EXIT", f"Dynamic TP2 reached: ${current_price:.6f} >= ${tp2_price:.6f}"
        
        return False, "HOLD", f"No sell conditions met - RSI: {current_rsi:.2f}" if current_rsi else "No sell conditions met - RSI: N/A"
        
    except Exception as e:
        return False, "HOLD", f"Error in sell logic: {e}"

def execute_sell_action(action, pair, current_price, position_tracker):
    """
    Execute the appropriate sell action (tiered or full exit)
    """
    try:
        if action == "TIER_1_EXIT":
            return position_tracker.execute_tier_exit(pair, current_price, 1, "Dynamic TP1")
        elif action == "TIER_2_EXIT":
            return position_tracker.execute_tier_exit(pair, current_price, 2, "Dynamic TP2")
        elif action.startswith("SELL"):
            return position_tracker.close_position(pair, current_price, reason=action)
        else:
            return 0.0
    except Exception as e:
        print(f"❌ Error executing sell action {action} for {pair}: {e}")
        return 0.0