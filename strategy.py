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
        
        # Calculate indicators (RSI removed - focus on reliable signals)
        # No more RSI calculation - it was inconsistent and blocking good trades
        ema_50 = ema(closes, 50)
        macd_line, signal_line, _ = macd(closes)
        current_atr = atr(highs, lows, closes)
        
        if not all([ema_50, macd_line, signal_line, current_atr]):
            return False, "Indicator calculation failed"
        
        # Debug logging (RSI removed)
        print(f"🔍 Price Analysis - Total candles: {len(candle_data)}, Last 5 closes: {[c.close for c in candle_data[-5:]]}")
        print(f"🔍 Last candle timestamp: {candle_data[-1].start}")
        print(f"🔍 Strategy: MACD + EMA trend analysis (RSI removed for better performance)")
        
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
        
        # Simplified buy conditions (RSI removed)
        # Focus on reliable trend and momentum indicators only
        
        # Main buy conditions: EMA uptrend + MACD bullish + reasonable volatility
        buy_conditions = (
            ema_uptrend and 
            macd_bullish and
            volatility_ok and 
            current_price <= rebuy_zone
        )
        
        # Final buy decision (simplified)
        should_buy = buy_conditions
        
        # Detailed reason logging (RSI removed)
        if not should_buy:
            if not ema_uptrend:
                reason = f"Price below 50 EMA: ${current_price:.6f} <= ${ema_50:.6f}"
            elif not macd_bullish:
                reason = f"MACD bearish: {macd_line:.6f} <= {signal_line:.6f}"
            elif not volatility_ok:
                reason = f"Volatility too high: {volatility_ratio*100:.2f}%"
            elif current_price > rebuy_zone:
                reason = f"Price above rebuy zone: ${current_price:.6f} > ${rebuy_zone:.6f}"
            else:
                reason = "Multiple filter failures"
        else:
            reason = f"Entry filters passed: EMA uptrend ✅ | MACD bullish ✅ | Volatility OK ✅"
        
        return should_buy, reason
        
    except Exception as e:
        print(f"❌ Error in enhanced_should_buy for {pair}: {e}")
        return False, f"Error: {str(e)}"

def enhanced_should_sell(candles, current_price, entry_price):
    """
    Enhanced sell logic:
    ATR-based stop loss triggered (RSI removed)
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
    
    # ATR-based Stop Loss Check (RSI removed)
    current_atr = atr(highs, lows, closes)
    if current_atr is not None and entry_price is not None:
        atr_stop_loss = entry_price - (1.5 * current_atr)
        stop_triggered = current_price <= atr_stop_loss
        print(f"🛡️ ATR Stop-Loss: {atr_stop_loss:.6f} | Current: {current_price:.6f} | Entry: {entry_price:.6f} | {'🚨 TRIGGERED' if stop_triggered else '✅ SAFE'}", flush=True)
    else:
        print(f"🛡️ ATR Stop-Loss: N/A | Current: {current_price:.6f} | Entry: {entry_price:.6f if entry_price else 'N/A'}", flush=True)
    
    print(f"", flush=True)  # Empty line for readability
    
    # Apply sell logic (RSI removed)
    if current_atr is not None and entry_price is not None:
        atr_stop_loss = entry_price - (1.5 * current_atr)
        if current_price <= atr_stop_loss:
            return True, "SELL (ATR STOP)", f"ATR stop triggered: ${current_price:.6f} <= ${atr_stop_loss:.6f}"
    
    return False, "HOLD", "No emergency sell conditions met (ATR stop only)"

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
