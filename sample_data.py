#!/usr/bin/env python3
"""
Sample data generator for testing the Streamlit dashboard
Run this to create sample data files locally
"""

import json
import os
from datetime import datetime, timezone

def create_sample_data():
    """Create sample JSON data files for dashboard testing"""
    
    # Ensure data directory exists
    os.makedirs('data', exist_ok=True)
    
    # Sample portfolio data
    portfolio_data = {
        "starting_balance": 1000.00,
        "current_cash": 850.00,
        "position_value": 150.00,
        "total_balance": 1000.00,
        "total_return_pct": 0.0,
        "realized_pnl": 0.0,
        "open_positions": 1,
        "max_positions": 4,
        "total_trades": 2,
        "winning_trades": 1,
        "portfolio_exposure": 15.0,
        "max_exposure": 75.0,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Sample positions data
    positions_data = {
        "XLM-USD": {
            "entry_price": 0.420000,
            "current_price": 0.419202,
            "quantity": 357.14,
            "position_value": 149.69,
            "unrealized_pnl": -0.28,
            "unrealized_pnl_pct": -0.19,
            "stop_loss": 0.416801,
            "entry_time": "2025-07-31T19:45:00Z"
        }
    }
    
    # Sample signals data
    signals_data = [
        {
            "pair": "BTC-USD",
            "price": 118435.03,
            "rsi": 40.27,
            "ema_50": 118471.38,
            "ema_uptrend": False,
            "macd_line": -2.635498,
            "signal_line": -2.371948,
            "macd_bullish": False,
            "atr": 78.32,
            "volatility": 0.0007,
            "action": "HOLD",
            "can_buy": False,
            "timestamp": datetime.now(timezone.utc).isoformat()
        },
        {
            "pair": "XLM-USD", 
            "price": 0.419202,
            "rsi": 22.06,
            "ema_50": 0.423037,
            "ema_uptrend": False,
            "macd_line": -0.001173,
            "signal_line": -0.001056,
            "macd_bullish": False,
            "atr": 0.001601,
            "volatility": 0.0038,
            "action": "HOLD",
            "can_buy": False,
            "timestamp": datetime.now(timezone.utc).isoformat()
        },
        {
            "pair": "ETH-USD",
            "price": 3860.85,
            "rsi": 40.97,
            "ema_50": 3861.27,
            "ema_uptrend": False,
            "macd_line": -0.462430,
            "signal_line": -0.416187,
            "macd_bullish": False,
            "atr": 5.39,
            "volatility": 0.0014,
            "action": "HOLD",
            "can_buy": False,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    ]
    
    # Sample trade history
    trade_history = [
        {
            "pair": "XLM-USD",
            "type": "BUY",
            "price": 0.420000,
            "quantity": 357.14,
            "total": 150.00,
            "timestamp": "2025-07-31T19:45:00Z",
            "reason": "RSI oversold + EMA break"
        }
    ]
    
    # Write files
    with open('data/portfolio.json', 'w') as f:
        json.dump(portfolio_data, f, indent=2)
    
    with open('data/positions.json', 'w') as f:
        json.dump(positions_data, f, indent=2)
    
    with open('data/signals.json', 'w') as f:
        json.dump(signals_data, f, indent=2)
    
    with open('data/trade_history.json', 'w') as f:
        json.dump(trade_history, f, indent=2)
    
    print("✅ Sample data files created successfully!")
    print("Files created:")
    print("  - data/portfolio.json")
    print("  - data/positions.json") 
    print("  - data/signals.json")
    print("  - data/trade_history.json")
    print("\n🚀 Now run: streamlit run dashboard.py")

if __name__ == "__main__":
    create_sample_data()