"""
Offline test for Analytics — uses a scratch SQLite DB, no network.
"""

from app.db import DatabaseManager
from app.repositories.trade_repository import TradeRepository
from app.analytics import Analytics
from app.constants import TARGET_HIT
from app.constants import STOP_LOSS_HIT

db = DatabaseManager(db_path="/tmp/test_analytics.db")
repo = TradeRepository(db=db)
analytics = Analytics(repo)


def make_trade(option_type, entry, stop_loss, target, exit_price, reason):
    option = {
        "strike": 25000,
        "option_type": option_type,
        "instrument_key": f"NSE_FO|{option_type}",
        "expiry": "2026-07-24",
        "ltp": entry,
    }
    plan = {
        "stop_loss": stop_loss,
        "target": target,
        "confidence": 80,
        "score": 5,
        "reason": [],
    }
    trade_id = repo.create_trade(option, plan, quantity=1)
    repo.close_trade(trade_id, exit_price=exit_price, exit_reason=reason)


make_trade("CE", entry=100, stop_loss=85, target=130, exit_price=130, reason=TARGET_HIT)
make_trade(
    "PE", entry=80, stop_loss=68, target=104, exit_price=68, reason=STOP_LOSS_HIT
)

summary = analytics.summary()

assert summary["total_trades"] == 2
assert summary["wins"] == 1
assert summary["losses"] == 1
assert summary["win_rate"] == 50.0
assert len(summary["equity_curve"]) == 2

print("test_analytics: PASSED")
