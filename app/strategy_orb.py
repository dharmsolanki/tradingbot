"""
strategy_orb.py

Configuration constants for the Opening Range Breakout (ORB) strategy.
Kept separate from strategy.py so both strategies can coexist.
"""

# Opening Range window (market opens 9:15, range ends at this time)
ORB_END_TIME = "09:30"  # HH:MM — candles up to this time form the range

# Minimum range size to consider valid (avoid flat/holiday opens)
ORB_MIN_RANGE_POINTS = 30  # NIFTY points
ORB_MAX_RANGE_POINTS = 300  # range too big = skip

# Risk/Reward
ORB_RISK_REWARD = 1.5  # Target = SL distance x 2

# Breakout confirmation — price must close ABOVE/BELOW range, not just touch
ORB_CONFIRMATION = "CLOSE"  # "CLOSE" or "HIGH_LOW"

# Minimum ATR (5m) to confirm volatility is present
ORB_MIN_ATR = 30

# Max trades per day via ORB
ORB_MAX_TRADES = 2
ORB_SIGNAL_CUTOFF = "13:00"  # No new trades after this time
