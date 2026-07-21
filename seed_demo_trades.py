"""
seed_demo_trades.py

DEV/TEST UTILITY ONLY — not part of the live trading app.

Inserts a few sample CLOSED trades directly into the paper_trades
database so you can see the Trade Book, Analytics, and Capital panels
populate on the dashboard without waiting for a real live signal.

This does NOT touch signal_engine, decision_engine, or any live
market logic — it only writes rows via TradeRepository, exactly like
a real closed trade would look.

Run:
    python3 seed_demo_trades.py

Then refresh the dashboard.
"""

from app.config import PAPER_TRADES_DB_PATH
from app.db import DatabaseManager
from app.repositories.trade_repository import TradeRepository

db = DatabaseManager(db_path=PAPER_TRADES_DB_PATH)
repo = TradeRepository(db=db)


def seed_trade(option_type, entry, stop_loss, target, exit_price, exit_reason, strike=25000):
    option = {
        "strike": strike,
        "option_type": option_type,
        "instrument_key": f"NSE_FO|TEST-{option_type}-{strike}",
        "expiry": "2026-07-31",
        "ltp": entry,
        "lot_size": 65,
    }
    plan = {
        "stop_loss": stop_loss,
        "target": target,
        "confidence": 78,
        "score": 6,
        "reason": ["demo seed data — not a real signal"],
        "quantity": 65,
    }
    trade_id = repo.create_trade(option, plan, quantity=65)
    net_pnl = repo.close_trade(trade_id, exit_price=exit_price, exit_reason=exit_reason)
    print(f"Seeded {option_type} trade: entry={entry} exit={exit_price} net_pnl={net_pnl}")


if __name__ == "__main__":
    seed_trade("CE", entry=120, stop_loss=100, target=160, exit_price=155, exit_reason="TARGET_HIT")
    seed_trade("PE", entry=90, stop_loss=75, target=120, exit_price=75, exit_reason="STOP_LOSS_HIT")
    seed_trade("CE", entry=200, stop_loss=170, target=260, exit_price=245, exit_reason="TARGET_HIT")

    print("\nDone. Refresh the dashboard to see Trade Book, Analytics, and Capital update.")
