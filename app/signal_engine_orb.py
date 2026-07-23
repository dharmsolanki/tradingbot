"""
signal_engine_orb.py

Opening Range Breakout signal engine.

Logic:
  1. Identify the Opening Range (9:15 to ORB_END_TIME candles)
  2. After range is set, scan each subsequent candle
  3. If close > range_high → BUY CE
  4. If close < range_low  → BUY PE
  5. SL = opposite end of range
  6. Target = entry + (risk × ORB_RISK_REWARD)

No existing files are modified.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from app import strategy_orb as orb_config


def get_opening_range(candles: List[List]) -> Optional[Dict[str, Any]]:
    """
    Extract opening range from candles.

    Args:
        candles: Sorted chronologically. Each candle:
                 [timestamp, open, high, low, close, volume, oi]

    Returns:
        {"high": float, "low": float, "candles_used": int} or None
    """

    range_candles = [
        c
        for c in candles
        if c[0][11:16] >= "09:15" and c[0][11:16] <= orb_config.ORB_END_TIME
    ]

    if not range_candles:
        return None

    range_high = max(c[2] for c in range_candles)  # highest high
    range_low = min(c[3] for c in range_candles)  # lowest low
    range_size = range_high - range_low

    if range_size < orb_config.ORB_MIN_RANGE_POINTS:
        return None

    # Skip if range is too wide — SL will be unreachable
    if range_size > orb_config.ORB_MAX_RANGE_POINTS:
        return None

    return {
        "high": range_high,
        "low": range_low,
        "size": round(range_size, 2),
        "candles_used": len(range_candles),
    }


def generate_orb_signal(
    candles: List[List],
    already_traded: bool = False,
) -> Dict[str, Any]:
    """
    Generate ORB signal from a chronologically sorted 5m candle list.

    Args:
        candles: All candles for the day so far (sorted oldest first).
        already_traded: True if a trade has already been taken today.

    Returns:
        {
            "signal": "BUY" | "NO_TRADE",
            "option_type": "CE" | "PE" | None,
            "entry": float | None,
            "stop_loss": float | None,
            "target": float | None,
            "range_high": float | None,
            "range_low": float | None,
            "confidence": int,
            "reason": str,
        }
    """

    NO_TRADE = {
        "signal": "NO_TRADE",
        "option_type": None,
        "entry": None,
        "stop_loss": None,
        "target": None,
        "range_high": None,
        "range_low": None,
        "confidence": 0,
        "reason": "",
    }

    if already_traded:
        return {**NO_TRADE, "reason": "Max trades reached for today."}

    candles = sorted(candles, key=lambda c: c[0])

    # No trades after cutoff time (check AFTER sort so [-1] is truly latest)
    if candles and candles[-1][0][11:16] > orb_config.ORB_SIGNAL_CUTOFF:
        return {**NO_TRADE, "reason": "Past signal cutoff time."}

    opening_range = get_opening_range(candles)

    if opening_range is None:
        return {**NO_TRADE, "reason": "Opening range not established yet."}

    # Only look at candles AFTER the opening range
    post_range = [c for c in candles if c[0][11:16] > orb_config.ORB_END_TIME]

    if not post_range:
        return {**NO_TRADE, "reason": "Waiting for post-range candles."}

    latest = post_range[-1]
    close = latest[4]

    range_high = opening_range["high"]
    range_low = opening_range["low"]
    range_size = opening_range["size"]

    # CE breakout — close above range high
    if close > range_high:
        sl = range_low
        risk = close - sl
        target = round(close + risk * orb_config.ORB_RISK_REWARD, 2)
        return {
            "signal": "BUY",
            "option_type": "CE",
            "entry": round(close, 2),
            "stop_loss": round(sl, 2),
            "target": target,
            "range_high": range_high,
            "range_low": range_low,
            "confidence": 85,
            "reason": f"Price closed above opening range high ({range_high}). Range size: {range_size} pts.",
        }

    # PE breakout — close below range low
    if close < range_low:
        sl = range_high
        risk = sl - close
        target = round(close - risk * orb_config.ORB_RISK_REWARD, 2)
        return {
            "signal": "BUY",
            "option_type": "PE",
            "entry": round(close, 2),
            "stop_loss": round(sl, 2),
            "target": target,
            "range_high": range_high,
            "range_low": range_low,
            "confidence": 85,
            "reason": f"Price closed below opening range low ({range_low}). Range size: {range_size} pts.",
        }

    return {
        **NO_TRADE,
        "reason": f"Price inside range ({range_low}–{range_high}). Waiting for breakout.",
    }
