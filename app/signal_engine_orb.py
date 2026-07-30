"""
signal_engine_orb.py

Opening Range Breakout (ORB) signal engine.

Features:
- Opening Range detection
- EMA trend filter
- Counter-trend filtering
- Configurable Risk:Reward target
- Confidence scoring
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from app import strategy_orb as orb_config
from app import strategy
from app.utils import get_logger

logger = get_logger(__name__)


def get_opening_range(candles: List[List]) -> Optional[Dict[str, Any]]:
    """Extract opening range from 9:15-ORB_END_TIME candles."""

    range_candles = [
        c
        for c in candles
        if c[0][11:16] >= "09:15" and c[0][11:16] <= orb_config.ORB_END_TIME
    ]

    if not range_candles:
        return None

    range_high = max(c[2] for c in range_candles)
    range_low = min(c[3] for c in range_candles)
    range_size = range_high - range_low

    if range_size < orb_config.ORB_MIN_RANGE_POINTS:
        return None

    if range_size > orb_config.ORB_MAX_RANGE_POINTS:
        return None

    return {
        "high": range_high,
        "low": range_low,
        "size": round(range_size, 2),
        "candles_used": len(range_candles),
    }


def get_trend(candles: List[List]) -> Optional[str]:
    """
    Determine trend using EMA crossover.
    Uses ALL available candles (historical + intraday) for accuracy.
    Returns BULLISH, BEARISH, SIDEWAYS, or None if not enough data.
    """

    if len(candles) < strategy.EMA_SLOW:
        return None

    closes = [c[4] for c in candles]

    # Simple EMA calculation without pandas_ta dependency
    def calc_ema(prices, period):
        if not prices:
            raise ValueError("prices cannot be empty.")
        k = 2 / (period + 1)
        ema = prices[0]
        for price in prices[1:]:
            ema = price * k + ema * (1 - k)
        return ema

    ema_fast = calc_ema(closes, strategy.EMA_FAST)
    ema_slow = calc_ema(closes, strategy.EMA_SLOW)

    diff = ema_fast - ema_slow
    threshold = closes[-1] * 0.0002  # 0.02% threshold to avoid SIDEWAYS noise

    if diff > threshold:
        return "BULLISH"
    elif diff < -threshold:
        return "BEARISH"
    else:
        return "SIDEWAYS"


def generate_orb_signal(
    candles: List[List],
    already_traded: bool = False,
    historical_candles: Optional[List[List]] = None,
) -> Dict[str, Any]:
    """
    Generate ORB signal.

    Args:
        candles: Today's intraday 5m candles (sorted oldest first).
        already_traded: True if trade already taken today.
        historical_candles: Optional — recent historical candles for
                            trend calculation (provides EMA_SLOW lookback).
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
    for candle in candles:
        if len(candle) < 5:
            return {
                **NO_TRADE,
                "reason": "Invalid candle data.",
            }

    # Cutoff time check
    if candles and candles[-1][0][11:16] > orb_config.ORB_SIGNAL_CUTOFF:
        return {**NO_TRADE, "reason": "Past signal cutoff time."}

    # Opening range
    opening_range = get_opening_range(candles)
    if opening_range is None:
        return {**NO_TRADE, "reason": "Opening range not established yet."}

    # Post-range candles only
    post_range = [c for c in candles if c[0][11:16] > orb_config.ORB_END_TIME]
    if not post_range:
        return {**NO_TRADE, "reason": "Waiting for post-range candles."}

    latest = post_range[-1]
    close = latest[4]

    range_high = opening_range["high"]
    range_low = opening_range["low"]
    range_size = opening_range["size"]

    # Trend — use historical + intraday combined for enough EMA lookback
    all_candles = sorted((historical_candles or []) + candles, key=lambda c: c[0])
    trend_direction = get_trend(all_candles)

    logger.info(
        "ORB DEBUG | Close=%.2f | RangeHigh=%.2f | RangeLow=%.2f | Trend=%s",
        close,
        range_high,
        range_low,
        trend_direction,
    )

    # Confidence based on trend alignment
    def confidence(option_type):
        if trend_direction == "BULLISH" and option_type == "CE":
            return 90
        if trend_direction == "BEARISH" and option_type == "PE":
            return 90
        if trend_direction == "SIDEWAYS" or trend_direction is None:
            return 78  # below 80 will be blocked by MIN_CONFIDENCE
        return 70  # counter-trend — low confidence, will be blocked

    # -----------------------------------------
    # Breakout Confirmation
    # -----------------------------------------

    if orb_config.ORB_CONFIRMATION == "CLOSE":
        ce_breakout = close > range_high
        pe_breakout = close < range_low

    elif orb_config.ORB_CONFIRMATION == "HIGH_LOW":
        ce_breakout = latest[2] > range_high  # Candle High
        pe_breakout = latest[3] < range_low  # Candle Low

    else:
        ce_breakout = False
        pe_breakout = False

    # CE Breakout
    if ce_breakout:
        logger.info(
            "ORB BUY CE | Close=%.2f crossed RangeHigh=%.2f",
            close,
            range_high,
        )

        if trend_direction == "BEARISH":
            return {
                **NO_TRADE,
                "reason": "CE breakout but trend BEARISH — counter-trend, skipping.",
            }

        sl = round(latest[3] - 10, 2)
        risk = close - sl

        if risk <= 0:
            return {
                **NO_TRADE,
                "reason": "Invalid SL — candle low above close.",
            }

        conf = confidence("CE")

        return {
            "signal": "BUY",
            "option_type": "CE",
            "entry": round(close, 2),
            "stop_loss": sl,
            "target": round(close + risk * orb_config.ORB_RISK_REWARD, 2),
            "range_high": range_high,
            "range_low": range_low,
            "confidence": conf,
            "reason": f"ORB CE breakout | Trend: {trend_direction} | Range: {range_low}-{range_high} ({range_size} pts)",
        }

    # PE Breakout
    if pe_breakout:
        logger.info(
            "ORB BUY PE | Close=%.2f crossed RangeLow=%.2f",
            close,
            range_low,
        )

        if trend_direction == "BULLISH":
            return {
                **NO_TRADE,
                "reason": "PE breakout but trend BULLISH — counter-trend, skipping.",
            }

        sl = round(latest[2] + 10, 2)
        risk = sl - close

        if risk <= 0:
            return {
                **NO_TRADE,
                "reason": "Invalid SL — candle high below close.",
            }

        conf = confidence("PE")

        return {
            "signal": "BUY",
            "option_type": "PE",
            "entry": round(close, 2),
            "stop_loss": sl,
            "target": round(close - risk * orb_config.ORB_RISK_REWARD, 2),
            "range_high": range_high,
            "range_low": range_low,
            "confidence": conf,
            "reason": f"ORB PE breakout | Trend: {trend_direction} | Range: {range_low}-{range_high} ({range_size} pts)",
        }

    logger.info(
        "ORB NO TRADE | Close=%.2f inside %.2f - %.2f",
        close,
        range_low,
        range_high,
    )
    return {
        **NO_TRADE,
        "reason": f"Price inside range ({range_low}–{range_high}). Waiting for breakout.",
    }
