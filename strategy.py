import numpy as np
import pandas as pd

def atr(highs, lows, closes, period=14):
    """Calculate Average True Range (ATR)"""
    if len(highs) < period + 1:
        return None
        
    # True Range calculation
    tr_list = []
    for i in range(1, len(highs)):
        high_low = highs[i] - lows[i]
        high_close_prev = abs(highs[i] - closes[i-1])
        low_close_prev = abs(lows[i] - closes[i-1])
        tr = max(high_low, high_close_prev, low_close_prev)
        tr_list.append(tr)
    
    # ATR is the moving average of True Range
    if len(tr_list) >= period:
        return np.mean(tr_list[-period:])
    return None

def ema(prices, period):
    """Calculate Exponential Moving Average (EMA)"""
    if len(prices) < period:
        return None
    
    prices_array = np.array(prices)
    alpha = 2 / (period + 1)
    ema_values = []
    
    # Start with SMA for first value
    ema_values.append(np.mean(prices_array[:period]))
    
    # Calculate EMA for remaining values
    for i in range(period, len(prices_array)):
        ema_val = alpha * prices_array[i] + (1 - alpha) * ema_values[-1]
        ema_values.append(ema_val)
    
    return ema_values[-1] if ema_values else None

def macd(prices, fast_period=12, slow_period=26, signal_period=9):
    """Calculate MACD (Moving Average Convergence Divergence)"""
    if len(prices) < slow_period + signal_period:
        return None, None, None
    
    # Calculate EMAs
    ema_fast = []
    ema_slow = []
    prices_array = np.array(prices)
    
    # Fast EMA
    alpha_fast = 2 / (fast_period + 1)
    ema_fast.append(np.mean(prices_array[:fast_period]))
    for i in range(fast_period, len(prices_array)):
        ema_val = alpha_fast * prices_array[i] + (1 - alpha_fast) * ema_fast[-1]
        ema_fast.append(ema_val)
    
    # Slow EMA  
    alpha_slow = 2 / (slow_period + 1)
    ema_slow.append(np.mean(prices_array[:slow_period]))
    for i in range(slow_period, len(prices_array)):
        ema_val = alpha_slow * prices_array[i] + (1 - alpha_slow) * ema_slow[-1]
        ema_slow.append(ema_val)
    
    # MACD line = Fast EMA - Slow EMA
    if len(ema_fast) < len(ema_slow):
        return None, None, None
        
    macd_line = ema_fast[-1] - ema_slow[-1]
    
    # Signal line = EMA of MACD line (simplified to just return current value)
    # For full implementation, you'd need to track MACD history
    signal_line = macd_line * 0.9  # Simplified approximation
    
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram

def exponential_moving_average(values, period):
    """Calculate EMA for a list of values"""
    import numpy as np
    alpha = 2.0 / (period + 1)
    ema = np.zeros_like(values)
    ema[0] = values[0]
    
    for i in range(1, len(values)):
        ema[i] = alpha * values[i] + (1 - alpha) * ema[i-1]
    
    return ema[-1]

def rsi(closes, period=14):
    """
    Calculate RSI using EMA-based smoothing for crypto markets
    More responsive to recent price changes than SMA method
    
    Args:
        closes: List of closing prices (including live price)
        period: RSI period (default 14)
    """
    if len(closes) < period + 1:
        return 0

    # Convert to float
    prices = [float(price) for price in closes]
    
    # Calculate all price deltas
    import numpy as np
    deltas = np.diff(prices)
    
    # Separate gains and losses
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    
    # Need at least 'period' deltas for EMA calculation
    if len(gains) < period:
        return 50  # Not enough data
    
    # Use EMA smoothing for gains and losses (more responsive for crypto)
    ema_gain = exponential_moving_average(gains[-period:], period)
    ema_loss = exponential_moving_average(losses[-period:], period)
    
    # Debug output for RSI calculation
    print(f"🔍 RSI Debug: Using last {period} deltas from {len(prices)} prices")
    print(f"🔍 RSI Debug: EMA gain: {ema_gain:.6f}, EMA loss: {ema_loss:.6f}")
    
    # Calculate RSI using EMA smoothed values
    if ema_loss == 0:
        return 100.0  # No losses = RSI 100
    if ema_gain == 0:
        return 0.0    # No gains = RSI 0
    
    rs = ema_gain / ema_loss
    rsi_value = 100 - (100 / (1 + rs))
    
    return round(rsi_value, 2)

def enhanced_should_buy(candles, pair, config, current_price):
    """
    Enhanced buy signal with multiple filters
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
        
        # Extract price arrays
        closes = [float(c.close) for c in candle_data]
        highs = [float(c.high) for c in candle_data]
        lows = [float(c.low) for c in candle_data]
        
        # Get enhanced live price for better RSI accuracy (pseudo-tick sampling)
        from bot import get_enhanced_live_price
        enhanced_live_price = get_enhanced_live_price(pair, samples=2, delay=0.3)
        
        if enhanced_live_price is not None:
            # Use enhanced live price for more accurate RSI
            closes_with_live = closes + [enhanced_live_price]
            print(f"🔍 Using enhanced live price: {enhanced_live_price:.6f} vs current: {current_price:.6f}")
        else:
            # Fallback to current price if enhanced sampling fails
            closes_with_live = closes + [current_price]
            print(f"🔍 Fallback to current price: {current_price:.6f}")
        
        # Calculate indicators
        current_rsi = rsi(closes_with_live)
        ema_50 = ema(closes, 50)
        macd_line, signal_line, _ = macd(closes)
        current_atr = atr(highs, lows, closes)
        
        if not all([current_rsi, ema_50, macd_line, signal_line, current_atr]):
            return False, "Indicator calculation failed"
        
        # Debug logging
        print(f"🔍 RSI Debug - Total candles: {len(candle_data)}, Last 5 closes: {[c.close for c in candle_data[-5:]]}")
        print(f"🔍 Last candle timestamp: {candle_data[-1].start}")
        print(f"🔍 RSI (EMA-based method): {current_rsi:.2f}")
        print(f"🔍 More responsive EMA smoothing for crypto markets")
        print(f"🔍 Using COMPLETED candles + ENHANCED live price sampling")
        
        # EMA trend check
        ema_uptrend = current_price > ema_50
        print(f"📈 EMA-50: {ema_50:.6f} | Price: {current_price:.6f} | Uptrend: {'✅' if ema_uptrend else '❌'}")
        
        # MACD momentum check
        macd_bullish = macd_line > signal_line
        print(f"🔁 MACD: {macd_line:.6f} | Signal: {signal_line:.6f} | Crossover: {'Bullish ✅' if macd_bullish else 'Bearish ❌'}")
        
        # ATR volatility check (should be reasonable, not too high)
        volatility_ratio = current_atr / current_price
        volatility_ok = volatility_ratio < 0.03  # Less than 3% volatility
        print(f"⚠️ ATR(14): {current_atr:.6f} | Volatility: {volatility_ratio:.4f} ({volatility_ratio*100:.2f}%) | {'✅' if volatility_ok else '❌'}")
        print(f"🛡️ Suggested Stop-Loss: {current_price - (1.5 * current_atr):.6f} (1.5x ATR below current price)")
        
        # Get configuration for this pair
        pair_config = config.get(pair, config.get("DEFAULT", {}))
        rebuy_zone = pair_config.get("rebuy_zone", current_price * 1.05)  # 5% above current as default
        
        print()
        
        # Enhanced buy conditions with SMART ADJUSTMENTS
        # 🎯 SMART TWEAK #1: Slightly more aggressive RSI (30 -> 32)
        rsi_oversold = current_rsi < 32  # Was 30, now 32 for more opportunities
        
        # 🎯 SMART TWEAK #2: Allow super oversold entries even with bearish MACD
        super_oversold = current_rsi < 25  # Emergency oversold condition
        
        # Main buy conditions
        basic_conditions = (
            rsi_oversold and 
            ema_uptrend and 
            volatility_ok and 
            current_price <= rebuy_zone
        )
        
        # Enhanced condition: allow super oversold entries even with bearish MACD
        emergency_oversold = (
            super_oversold and 
            ema_uptrend and 
            volatility_ok and 
            current_price <= rebuy_zone
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
            elif current_price > rebuy_zone:
                reason = f"Price above rebuy zone: ${current_price:.6f} > ${rebuy_zone:.6f}"
            else:
                reason = "Multiple filter failures"
        else:
            if emergency_oversold:
                reason = f"Emergency oversold entry: RSI {current_rsi:.2f} < 25"
            else:
                reason = f"All enhanced filters passed: RSI {current_rsi:.2f}, EMA trend ✅, MACD ✅"
        
        return should_buy, reason
        
    except Exception as e:
        print(f"❌ Error in enhanced_should_buy for {pair}: {e}")
        return False, f"Error: {str(e)}"

def enhanced_should_sell(candles, current_price, entry_price):
    """
    Enhanced sell logic:
    1. RSI > 70 (overbought) OR
    2. ATR-based stop loss triggered
    """
    # Extract OHLC data
    try:
        if hasattr(candles, 'candles') and candles.candles:
            candle_data = candles.candles
        else:
            candle_data = candles
            
        # Check if we have enough data
        if not candle_data or len(candle_data) < 15:
            return False, "HOLD", "Insufficient data"
            
        closes = [float(c.close) for c in candle_data]
        highs = [float(c.high) for c in candle_data]
        lows = [float(c.low) for c in candle_data]
    except Exception as e:
        return False, "HOLD", f"Data parsing error: {e}"
    
    # RSI Overbought Check (with debug info)
    current_rsi = rsi(closes)  # Use same method as buy logic
    print(f"🔍 SELL Check - RSI: {current_rsi:.2f} | Overbought Threshold: 70 | {'✅ SELL' if current_rsi and current_rsi > 70 else '❌ HOLD'}" if current_rsi else "🔍 SELL Check - RSI: N/A | ❌ HOLD", flush=True)
    
    # ATR-based Stop Loss Check (with debug info)
    current_atr = atr(highs, lows, closes)
    if current_atr is not None and entry_price is not None:
        atr_stop_loss = entry_price - (1.5 * current_atr)
        stop_triggered = current_price <= atr_stop_loss
        print(f"🛡️ ATR Stop-Loss: {atr_stop_loss:.6f} | Current: {current_price:.6f} | Entry: {entry_price:.6f} | {'🚨 TRIGGERED' if stop_triggered else '✅ SAFE'}", flush=True)
    else:
        print(f"🛡️ ATR Stop-Loss: N/A | Current: {current_price:.6f} | Entry: {entry_price:.6f if entry_price else 'N/A'}", flush=True)
    
    print(f"", flush=True)  # Empty line for readability
    
    # Apply sell logic
    if current_rsi is not None and current_rsi > 70:
        return True, "SELL (RSI)", f"RSI overbought: {current_rsi:.2f}"
    
    if current_atr is not None and entry_price is not None:
        atr_stop_loss = entry_price - (1.5 * current_atr)
        if current_price <= atr_stop_loss:
            return True, "SELL (ATR STOP)", f"ATR stop triggered: ${current_price:.6f} <= ${atr_stop_loss:.6f}"
    
    return False, "HOLD", f"No sell conditions met - RSI: {current_rsi:.2f}" if current_rsi is not None else "No sell conditions met - RSI: N/A"

def get_atr_stop_loss(candles, entry_price, multiplier=1.5):
    """Calculate ATR-based stop loss price"""
    try:
        if hasattr(candles, 'candles') and candles.candles:
            candle_data = candles.candles
        else:
            candle_data = candles
            
        # Check if we have enough data
        if not candle_data or len(candle_data) < 15:
            return None
            
        closes = [float(c.close) for c in candle_data]
        highs = [float(c.high) for c in candle_data]
        lows = [float(c.low) for c in candle_data]
        
        current_atr = atr(highs, lows, closes)
        if current_atr is not None and entry_price is not None:
            return entry_price - (multiplier * current_atr)
    except Exception:
        pass
    
    return None

# Legacy functions for backward compatibility
def should_buy(candles):
    """Legacy function - basic RSI only"""
    try:
        if hasattr(candles, 'candles') and candles.candles:
            candle_data = candles.candles
        else:
            candle_data = candles
            
        # Check if we have enough data
        if not candle_data or len(candle_data) < 15:
            return False
            
        closes = [float(c.close) for c in candle_data]
        current_rsi = rsi(closes)  # Use improved RSI
        return current_rsi is not None and current_rsi < 30
    except Exception:
        return False

def should_sell(candles):
    """Legacy function - basic RSI only"""
    try:
        if hasattr(candles, 'candles') and candles.candles:
            candle_data = candles.candles
        else:
            candle_data = candles
            
        # Check if we have enough data
        if not candle_data or len(candle_data) < 15:
            return False
            
        closes = [float(c.close) for c in candle_data]
        current_rsi = rsi(closes)  # Use improved RSI
        return current_rsi is not None and current_rsi > 70
    except Exception:
        return False
