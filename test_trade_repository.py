"""
Offline test for TradeRepository — uses a scratch SQLite DB, no network.
"""

from app.db import DatabaseManager
from app.repositories.trade_repository import TradeRepository
from app.constants import TARGET_HIT

db = DatabaseManager(db_path="/tmp/test_trade_repository.db")
repo = TradeRepository(db=db)

option = {
    "strike": 25000,
    "option_type": "CE",
    "instrument_key": "NSE_FO|TEST",
    "expiry": "2026-07-24",
    "ltp": 120.5,
}

trade_plan = {
    "stop_loss": 100,
    "target": 150,
    "confidence": 85,
    "score": 7,
    "reason": ["ema cross", "rsi above 55"],
}

trade_id = repo.create_trade(option, trade_plan, quantity=1)
assert repo.get_open_trade() is not None, "Trade should be open."

net_pnl = repo.close_trade(trade_id, exit_price=145.0, exit_reason=TARGET_HIT)
assert net_pnl == 24.5, f"Expected 24.5, got {net_pnl}"
assert repo.get_open_trade() is None, "No trade should be open after close."

print("test_trade_repository: PASSED")
