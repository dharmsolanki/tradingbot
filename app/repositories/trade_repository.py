"""
trade_repository.py

Data access layer for paper trades. All SQL for the paper_trades
table lives here — no other module should write raw SQL against it.

Uses DatabaseManager (app.db) and the canonical schema (app.core.schema),
which is the richer schema (includes brokerage/charges/net_pnl) — this
replaces the ad-hoc table paper_trader.py used to create on its own.
"""

from __future__ import annotations

import uuid
from datetime import datetime, UTC
from typing import Any, Dict, List, Optional

from app.core.exceptions import TradeAlreadyOpenError, TradeNotFoundError
from app.core.schema import CREATE_INDEXES, CREATE_PAPER_TRADES_TABLE
from app.db import DatabaseManager
from app.constants import TRADE_OPEN


class TradeRepository:
    """Repository for creating, reading, and closing paper trades."""

    def __init__(self, db: Optional[DatabaseManager] = None) -> None:
        """
        Args:
            db: Injected DatabaseManager. Creates a default one
                (using config-driven path) if not provided.
        """

        if db is None:
            from app.config import PAPER_TRADES_DB_PATH

            db = DatabaseManager(db_path=PAPER_TRADES_DB_PATH)

        self.db = db
        self._create_schema()

    def _create_schema(self) -> None:
        """Create the paper_trades table and its indexes if missing."""

        self.db.execute(CREATE_PAPER_TRADES_TABLE)

        for index_statement in CREATE_INDEXES:
            self.db.execute(index_statement)

    def create_trade(
        self,
        option: Dict[str, Any],
        trade_plan: Dict[str, Any],
        quantity: int,
    ) -> str:
        """
        Insert a new OPEN paper trade.

        Args:
            option: Output of OptionService.get_option().
            trade_plan: Output of risk.calculate_trade_levels().
            quantity: Number of lots/units.

        Returns:
            The generated trade_id.

        Raises:
            TradeAlreadyOpenError: If an OPEN trade already exists.
        """

        if self.get_open_trade() is not None:
            raise TradeAlreadyOpenError(
                "An open trade already exists. Close it before opening a new one."
            )

        trade_id = str(uuid.uuid4())

        if quantity <= 0:
            raise ValueError("quantity must be positive.")

        reason = trade_plan.get("reason", [])

        if isinstance(reason, list):
            entry_reason = "; ".join(reason)
        else:
            entry_reason = str(reason)

        self.db.execute(
            """
            INSERT INTO paper_trades (
                trade_id, symbol, instrument_key, option_type,
                strike, expiry, quantity,
                entry_price, stop_loss, target,
                status, confidence, score,
                entry_reason, entry_time
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trade_id,
                f"{option['strike']} {option['option_type']}",
                option["instrument_key"],
                option["option_type"],
                option["strike"],
                option["expiry"],
                quantity,
                option["ltp"],
                trade_plan["stop_loss"],
                trade_plan["target"],
                TRADE_OPEN,
                trade_plan.get("confidence", 0),
                trade_plan.get("score", 0),
                entry_reason,
                datetime.now(UTC).isoformat(),
            ),
        )

        return trade_id

    def get_open_trade(self) -> Optional[Dict[str, Any]]:
        """Return the most recent OPEN trade, or None if there is none."""

        return self.db.fetchone("""
            SELECT * FROM paper_trades
            WHERE status = 'OPEN'
            ORDER BY id DESC
            LIMIT 1
            """)

    def get_trade_by_id(self, trade_id: str) -> Optional[Dict[str, Any]]:
        """Return a trade by its trade_id, or None if not found."""

        return self.db.fetchone(
            "SELECT * FROM paper_trades WHERE trade_id = ?",
            (trade_id,),
        )

    def close_trade(
        self,
        trade_id: str,
        exit_price: float,
        exit_reason: str,
        brokerage: float = 0.0,
        charges: float = 0.0,
    ) -> float:
        """
        Close an OPEN trade and record P/L.

        Args:
            trade_id: Trade to close.
            exit_price: Exit premium.
            exit_reason: One of the exit reason constants.
            brokerage: Brokerage cost to deduct.
            charges: Other charges (taxes, fees) to deduct.

        Returns:
            net_pnl for the closed trade.

        Raises:
            TradeNotFoundError: If trade_id does not exist or is not OPEN.
        """

        if brokerage < 0 or charges < 0:
            raise ValueError("brokerage and charges cannot be negative.")

        trade = self.get_trade_by_id(trade_id)

        if trade is None or trade["status"] != TRADE_OPEN:
            raise TradeNotFoundError(f"No OPEN trade found for trade_id={trade_id}.")

        entry = trade["entry_price"]
        quantity = trade["quantity"]

        # Both CE and PE are long-option positions (we only buy, never
        # write/sell). Profit in both cases = premium rise since entry.
        gross_pnl = (exit_price - entry) * quantity

        net_pnl = gross_pnl - brokerage - charges

        self.db.execute(
            """
            UPDATE paper_trades
            SET exit_price = ?, exit_time = ?, status = 'CLOSED',
                exit_reason = ?, gross_pnl = ?, brokerage = ?,
                charges = ?, net_pnl = ?
            WHERE trade_id = ?
            """,
            (
                exit_price,
                datetime.now(UTC).isoformat(),
                exit_reason,
                round(gross_pnl, 2),
                round(brokerage, 2),
                round(charges, 2),
                round(net_pnl, 2),
                trade_id,
            ),
        )

        return round(net_pnl, 2)

    def list_trades(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Return trades, optionally filtered by status.

        Args:
            status: "OPEN", "CLOSED", "CANCELLED", or None for all.
        """

        if status is None:
            return self.db.fetchall("SELECT * FROM paper_trades ORDER BY id DESC")

        return self.db.fetchall(
            "SELECT * FROM paper_trades WHERE status = ? ORDER BY id DESC",
            (status,),
        )
