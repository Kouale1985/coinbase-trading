import numpy as np
from constants import (
    ATR_PERIOD, EMA_TREND_PERIOD, MACD_FAST_PERIOD, 
    MACD_SLOW_PERIOD, MACD_SIGNAL_PERIOD
)

def atr(highs, lows, closes, period=ATR_PERIOD):
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

def ema(prices, period=EMA_TREND_PERIOD):
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

def macd(prices, fast_period=MACD_FAST_PERIOD, slow_period=MACD_SLOW_PERIOD, signal_period=MACD_SIGNAL_PERIOD):
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

def calculate_all_indicators(candle_data):
    """
    Calculate all indicators for given candle data in a single function.
    Returns a dictionary with all calculated indicators.
    """
    try:
        # Extract price arrays
        closes = [float(c.close) for c in candle_data]
        highs = [float(c.high) for c in candle_data]
        lows = [float(c.low) for c in candle_data]
        
        # Calculate all indicators
        indicators = {
            'rsi': rsi(closes, exclude_current=True),
            'ema_50': ema(closes, EMA_TREND_PERIOD),
            'macd_line': None,
            'signal_line': None,
            'macd_histogram': None,
            'atr': atr(highs, lows, closes)
        }
        
        # Calculate MACD
        macd_line, signal_line, histogram = macd(closes)
        indicators['macd_line'] = macd_line
        indicators['signal_line'] = signal_line  
        indicators['macd_histogram'] = histogram
        
        return indicators
        
    except Exception as e:
        print(f"❌ Error calculating indicators: {e}")
        return {
            'rsi': None,
            'ema_50': None, 
            'macd_line': None,
            'signal_line': None,
            'macd_histogram': None,
            'atr': None
        }

def get_atr_stop_loss(candle_data, entry_price, multiplier=1.5):
    """Calculate ATR-based stop loss price"""
    try:
        if hasattr(candle_data, 'candles') and candle_data.candles:
            candle_data = candle_data.candles
            
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

def get_dynamic_targets(current_price, atr_value):
    """
    Calculate dynamic profit targets based on ATR
    Returns (tp1_price, tp2_price) using ATR multipliers
    """
    from constants import ATR_DYNAMIC_TP1_MULTIPLIER, ATR_DYNAMIC_TP2_MULTIPLIER
    
    if not atr_value or atr_value <= 0:
        return None, None
        
    tp1_price = current_price + (ATR_DYNAMIC_TP1_MULTIPLIER * atr_value)
    tp2_price = current_price + (ATR_DYNAMIC_TP2_MULTIPLIER * atr_value)
    
    return tp1_price, tp2_price