"""
decision_engine.py

Combines the signal engine, option service, and risk engine into a
single decision: is there a valid, tradeable setup right now?

This module NEVER places real orders. It only produces a TradePlan
(or a WAIT/NO_TRADE result) that the demo trading engine can act on.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from app import strategy, strategy_orb
from app.option_service import OptionService
from app.risk import (
    calculate_position_size,
    calculate_trade_levels,
    check_daily_loss_limit,
    check_trade_count_limit,
)
from app.signal_engine import (
    calculate_indicators_multi_timeframe,
    generate_signal_v2,
)
from app.utils import get_logger

logger = get_logger(__name__)


class DecisionEngine:
    """Decides whether a live, high-probability trade setup exists."""

    def __init__(self, option_service: Optional[OptionService] = None) -> None:
        self.option_service = option_service or OptionService()

    def evaluate(
        self,
        token: str,
        instrument_key: str,
        candles_5m: list,
        candles_15m: list,
        capital: float,
        realized_pnl_today: float,
        trades_today_count: int,
        has_open_trade: bool,
    ) -> Dict[str, Any]:
        """
        Run the full decision pipeline for one evaluation cycle.

        Returns
        -------
        dict
            {
                "decision": "TRADE" | "WAIT" | "NO_TRADE" | "BLOCKED",
                "signal": {...},
                "trade_plan": {...} | None,
                "reasons": [...]
            }
        """

        reasons: list[str] = []

        # ---------- Guard: already in a position ----------

        if has_open_trade:
            return {
                "decision": "WAIT",
                "signal": None,
                "trade_plan": None,
                "reasons": ["A trade is already open. Managing existing position."],
            }

        # ---------- Guard: daily loss limit ----------

        loss_check = check_daily_loss_limit(realized_pnl_today, capital)

        if loss_check["breached"]:
            return {
                "decision": "BLOCKED",
                "signal": None,
                "trade_plan": None,
                "reasons": [
                    f"Daily loss limit breached ({loss_check['loss_percent']}% "
                    f">= {strategy.MAX_DAILY_LOSS_PERCENT}%). No more trades today."
                ],
            }

        # ---------- Guard: max trades per day ----------

        if check_trade_count_limit(trades_today_count):
            return {
                "decision": "BLOCKED",
                "signal": None,
                "trade_plan": None,
                "reasons": [
                    f"Max trades per day reached ({trades_today_count}/"
                    f"{strategy.MAX_TRADES_PER_DAY})."
                ],
            }

        if not candles_5m or not candles_15m:
            return {
                "decision": "NO_TRADE",
                "signal": None,
                "trade_plan": None,
                "reasons": ["Insufficient candle data."],
            }

        # ---------- Signal ----------

        if strategy.SIGNAL_MODE == "ORB":
            from app.signal_engine_orb import generate_orb_signal

            signal = generate_orb_signal(
                candles=candles_5m,
                # already_traded=trades_today_count >= strategy_orb.ORB_MAX_TRADES,
                already_traded=False,
                historical_candles=candles_15m,  # trend ke liye lookback
            )
            # Normalise ORB signal to same shape as EMA signal
            signal["trend"] = signal.get("reason", "ORB")
            signal["entry"] = {"reasons": [signal.get("reason", "")], "score": 0}
            signal["option_type"] = signal.get("option_type")
        else:
            indicators = calculate_indicators_multi_timeframe(candles_5m, candles_15m)
            signal = generate_signal_v2(indicators["5m"], indicators["15m"])

        if signal["signal"] != "BUY":
            return {
                "decision": "NO_TRADE",
                "signal": signal,
                "trade_plan": None,
                "reasons": [
                    signal.get(
                        "reason", "No high-probability setup on current candles."
                    )
                ],
            }

        if signal["confidence"] < strategy.MIN_CONFIDENCE:
            return {
                "decision": "NO_TRADE",
                "signal": signal,
                "trade_plan": None,
                "reasons": [
                    f"Confidence {signal['confidence']} below threshold "
                    f"{strategy.MIN_CONFIDENCE}."
                ],
            }

        # ---------- Option Selection ----------

        chain, lot_size_map = self.option_service.get_option_chain(
            token, instrument_key
        )

        if not chain:
            return {
                "decision": "NO_TRADE",
                "signal": signal,
                "trade_plan": None,
                "reasons": ["Option chain unavailable."],
            }

        option = self.option_service.get_option(
            chain,
            option_type=signal["option_type"],
            moneyness=strategy.OPTION_MODE,
            lot_size_map=lot_size_map,
        )

        liquidity = self.option_service.check_liquidity(
            option,
            min_oi=strategy.MIN_OPTION_OI,
            max_spread_percent=strategy.MAX_SPREAD_PERCENT,
        )

        if not liquidity["liquid"]:
            return {
                "decision": "NO_TRADE",
                "signal": signal,
                "trade_plan": None,
                "reasons": ["Option not liquid enough."] + liquidity["reasons"],
            }

        # ---------- Trade Plan (Entry / SL / Target) ----------

        pseudo_signal = {
            "signal": "BUY",
            "confidence": signal["confidence"],
            "score": signal.get("entry", {}).get("score", 0),
            "reasons": signal.get("entry", {}).get("reasons", []),
        }

        trade_plan = calculate_trade_levels(pseudo_signal, option)

        if not trade_plan["trade"]:
            return {
                "decision": "NO_TRADE",
                "signal": signal,
                "trade_plan": None,
                "reasons": [trade_plan.get("reason", "Trade plan rejected.")],
            }

        # ---------- Position Sizing ----------

        risk_per_unit = trade_plan["risk"]

        if risk_per_unit <= 0:
            return {
                "decision": "NO_TRADE",
                "signal": signal,
                "trade_plan": None,
                "reasons": ["Invalid trade risk calculated."],
            }

        lots = calculate_position_size(
            capital=capital,
            risk_per_unit=risk_per_unit,
            lot_size=option["lot_size"],
        )

        if lots < 1:
            return {
                "decision": "NO_TRADE",
                "signal": signal,
                "trade_plan": None,
                "reasons": ["Insufficient capital for even one lot at current risk."],
            }

        trade_plan["quantity"] = lots * option["lot_size"]
        trade_plan["lots"] = lots
        trade_plan["lot_size"] = option["lot_size"]

        return {
            "decision": "TRADE",
            "signal": signal,
            "trade_plan": trade_plan,
            "option": option,
            "reasons": ["High-probability setup confirmed."] + reasons,
        }
