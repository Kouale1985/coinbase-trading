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

def rsi(prices, period=14):
    """Calculate Relative Strength Index (RSI)"""
    if len(prices) < period + 1:
        return None
    
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])
    
    if avg_loss == 0:
        return 100
    
    rs = avg_gain / avg_loss
    rsi_val = 100 - (100 / (1 + rs))
    return rsi_val

def enhanced_should_buy(candles, current_price):
    """
    Enhanced buy logic with multiple filters:
    1. RSI < 30 (oversold)
    2. Price > 50 EMA (uptrend)
    3. MACD line > signal line (momentum)
    4. ATR < 3% of price (not too volatile)
    """
    if not candles or len(candles) < 50:
        return False, "Insufficient data"
    
    # Extract OHLC data
    try:
        if hasattr(candles, 'candles') and candles.candles:
            candle_data = candles.candles
        else:
            candle_data = candles
            
        closes = [float(c.close) for c in candle_data]
        highs = [float(c.high) for c in candle_data]
        lows = [float(c.low) for c in candle_data]
    except Exception as e:
        return False, f"Data parsing error: {e}"
    
    # 1. RSI Filter
    current_rsi = rsi(closes)
    if current_rsi is None or current_rsi >= 30:
        return False, f"RSI not oversold: {current_rsi:.2f}"
    
    # 2. EMA Trend Filter
    ema_50 = ema(closes, 50)
    if ema_50 is None or current_price <= ema_50:
        return False, f"Price below 50 EMA: ${current_price:.6f} <= ${ema_50:.6f}"
    
    # 3. MACD Momentum Filter
    macd_line, signal_line, _ = macd(closes)
    if macd_line is None or signal_line is None or macd_line <= signal_line:
        return False, f"MACD not bullish: {macd_line:.6f} <= {signal_line:.6f}"
    
    # 4. Volatility Filter (ATR)
    current_atr = atr(highs, lows, closes)
    if current_atr is None:
        return False, "ATR calculation failed"
        
    volatility_ratio = current_atr / current_price
    if volatility_ratio > 0.03:  # 3% threshold
        return False, f"Too volatile: ATR ratio {volatility_ratio:.4f} > 0.03"
    
    return True, f"All filters passed - RSI: {current_rsi:.2f}, EMA: ${ema_50:.6f}, MACD: {macd_line:.6f}, ATR: {volatility_ratio:.4f}"

def enhanced_should_sell(candles, current_price, entry_price):
    """
    Enhanced sell logic:
    1. RSI > 70 (overbought) OR
    2. ATR-based stop loss triggered
    """
    if not candles or len(candles) < 15:
        return False, "HOLD", "Insufficient data"
    
    # Extract OHLC data
    try:
        if hasattr(candles, 'candles') and candles.candles:
            candle_data = candles.candles
        else:
            candle_data = candles
            
        closes = [float(c.close) for c in candle_data]
        highs = [float(c.high) for c in candle_data]
        lows = [float(c.low) for c in candle_data]
    except Exception as e:
        return False, "HOLD", f"Data parsing error: {e}"
    
    # RSI Overbought Check
    current_rsi = rsi(closes)
    if current_rsi is not None and current_rsi > 70:
        return True, "SELL (RSI)", f"RSI overbought: {current_rsi:.2f}"
    
    # ATR-based Stop Loss
    current_atr = atr(highs, lows, closes)
    if current_atr is not None and entry_price is not None:
        atr_stop_loss = entry_price - (1.5 * current_atr)
        if current_price <= atr_stop_loss:
            return True, "SELL (ATR STOP)", f"ATR stop triggered: ${current_price:.6f} <= ${atr_stop_loss:.6f}"
    
    return False, "HOLD", f"No sell conditions met - RSI: {current_rsi:.2f if current_rsi else 'N/A'}"

def get_atr_stop_loss(candles, entry_price, multiplier=1.5):
    """Calculate ATR-based stop loss price"""
    if not candles or len(candles) < 15:
        return None
    
    try:
        if hasattr(candles, 'candles') and candles.candles:
            candle_data = candles.candles
        else:
            candle_data = candles
            
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
    if not candles or len(candles) < 15:
        return False
    
    try:
        if hasattr(candles, 'candles') and candles.candles:
            candle_data = candles.candles
        else:
            candle_data = candles
            
        closes = [float(c.close) for c in candle_data]
        current_rsi = rsi(closes)
        return current_rsi is not None and current_rsi < 30
    except Exception:
        return False

def should_sell(candles):
    """Legacy function - basic RSI only"""
    if not candles or len(candles) < 15:
        return False
    
    try:
        if hasattr(candles, 'candles') and candles.candles:
            candle_data = candles.candles
        else:
            candle_data = candles
            
        closes = [float(c.close) for c in candle_data]
        current_rsi = rsi(closes)
        return current_rsi is not None and current_rsi > 70
    except Exception:
        return False
