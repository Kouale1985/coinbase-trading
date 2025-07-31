CONFIG = {
    "DEFAULT": {
        "take_profit_1": 1.05,  # 5% profit target 1
        "take_profit_2": 1.15,  # 15% profit target 2
        "rebuy_zone": 999999,   # Very high value = always allow buys
        "stop_loss_pct": 0.05   # 5% stop loss
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
    }
}
