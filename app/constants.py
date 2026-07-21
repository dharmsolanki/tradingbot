"""
Application-wide constants.

Keep all reusable constant values here.
Avoid hardcoding strings throughout the project.
"""

# ==========================
# Trade Status
# ==========================

TRADE_OPEN = "OPEN"
TRADE_CLOSED = "CLOSED"
TRADE_CANCELLED = "CANCELLED"


# ==========================
# Signal Types
# ==========================

BUY = "BUY"
SELL = "SELL"
NO_TRADE = "NO_TRADE"


# ==========================
# Option Types
# ==========================

CALL = "CE"
PUT = "PE"


# ==========================
# Trade Exit Reasons
# ==========================

TARGET_HIT = "TARGET_HIT"
STOP_LOSS_HIT = "STOP_LOSS_HIT"
MANUAL_EXIT = "MANUAL_EXIT"
TIME_EXIT = "TIME_EXIT"


# ==========================
# Database
# ==========================

DEFAULT_DB_PATH = "database/trading.db"


# ==========================
# Monitoring
# ==========================

DEFAULT_MONITOR_INTERVAL = 1  # seconds


# ==========================
# Risk Defaults
# ==========================

DEFAULT_QUANTITY = 1
