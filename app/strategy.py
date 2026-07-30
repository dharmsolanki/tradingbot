"""
Trading Strategy Configuration

Is file me sirf strategy parameters rahenge.
Signal Engine in values ko use karega.
"""

# ==========================
# Strategy Mode
# ==========================
# "EMA"  — original Multi-Timeframe EMA+MACD+RSI strategy
# "ORB"  — Opening Range Breakout strategy
SIGNAL_MODE = "ORB"
VALID_SIGNAL_MODES = {
    "EMA",
    "ORB",
}

if SIGNAL_MODE not in VALID_SIGNAL_MODES:
    raise ValueError(f"Invalid SIGNAL_MODE: {SIGNAL_MODE}")

# ==========================
# EMA
# ==========================

EMA_FAST = 20
EMA_SLOW = 50

# ==========================
# RSI
# ==========================

RSI_PERIOD = 14

RSI_BUY_LEVEL = 55
RSI_SELL_LEVEL = 45

# ==========================
# MACD
# ==========================

MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# ==========================
# ATR
# ==========================

ATR_PERIOD = 14

# Ignore trades when volatility is too low
MIN_ATR = 20

# ==========================
# SuperTrend
# ==========================

SUPERTREND_LENGTH = 10
SUPERTREND_MULTIPLIER = 3

# ==========================
# Risk Management
# ==========================

# Reward = Risk × Ratio
RISK_REWARD_RATIO = 2.0

# Option Premium Based Stop Loss (%)
STOP_LOSS_PERCENT = 15.0

# Automatically becomes 30%
TARGET_PERCENT = STOP_LOSS_PERCENT * RISK_REWARD_RATIO

# Default quantity
DEFAULT_QUANTITY = 1

# Maximum capital risk per trade
MAX_RISK_PER_TRADE = 3.0

# ==========================
# Signal
# ==========================

MIN_CONFIDENCE = 75

# ==========================
# Option Selection
# ==========================

OPTION_MODE = "ATM"  # ATM / ITM / OTM
VALID_OPTION_MODES = {
    "ATM",
    "ITM",
    "OTM",
}

if OPTION_MODE not in VALID_OPTION_MODES:
    raise ValueError(f"Invalid OPTION_MODE: {OPTION_MODE}")

STRIKE_STEP = 50  # NIFTY
# STRIKE_STEP = 100  # BANKNIFTY

# ==========================
# Demo Account / Risk Management
# ==========================

# Virtual capital for demo trading (not real money).
STARTING_CAPITAL = 10000.0  # virtual demo capital

# Stop trading for the day once realized loss exceeds this % of capital.
MAX_DAILY_LOSS_PERCENT = 3.0

# Maximum number of trades allowed per trading day.
MAX_TRADES_PER_DAY = 10

# Once a trade is in profit by this % of risk, move stop loss to entry.
TRAILING_TRIGGER_RR = 1.0

# Minimum liquidity filters applied before a trade plan is accepted.
MIN_OPTION_OI = 500
MAX_SPREAD_PERCENT = 5.0

# ==========================
# Recommendations
# ==========================

# Target 2 = Risk x this ratio (Target 1 uses RISK_REWARD_RATIO above).
RISK_REWARD_RATIO_2 = 3.5

# Entry is published as a range (e.g. "145-148") rather than a single
# price, to reflect real fill variance. Width as % of the entry premium.
ENTRY_RANGE_PERCENT = 2.0

# Label shown on published recommendations, describing the confirmation
# logic actually used (multi-timeframe trend + entry confirmation).
STRATEGY_NAME = "Multi-Timeframe EMA + MACD + RSI Confirmation"
MIN_DAILY_PROFIT_RUPEES = 10000.0
if MIN_DAILY_PROFIT_RUPEES < 0:
    raise ValueError("MIN_DAILY_PROFIT_RUPEES cannot be negative.")

if STOP_LOSS_PERCENT <= 0:
    raise ValueError("STOP_LOSS_PERCENT must be greater than zero.")

if RISK_REWARD_RATIO <= 0:
    raise ValueError("RISK_REWARD_RATIO must be greater than zero.")

if DEFAULT_QUANTITY <= 0:
    raise ValueError("DEFAULT_QUANTITY must be greater than zero.")
