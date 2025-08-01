# === Trading Constants ===

# RSI Thresholds
RSI_OVERSOLD_THRESHOLD = 32          # Primary oversold condition (was magic number)
RSI_SUPER_OVERSOLD_THRESHOLD = 25    # Emergency oversold condition
RSI_OVERBOUGHT_THRESHOLD = 70        # Overbought exit condition

# ATR Configuration  
ATR_PERIOD = 14                      # ATR calculation period
ATR_STOP_LOSS_MULTIPLIER = 1.5       # ATR stop loss multiplier
ATR_DYNAMIC_TP1_MULTIPLIER = 2.0     # ATR-based take profit 1 (2x ATR)
ATR_DYNAMIC_TP2_MULTIPLIER = 4.0     # ATR-based take profit 2 (4x ATR)

# EMA Configuration
EMA_TREND_PERIOD = 50                # EMA trend confirmation period

# MACD Configuration
MACD_FAST_PERIOD = 12               # MACD fast EMA period
MACD_SLOW_PERIOD = 26               # MACD slow EMA period  
MACD_SIGNAL_PERIOD = 9              # MACD signal line period

# Volatility Filters
MAX_VOLATILITY_RATIO = 0.03         # Max 3% volatility (ATR/price)

# === Portfolio Management Constants ===

# Starting Balance
STARTING_BALANCE_USD = 1000         # Base portfolio value

# Position Limits
MAX_POSITIONS = 4                   # Maximum concurrent positions
MAX_EXPOSURE = 0.75                 # Maximum 75% portfolio exposure  
CASH_BUFFER = 0.25                  # Minimum 25% cash buffer
MAX_PER_TRADE = 0.25                # Maximum 25% per trade
MIN_TRADE_SIZE = 50                 # Minimum trade size in USD

# Risk Management
RISK_PER_TRADE = 0.02               # 2% risk per trade for position sizing

# === Tiered Exit System Constants ===

# Partial Exit Percentages
TIER_1_EXIT_PERCENTAGE = 0.30       # Sell 30% at first target
TIER_2_EXIT_PERCENTAGE = 0.30       # Sell 30% at second target  
TIER_3_HOLD_PERCENTAGE = 0.40       # Hold 40% for trailing stop

# Default Profit Targets (will be replaced by dynamic ATR-based system)
DEFAULT_TAKE_PROFIT_1_PCT = 0.10    # 10% default TP1
DEFAULT_TAKE_PROFIT_2_PCT = 0.20    # 20% default TP2

# Trailing Stop Configuration
TRAILING_STOP_ACTIVATION_PCT = 0.15  # Activate trailing stop after 15% gain
TRAILING_STOP_DISTANCE_PCT = 0.03    # 3% below highest price

# === Signal Throttling ===

SIGNAL_THROTTLE_MINUTES = 15        # 15-minute throttle between signals per pair

# === API Configuration ===

GRANULARITY = "ONE_MINUTE"          # Candle data granularity (reduced lag)
LOOP_SECONDS_DEFAULT = 60           # Bot loop interval in seconds (faster updates)
CANDLE_FETCH_MINUTES = 1000         # Fetch 1000 minutes of data for proper RSI initialization

# === Trading Pairs ===

# Tier-1 High-Volume Cryptocurrency Pairs (Liquid, Less Manipulation Risk)
TIER_1_PAIRS = [
    "BTC-USD", "ETH-USD", "XRP-USD", "ADA-USD", "SOL-USD",
    "DOGE-USD", "DOT-USD", "AVAX-USD", "MATIC-USD", "LINK-USD", 
    "UNI-USD", "LTC-USD", "ATOM-USD", "XLM-USD", "ALGO-USD",
    "VET-USD", "ICP-USD", "FIL-USD", "ETC-USD",
    "OP-USD", "ARB-USD"
]

# === Retry Configuration ===

MAX_RETRIES = 3                     # Maximum API retry attempts
RETRY_BASE_DELAY = 1                # Base delay for exponential backoff (seconds)
RETRY_MAX_DELAY = 30                # Maximum delay between retries (seconds)

# === Simulation Configuration ===

SIMULATION_DEFAULT = True           # Default to simulation mode for safety