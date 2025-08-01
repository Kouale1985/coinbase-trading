# Legacy config.py - Now using dynamic ATR-based targets instead of static configs
# This file is kept for backward compatibility but is no longer actively used

CONFIG = {
    "DEFAULT": {
        "take_profit_1": 1.08,     # 8% profit target 1 (conservative) - DEPRECATED
        "take_profit_2": 1.20,     # 20% profit target 2 (aggressive) - DEPRECATED  
        "rebuy_zone": 999999,      # No price limit - rely on technical filters - DEPRECATED
        "stop_loss_pct": 0.05      # 5% stop loss (overridden by ATR stops) - DEPRECATED
    },
    "XLM-USD": {
        "take_profit_1": 0.46,
        "take_profit_2": 0.50,
        "rebuy_zone": 0.45,     # Updated to current market levels
        "stop_loss_pct": 0.05
    },
    "XRP-USD": {
        "take_profit_1": 3.50,  # Updated based on current price ~$3.07
        "take_profit_2": 4.00,
        "rebuy_zone": 3.50,     # Updated to current market levels
        "stop_loss_pct": 0.05
    },
    "LINK-USD": {
        "take_profit_1": 22.00,
        "take_profit_2": 28.00,
        "rebuy_zone": 25.00,    # Updated to more realistic level
        "stop_loss_pct": 0.05
    },
    "OP-USD": {
        "take_profit_1": 3.00,
        "take_profit_2": 4.50,
        "rebuy_zone": 3.50,     # Updated to more realistic level
        "stop_loss_pct": 0.05
    },
    "ARB-USD": {
        "take_profit_1": 1.20,  # Updated based on typical ARB levels
        "take_profit_2": 1.50,
        "rebuy_zone": 1.50,     # Updated to more realistic level
        "stop_loss_pct": 0.05
    },
    # Major Tier-1 Cryptocurrencies
    "BTC-USD": {
        "take_profit_1": 1.08,     # 8% profit (conservative for BTC)
        "take_profit_2": 1.15,     # 15% profit target
        "rebuy_zone": 999999,      # No price limit - use technical filters
        "stop_loss_pct": 0.05
    },
    "ETH-USD": {
        "take_profit_1": 1.10,     # 10% profit target
        "take_profit_2": 1.20,     # 20% profit target
        "rebuy_zone": 999999,      # No price limit - use technical filters  
        "stop_loss_pct": 0.05
    },
    "SOL-USD": {
        "take_profit_1": 1.12,     # 12% profit target
        "take_profit_2": 1.25,     # 25% profit target
        "rebuy_zone": 999999,      # No price limit - use technical filters
        "stop_loss_pct": 0.05
    },
    "ADA-USD": {
        "take_profit_1": 1.15,     # 15% profit target (higher vol altcoin)
        "take_profit_2": 1.30,     # 30% profit target
        "rebuy_zone": 999999,      # No price limit - use technical filters
        "stop_loss_pct": 0.05
    }
}
