"""
Offline test for the new risk-management functions (no network needed).
"""

from app.risk import (
    calculate_position_size,
    check_daily_loss_limit,
    check_trade_count_limit,
    update_trailing_stop,
)

# Position sizing: 1% of 100000 = 1000 max risk. risk_per_lot = 15*65 = 975 -> 1 lot.
assert calculate_position_size(100000, risk_per_unit=15, lot_size=65) == 1

# Daily loss limit: 2.5% loss, threshold 3% -> not breached.
result = check_daily_loss_limit(-2500, 100000)
assert result["breached"] is False

# Daily loss limit breached: 5% loss, threshold 3%.
result = check_daily_loss_limit(-5000, 100000)
assert result["breached"] is True

# Trade count limit.
assert check_trade_count_limit(5) is True
assert check_trade_count_limit(2) is False

# Trailing stop moves to breakeven once trigger reached, never moves backward.
new_sl = update_trailing_stop("CE", entry=100, current_stop_loss=85, current_premium=118, risk=15)
assert new_sl == 100

unchanged_sl = update_trailing_stop("CE", entry=100, current_stop_loss=85, current_premium=105, risk=15)
assert unchanged_sl == 85

print("test_risk_management: PASSED")
