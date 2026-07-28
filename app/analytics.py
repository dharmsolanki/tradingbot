"""
analytics.py

Computes performance analytics from closed paper trades.
Read-only — never modifies trade data.
"""

from __future__ import annotations

from typing import Any, Dict, List
from app.constants import TRADE_CLOSED

from app.repositories.trade_repository import TradeRepository


class Analytics:
    """Derives win rate, RR, equity curve, and other stats from trade history."""

    def __init__(self, repository: TradeRepository) -> None:
        self.repository = repository

    def summary(self) -> Dict[str, Any]:
        """
        Return aggregate performance statistics across all closed trades.
        """

        closed = self.repository.list_trades(status=TRADE_CLOSED)

        if not closed:
            return {
                "total_trades": 0,
                "wins": 0,
                "losses": 0,
                "win_rate": 0.0,
                "loss_rate": 0.0,
                "average_rr": 0.0,
                "total_net_pnl": 0.0,
                "best_trade": None,
                "worst_trade": None,
                "equity_curve": [],
            }

        wins = [t for t in closed if (t["net_pnl"] or 0) > 0]
        losses = [t for t in closed if (t["net_pnl"] or 0) <= 0]

        total = len(closed)
        win_rate = round(len(wins) / total * 100, 2)
        loss_rate = round(len(losses) / total * 100, 2)

        rr_values = []
        for t in closed:
            risk = t["entry_price"] - t["stop_loss"]
            if risk and risk > 0:
                actual_move = (t["exit_price"] or t["entry_price"]) - t["entry_price"]
                rr_values.append(actual_move / risk)

        average_rr = round(sum(rr_values) / len(rr_values), 2) if rr_values else 0.0

        total_net_pnl = round(sum(t["net_pnl"] or 0 for t in closed), 2)

        best_trade = max(closed, key=lambda t: t["net_pnl"] or 0)
        worst_trade = min(closed, key=lambda t: t["net_pnl"] or 0)

        equity_curve = self._equity_curve(closed)

        return {
            "total_trades": total,
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": win_rate,
            "loss_rate": loss_rate,
            "average_rr": average_rr,
            "total_net_pnl": total_net_pnl,
            "best_trade": {
                "trade_id": best_trade["trade_id"],
                "symbol": best_trade["symbol"],
                "net_pnl": best_trade["net_pnl"],
            },
            "worst_trade": {
                "trade_id": worst_trade["trade_id"],
                "symbol": worst_trade["symbol"],
                "net_pnl": worst_trade["net_pnl"],
            },
            "equity_curve": equity_curve,
        }

    @staticmethod
    def _equity_curve(closed_trades: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Build a running cumulative P/L series ordered by close time,
        for charting on the dashboard.
        """

        ordered = sorted(closed_trades, key=lambda t: t["exit_time"] or "")

        curve = []
        running_total = 0.0

        for trade in ordered:
            running_total += trade["net_pnl"] or 0
            curve.append(
                {
                    "trade_id": trade["trade_id"],
                    "exit_time": trade["exit_time"],
                    "cumulative_pnl": round(running_total, 2),
                }
            )

        return curve
