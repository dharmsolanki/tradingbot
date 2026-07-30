"""
recommendation_engine.py

Wraps DecisionEngine output into a professional trading recommendation.

RecommendationEngine does NOT duplicate any signal, risk, or option
selection logic — it calls DecisionEngine.evaluate() and enriches the
result with:
  - Entry range (low/high band around LTP)
  - Target 2 (higher target from strategy.RISK_REWARD_RATIO_2)
  - Strategy name
  - Indicator snapshot for display
  - Lifecycle status tracking (WAITING → ACTIVE → TARGET_HIT / SL_HIT / CLOSED)

All values come from live Upstox API data via the existing pipeline.
Nothing is hardcoded or assumed.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from app import strategy
from app.config import INSTRUMENTS
from app.decision_engine import DecisionEngine
from app.market_data import MarketData
from app.notifier import Notification, NotificationService, format_recommendation
from app.utils import get_logger
from app.constants import TRADE_CLOSED
from app.constants import TARGET_HIT

logger = get_logger(__name__)

# Recommendation lifecycle statuses
STATUS_WAITING = "WAITING"  # Generated but entry not yet reached
STATUS_ACTIVE = "ACTIVE"  # Entry filled (live MTM tracking)
STATUS_TARGET_1_HIT = "TARGET_1_HIT"
STATUS_TARGET_HIT = TARGET_HIT
STATUS_SL_HIT = "SL_HIT"
STATUS_CLOSED = TRADE_CLOSED
STATUS_EXPIRED = "EXPIRED"  # Market closed without trigger


class RecommendationEngine:
    """
    Generates and lifecycle-manages professional trading recommendations.

    One recommendation can be active at a time per instrument. If no
    high-confidence setup is found, no recommendation is generated —
    quality over quantity is enforced by the underlying DecisionEngine.
    """

    def __init__(
        self,
        decision_engine: Optional[DecisionEngine] = None,
        market_data: Optional[MarketData] = None,
        notifier: Optional[NotificationService] = None,
    ) -> None:
        self.decision_engine = decision_engine or DecisionEngine()
        self.market = market_data or MarketData()
        self.notifier = notifier or NotificationService()

        # In-memory store: rec_id → recommendation dict.
        # Persisted to DB via main.py's state broadcast (dashboard reads
        # from /api/recommendations which serves this list).
        self._recommendations: Dict[str, Dict[str, Any]] = {}

    # ==========================
    # Public API
    # ==========================

    def try_generate(
        self,
        token: str,
        instrument_key: str,
        candles_5m: list,
        candles_15m: list,
        capital: float,
        realized_pnl_today: float,
        trades_today_count: int,
        has_open_trade: bool,
    ) -> Optional[Dict[str, Any]]:
        """
        Attempt to generate a recommendation for the current market state.

        Returns the recommendation dict if a high-confidence setup is
        found, or None if conditions are not met (no setup = no rec).

        Args:
            token: Live Upstox access token.
            instrument_key: Upstox instrument key (e.g. "NSE_INDEX|Nifty 50").
            candles_5m: 5-minute candle list (from market_data).
            candles_15m: 15-minute candle list.
            capital: Current virtual capital.
            realized_pnl_today: Today's realized P/L (for loss-limit check).
            trades_today_count: Number of trades taken today.
            has_open_trade: Whether a demo trade is already open.

        Returns:
            dict | None
        """

        result = self.decision_engine.evaluate(
            token=token,
            instrument_key=instrument_key,
            candles_5m=candles_5m,
            candles_15m=candles_15m,
            capital=capital,
            realized_pnl_today=realized_pnl_today,
            trades_today_count=trades_today_count,
            has_open_trade=has_open_trade,
        )

        if result["decision"] != "TRADE":
            return None

        # Prevent duplicate active recommendation for same instrument
        for rec in self._recommendations.values():
            if rec["instrument_key"] == instrument_key and rec["status"] in (
                STATUS_WAITING,
                STATUS_ACTIVE,
            ):
                logger.debug(
                    "Recommendation already active for %s. Skipping duplicate.",
                    instrument_key,
                )
                return rec

        rec = self._build_recommendation(result, instrument_key)

        self._recommendations[rec["rec_id"]] = rec

        self._dispatch_notification(rec)

        logger.info(
            "Recommendation generated: %s %s %s (confidence=%s%%)",
            rec["signal"],
            rec["instrument"],
            rec["strike"],
            rec["confidence"],
        )

        return rec

    def update_lifecycle(
        self,
        token: str,
        rec_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Check the live premium of an ACTIVE recommendation and update
        its status (TARGET_HIT, SL_HIT, etc.).

        Args:
            token: Live Upstox access token.
            rec_id: ID of the recommendation to update.

        Returns:
            Updated recommendation dict, or None if not found.
        """

        rec = self._recommendations.get(rec_id)

        if rec is None:
            return None

        if rec["status"] not in (STATUS_WAITING, STATUS_ACTIVE):
            return rec

        try:
            ltp = self.market.get_ltp(token, rec["instrument_key"])
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not fetch LTP for recommendation %s: %s", rec_id, exc)
            return rec

        rec["current_premium"] = ltp
        rec["live_pnl"] = round((ltp - rec["entry_mid"]) * rec.get("lot_size", 1), 2)

        if (
            rec["status"] == STATUS_WAITING
            and rec["entry_range"]["low"] <= ltp <= rec["entry_range"]["high"]
        ):
            rec["status"] = STATUS_ACTIVE
            rec["activated_at"] = datetime.now().isoformat()

        if rec["status"] == STATUS_ACTIVE:
            if ltp >= rec["target_2"]:
                rec["status"] = STATUS_TARGET_HIT
                rec["closed_at"] = datetime.now().isoformat()
            elif ltp >= rec["target_1"]:
                rec["status"] = STATUS_TARGET_1_HIT
            elif ltp <= rec["stop_loss"]:
                rec["status"] = STATUS_SL_HIT
                rec["closed_at"] = datetime.now().isoformat()

        return rec

    def expire_open(self) -> None:
        """
        Mark all still-open (WAITING/ACTIVE) recommendations as EXPIRED
        at end of day. Called by main.py when market closes.
        """

        for rec in self._recommendations.values():
            if rec["status"] in (STATUS_WAITING, STATUS_ACTIVE):
                rec["status"] = STATUS_EXPIRED
                rec["closed_at"] = datetime.now().isoformat()

    def cleanup_old(self, keep_days: int = 7) -> None:
        """
        Remove old recommendations from memory.
        Keeps only recent recommendations.
        """

        cutoff = datetime.now().timestamp() - (keep_days * 86400)

        remove = []

        for rec_id, rec in self._recommendations.items():
            try:
                ts = datetime.fromisoformat(rec["generated_at"]).timestamp()
            except Exception:
                remove.append(rec_id)
                continue

            if ts < cutoff:
                remove.append(rec_id)

        for rec_id in remove:
            self._recommendations.pop(rec_id, None)

        if remove:
            logger.info("Removed %d old recommendations", len(remove))

    def today_recommendations(self) -> List[Dict[str, Any]]:
        """Return all recommendations generated today, newest first."""

        today = datetime.now().strftime("%Y-%m-%d")

        return [
            r
            for r in sorted(
                self._recommendations.values(),
                key=lambda x: x["generated_at"],
                reverse=True,
            )
            if r["generated_at"].startswith(today)
        ]

    def all_recommendations(self) -> List[Dict[str, Any]]:
        """Return all recommendations (all days), newest first."""

        return sorted(
            self._recommendations.values(),
            key=lambda x: x["generated_at"],
            reverse=True,
        )

    def get_recommendation(
        self,
        rec_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Return a recommendation by its ID.
        """

        return self._recommendations.get(rec_id)

    # ==========================
    # Internal Helpers
    # ==========================

    def _build_recommendation(
        self,
        decision_result: Dict[str, Any],
        instrument_key: str,
    ) -> Dict[str, Any]:
        """
        Enrich a TRADE decision result into a full recommendation dict.
        All numerical values come from the live decision pipeline —
        nothing is hardcoded.
        """

        signal = decision_result["signal"]
        trade_plan = decision_result["trade_plan"]
        option = decision_result["option"]

        entry_mid = option["ltp"]
        entry_range_width = entry_mid * strategy.ENTRY_RANGE_PERCENT / 100

        entry_range = {
            "low": round(entry_mid - entry_range_width, 1),
            "high": round(entry_mid + entry_range_width, 1),
        }

        risk = entry_mid - trade_plan["stop_loss"]
        target_2 = round(entry_mid + (risk * strategy.RISK_REWARD_RATIO_2), 1)

        instrument_name = _instrument_name(instrument_key)

        indicators = signal.get("indicators", {})

        rec = {
            "rec_id": str(uuid.uuid4()),
            "instrument": instrument_name,
            "instrument_key": option["instrument_key"],
            "signal": f"BUY {instrument_name} {int(option['strike'])} {option['option_type']}",
            "option_type": option["option_type"],
            "strike": int(option["strike"]),
            "expiry": option["expiry"],
            "lot_size": option["lot_size"],
            "entry_range": entry_range,
            "entry_mid": entry_mid,
            "stop_loss": trade_plan["stop_loss"],
            "target_1": trade_plan["target"],
            "target_2": target_2,
            "rr_ratio": strategy.RISK_REWARD_RATIO,
            "confidence": signal["confidence"],
            "strategy_name": strategy.STRATEGY_NAME,
            "market_trend": signal.get("trend", "—"),
            "reasons": list(
                dict.fromkeys(
                    decision_result.get("reasons", [])
                    + signal.get("entry", {}).get("reasons", [])
                )
            ),
            "indicators": {
                "ema_fast": indicators.get("ema_fast"),
                "ema_slow": indicators.get("ema_slow"),
                "rsi": indicators.get("rsi"),
                "macd": indicators.get("macd"),
                "atr": indicators.get("atr"),
            },
            "quantity": trade_plan["quantity"],
            "lots": trade_plan["lots"],
            "status": STATUS_WAITING,
            "current_premium": entry_mid,
            "live_pnl": 0.0,
            "generated_at": datetime.now().isoformat(),
            "activated_at": None,
            "closed_at": None,
        }

        return rec

    def _dispatch_notification(self, rec: Dict[str, Any]) -> None:
        """Send a notification when a new recommendation is generated."""

        body = format_recommendation(rec)

        self.notifier.notify(
            Notification(
                event="RECOMMENDATION_GENERATED",
                title=rec["signal"],
                body=body,
                metadata={
                    "rec_id": rec["rec_id"],
                    "confidence": rec["confidence"],
                    "instrument": rec["instrument"],
                },
            )
        )


def _instrument_name(instrument_key: str) -> str:
    """Reverse-lookup instrument key to friendly name (e.g. NIFTY)."""

    for name, key in INSTRUMENTS.items():
        if key == instrument_key:
            return name

    return instrument_key.split("|")[-1]
