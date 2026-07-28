"""
paper_trader.py

Manual paper-trading facade used by the app to open/close simulated
trades. Storage is delegated to TradeRepository (app.db + app.core.schema)
so there is a single source of truth for the paper_trades schema.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.repositories.trade_repository import TradeRepository


class PaperTrader:
    """Facade over TradeRepository for opening/closing paper trades."""

    def __init__(self, db_path: str = "database/paper_trades.db") -> None:
        """
        Args:
            db_path: Path to the SQLite database file.
        """

        from app.db import DatabaseManager

        self.repository = TradeRepository(db=DatabaseManager(db_path=db_path))

    def open_trade(
        self,
        option: Dict[str, Any],
        trade_plan: Dict[str, Any],
        quantity: int = 1,
    ) -> str:
        """
        Open a new paper trade.

        Args:
            option: Output of OptionService.get_option().
            trade_plan: Output of risk.calculate_trade_levels().
            quantity: Number of lots/units.

        Returns:
            The generated trade_id.
        """

        if quantity <= 0:
            raise ValueError("quantity must be positive.")

        if self.repository.get_open_trade() is not None:
            raise ValueError("An open trade already exists.")

        return self.repository.create_trade(option, trade_plan, quantity)

    def get_open_trade(self) -> Optional[Dict[str, Any]]:
        """Return the current OPEN trade, or None if there isn't one."""

        return self.repository.get_open_trade()

    def close_trade(
        self,
        trade_id: str,
        exit_price: float,
        reason: str,
    ) -> float:
        """
        Close an OPEN trade.

        Args:
            trade_id: Trade to close.
            exit_price: Exit premium.
            reason: Exit reason (e.g. TARGET_HIT, STOP_LOSS_HIT, MANUAL_EXIT).

        Returns:
            net_pnl for the closed trade.
        """

        if exit_price <= 0:
            raise ValueError("exit_price must be positive.")

        return self.repository.close_trade(
            trade_id,
            exit_price,
            exit_reason=reason,
        )
