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

def rsi(prices, period=14, exclude_current=True):
    """
    Calculate RSI using SMA method - matches Coinbase UI exactly
    Coinbase uses RSI Length: 14, Smoothing Line: SMA, Smoothing Length: 14
    
    Args:
        prices: List of closing prices
        period: RSI period (default 14)
        exclude_current: If True, exclude the last candle (current/live candle)
    """
    if exclude_current and len(prices) > 1:
        # Exclude current candle to match Coinbase UI behavior
        prices = prices[:-1]
    
    if len(prices) < period + 1:
        return None
    
    # Use only the most recent period+1 prices for calculation
    prices = prices[-(period + 1):]
    
    # Calculate price changes
    deltas = np.diff(prices)
    
    # Separate gains and losses
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    
    # Use Simple Moving Average (SMA) - exactly like Coinbase
    avg_gain = np.mean(gains)
    avg_loss = np.mean(losses)
    
    # Avoid division by zero
    if avg_loss == 0:
        return 100
    
    # Calculate RSI using standard formula
    rs = avg_gain / avg_loss
    rsi_val = 100 - (100 / (1 + rs))
    
    return float(rsi_val)

def enhanced_should_buy(candles, current_price):
    """
    Enhanced buy logic with multiple filters:
    1. RSI < 30 (oversold)
    2. Price > 50 EMA (uptrend)
    3. MACD line > signal line (momentum)
    4. ATR < 3% of price (not too volatile)
    """
    # Extract OHLC data
    try:
        if hasattr(candles, 'candles') and candles.candles:
            candle_data = candles.candles
        else:
            candle_data = candles
            
        # Check if we have enough data
        if not candle_data or len(candle_data) < 50:
            return False, "Insufficient data"
            
        closes = [float(c.close) for c in candle_data]
        highs = [float(c.high) for c in candle_data]
        lows = [float(c.low) for c in candle_data]
    except Exception as e:
        return False, f"Data parsing error: {e}"
    
    # 1. RSI Filter (with debug info)
    current_rsi = rsi(closes, exclude_current=True)  # Exclude current candle like Coinbase
    current_rsi_with_live = rsi(closes, exclude_current=False)  # Include current candle
    
    # Debug logging for RSI comparison
    print(f"🔍 RSI Debug - Total candles: {len(closes)}, Last 5 closes: {[f'{c:.6f}' for c in closes[-5:]]}", flush=True)
    print(f"🔍 RSI without current candle (SMA method): {current_rsi:.2f}" if current_rsi else "🔍 RSI without current candle (SMA method): N/A", flush=True)
    print(f"🔍 RSI with current candle (SMA method): {current_rsi_with_live:.2f}" if current_rsi_with_live else "🔍 RSI with current candle (SMA method): N/A", flush=True)
    print(f"🔍 Should match Coinbase UI RSI (Length: 14, Smoothing: SMA)", flush=True)
    
    # 2. EMA Trend Filter (with debug info)
    ema_50 = ema(closes, 50)
    print(f"📈 EMA-50: {ema_50:.6f} | Price: {current_price:.6f} | Uptrend: {'✅' if ema_50 and current_price > ema_50 else '❌'}" if ema_50 else "📈 EMA-50: N/A | Price: {current_price:.6f} | Uptrend: ❌", flush=True)
    
    # 3. MACD Momentum Filter (with debug info)
    macd_line, signal_line, histogram = macd(closes)
    if macd_line is not None and signal_line is not None:
        crossover_status = "Bullish ✅" if macd_line > signal_line else "Bearish ❌"
        print(f"🔁 MACD: {macd_line:.6f} | Signal: {signal_line:.6f} | Crossover: {crossover_status}", flush=True)
    else:
        print(f"🔁 MACD: N/A | Signal: N/A | Crossover: ❌", flush=True)
    
    # 4. ATR Volatility Filter (with debug info)
    current_atr = atr(highs, lows, closes)
    volatility_ratio = current_atr / current_price if current_atr else None
    if current_atr:
        suggested_stop_loss = current_price - (1.5 * current_atr)
        volatility_ok = volatility_ratio <= 0.03
        print(f"⚠️ ATR(14): {current_atr:.6f} | Volatility: {volatility_ratio:.4f} ({volatility_ratio*100:.2f}%) | {'✅' if volatility_ok else '❌'}", flush=True)
        print(f"🛡️ Suggested Stop-Loss: {suggested_stop_loss:.6f} (1.5x ATR below current price)", flush=True)
    else:
        print(f"⚠️ ATR(14): N/A | Volatility: N/A | ❌", flush=True)
    
    print(f"", flush=True)  # Empty line for readability
    
    # Now apply the filters with existing logic
    if current_rsi is None or current_rsi >= 30:
        rsi_display = current_rsi if current_rsi is not None else "N/A"
        return False, f"RSI not oversold: {rsi_display:.2f}" if current_rsi is not None else f"RSI not oversold: {rsi_display}"
    
    if ema_50 is None or current_price <= ema_50:
        ema_display = ema_50 if ema_50 is not None else "N/A"
        return False, f"Price below 50 EMA: ${current_price:.6f} <= ${ema_50:.6f}" if ema_50 is not None else f"Price below 50 EMA: ${current_price:.6f} <= {ema_display}"
    
    if macd_line is None or signal_line is None or macd_line <= signal_line:
        macd_display = f"{macd_line:.6f}" if macd_line is not None else "N/A"
        signal_display = f"{signal_line:.6f}" if signal_line is not None else "N/A"
        return False, f"MACD not bullish: {macd_display} <= {signal_display}"
    
    if current_atr is None:
        return False, "ATR calculation failed"
        
    if volatility_ratio > 0.03:  # 3% threshold
        return False, f"Too volatile: ATR ratio {volatility_ratio:.4f} > 0.03"
    
    return True, f"All filters passed - RSI: {current_rsi:.2f}, EMA: ${ema_50:.6f}, MACD: {macd_line:.6f}, ATR: {volatility_ratio:.4f}"

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
    current_rsi = rsi(closes, exclude_current=True)  # Use same method as buy logic
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
        current_rsi = rsi(closes, exclude_current=True)  # Use improved RSI
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
        current_rsi = rsi(closes, exclude_current=True)  # Use improved RSI
        return current_rsi is not None and current_rsi > 70
    except Exception:
        return False
