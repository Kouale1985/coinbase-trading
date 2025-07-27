import numpy as np

def rsi(prices, period=14):
    deltas = np.diff(prices)
    seed = deltas[:period]
    up = seed[seed > 0].sum() / period
    down = -seed[seed < 0].sum() / period
    rs = up / down if down != 0 else 0
    rsi_values = [100 - 100 / (1 + rs)]

    for delta in deltas[period:]:
        up_val = max(delta, 0)
        down_val = -min(delta, 0)
        up = (up * (period - 1) + up_val) / period
        down = (down * (period - 1) + down_val) / period
        rs = up / down if down != 0 else 0
        rsi_values.append(100 - 100 / (1 + rs))
    
    return rsi_values

def should_buy(candles):
    closes = [c.close for c in candles]
    rsi_values = rsi(closes)
    last_rsi = rsi_values[-1] if rsi_values else 50
    return last_rsi < 30  # Oversold

def should_sell(candles):
    closes = [c.close for c in candles]
    rsi_values = rsi(closes)
    last_rsi = rsi_values[-1] if rsi_values else 50
    return last_rsi > 70  # Overbought
