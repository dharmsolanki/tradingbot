from app.indicators import (
    ema,
    rsi,
    macd,
    atr,
    supertrend,
)

from app import strategy
from app.utils import get_logger

logger = get_logger(__name__)

import math


def calculate_indicators(candles):
    """
    Calculate all technical indicators.

    Parameters
    ----------
    candles : list

        Upstox candle format:
        [
            timestamp,
            open,
            high,
            low,
            close,
            volume,
            oi
        ]

    Returns
    -------
    dict
    """

    if not candles:
        raise ValueError("Candles list cannot be empty.")

    minimum_required = (
        max(
            strategy.EMA_SLOW,
            strategy.ATR_PERIOD,
            strategy.SUPERTREND_LENGTH,
            strategy.MACD_SLOW,
        )
        + 5
    )

    if len(candles) < minimum_required:
        raise ValueError(
            f"At least {minimum_required} candles required, got {len(candles)}."
        )

    # Upstox returns candles latest-first; indicators need chronological
    # (oldest-first) order. Sort defensively by timestamp so calculations
    # are always correct regardless of API ordering.
    candles = sorted(candles, key=lambda c: c[0])

    high = [c[2] for c in candles]
    low = [c[3] for c in candles]
    close = [c[4] for c in candles]

    ema_fast = ema(
        close,
        strategy.EMA_FAST,
    )

    ema_slow = ema(
        close,
        strategy.EMA_SLOW,
    )

    rsi_values = rsi(
        close,
        strategy.RSI_PERIOD,
    )

    macd_values = macd(
        close,
        strategy.MACD_FAST,
        strategy.MACD_SLOW,
        strategy.MACD_SIGNAL,
    )

    atr_values = atr(
        high,
        low,
        close,
        strategy.ATR_PERIOD,
    )

    st_values = supertrend(
        high,
        low,
        close,
        strategy.SUPERTREND_LENGTH,
        strategy.SUPERTREND_MULTIPLIER,
    )

    return {
        "ema_fast": ema_fast,
        "ema_slow": ema_slow,
        "rsi": rsi_values,
        "macd": macd_values,
        "atr": atr_values,
        "supertrend": st_values,
    }


def get_trend(indicators):
    """
    Determine higher timeframe trend.

    Returns:
        {
            "trend": "BULLISH" | "BEARISH" | "SIDEWAYS",
            "score": int,
            "reasons": list[str]
        }
    """

    reasons = []
    score = 0

    ema_fast = indicators["ema_fast"][-1]
    ema_slow = indicators["ema_slow"][-1]

    st_direction = indicators["supertrend"]["direction"][-1]

    # EMA Trend
    if ema_fast > ema_slow:
        score += 60
        reasons.append("EMA Bullish")

    elif ema_fast < ema_slow:
        score -= 60
        reasons.append("EMA Bearish")

    # SuperTrend
    if st_direction == 1:
        score += 40
        reasons.append("SuperTrend Bullish")

    elif st_direction == -1:
        score -= 40
        reasons.append("SuperTrend Bearish")

    if score >= 80:
        trend = "BULLISH"

    elif score <= -80:
        trend = "BEARISH"

    else:
        trend = "SIDEWAYS"

    return {
        "trend": trend,
        "score": score,
        "reasons": reasons,
    }


def get_entry(indicators):
    """
    Determine entry signal from lower timeframe indicators.

    Returns:
        {
            "entry": "BUY" | "SELL" | "WAIT",
            "score": int,
            "reasons": list[str]
        }
    """

    reasons = []
    score = 0

    ema_fast = indicators["ema_fast"]
    ema_slow = indicators["ema_slow"]

    macd_line = indicators["macd"]["macd"]
    signal_line = indicators["macd"]["signal"]

    rsi_values = indicators["rsi"]

    # Need at least 2 values for crossover detection
    if len(ema_fast) < 2 or len(macd_line) < 2:
        return {
            "entry": "WAIT",
            "score": 0,
            "reasons": ["Not enough data"],
        }

    # EMA Crossover
    if ema_fast[-2] <= ema_slow[-2] and ema_fast[-1] > ema_slow[-1]:
        score += 40
        reasons.append("Fresh EMA Bullish Crossover")

    elif ema_fast[-2] >= ema_slow[-2] and ema_fast[-1] < ema_slow[-1]:
        score -= 40
        reasons.append("Fresh EMA Bearish Crossover")

    # MACD Crossover
    if macd_line[-2] <= signal_line[-2] and macd_line[-1] > signal_line[-1]:
        score += 30
        reasons.append("Fresh MACD Bullish Crossover")

    elif macd_line[-2] >= signal_line[-2] and macd_line[-1] < signal_line[-1]:
        score -= 30
        reasons.append("Fresh MACD Bearish Crossover")

    # RSI Filter
    rsi = rsi_values[-1]

    if not (0 <= rsi <= 100):
        return {
            "entry": "WAIT",
            "score": 0,
            "reasons": ["Invalid RSI value"],
        }

    if 55 <= rsi <= 70:
        score += 30
        reasons.append(f"RSI Strong Bullish ({rsi:.2f})")

    elif 30 <= rsi <= 45:
        score -= 30
        reasons.append(f"RSI Strong Bearish ({rsi:.2f})")

    if score >= 60:
        entry = "BUY"

    elif score <= -60:
        entry = "SELL"

    else:
        entry = "WAIT"

    return {
        "entry": entry,
        "score": score,
        "reasons": reasons,
    }


def generate_signal(indicators):
    """
    Generate trading signal from calculated indicators.
    """

    score = 0
    reasons = []

    # ---------- Latest Indicator Values ----------

    ema_fast = indicators["ema_fast"][-1]
    ema_slow = indicators["ema_slow"][-1]

    rsi_value = indicators["rsi"][-1]

    macd_value = indicators["macd"]["macd"][-1]
    signal_value = indicators["macd"]["signal"][-1]

    atr_value = indicators["atr"][-1]

    direction = indicators["supertrend"]["direction"][-1]

    # ---------- Indicator Validation ----------

    values = [
        ema_fast,
        ema_slow,
        rsi_value,
        macd_value,
        signal_value,
        atr_value,
        direction,
    ]

    def _invalid(v):
        return v is None or (isinstance(v, float) and math.isnan(v))

    if any(_invalid(v) for v in values):
        return {
            "signal": "NO_TRADE",
            "option_type": None,
            "score": 0,
            "confidence": 0,
            "reasons": ["Invalid indicator values."],
        }

    # ---------- EMA ----------

    if ema_fast > ema_slow:
        score += 30
        reasons.append("EMA Bullish")

    elif ema_fast < ema_slow:
        score -= 30
        reasons.append("EMA Bearish")

    # ---------- RSI ----------

    if rsi_value > strategy.RSI_BUY_LEVEL:
        score += 20
        reasons.append(f"RSI Bullish ({rsi_value:.2f})")

    elif rsi_value < strategy.RSI_SELL_LEVEL:
        score -= 20
        reasons.append(f"RSI Bearish ({rsi_value:.2f})")

    # ---------- MACD ----------

    if macd_value > signal_value:
        score += 20
        reasons.append(f"MACD Bullish ({macd_value:.2f} > {signal_value:.2f})")

    elif macd_value < signal_value:
        score -= 20
        reasons.append(f"MACD Bearish ({macd_value:.2f} < {signal_value:.2f})")

    # ---------- SuperTrend ----------

    if direction == 1:
        score += 30
        reasons.append("SuperTrend Bullish")

    elif direction == -1:
        score -= 30
        reasons.append("SuperTrend Bearish")

    # ---------- ATR Filter ----------

    if atr_value < strategy.MIN_ATR:
        return {
            "signal": "NO_TRADE",
            "option_type": None,
            "score": score,
            "confidence": abs(score),
            "reasons": reasons
            + [f"ATR too low ({atr_value:.2f} < {strategy.MIN_ATR})"],
        }

    # ---------- Final Decision ----------

    if score >= strategy.MIN_CONFIDENCE:
        return {
            "signal": "BUY",
            "option_type": "CE",
            "score": score,
            "confidence": abs(score),
            "reasons": reasons,
        }

    if score <= -strategy.MIN_CONFIDENCE:
        return {
            "signal": "BUY",
            "option_type": "PE",
            "score": score,
            "confidence": abs(score),
            "reasons": reasons,
        }

    return {
        "signal": "NO_TRADE",
        "option_type": None,
        "score": score,
        "confidence": abs(score),
        "reasons": reasons,
    }


def calculate_indicators_multi_timeframe(
    candles_5m,
    candles_15m,
):
    """
    Calculate indicators for both 5m and 15m timeframes.
    """

    return {
        "5m": calculate_indicators(candles_5m),
        "15m": calculate_indicators(candles_15m),
    }


def calculate_confidence(trend, entry):
    """
    Combine trend and entry scores into a confidence score.
    """

    score = abs(trend["score"]) * 0.6 + abs(entry["score"]) * 0.4

    confidence = min(100, round(score))

    return confidence


def generate_signal_v2(indicators_5m, indicators_15m):
    """
    Multi-timeframe signal generator.
    """

    trend = get_trend(indicators_15m)

    entry = get_entry(indicators_5m)

    confidence = calculate_confidence(
        trend,
        entry,
    )

    if confidence < strategy.MIN_CONFIDENCE:
        return {
            "signal": "NO_TRADE",
            "confidence": confidence,
            "trend": trend,
            "entry": entry,
        }

    # Trend mismatch
    if trend["trend"] == "BULLISH" and entry["entry"] != "BUY":
        logger.debug(
            "Signal rejected | trend=%s entry=%s confidence=%s",
            trend["trend"],
            entry["entry"],
            confidence,
        )
        return {
            "signal": "NO_TRADE",
            "confidence": confidence,
            "trend": trend,
            "entry": entry,
        }

    if trend["trend"] == "BEARISH" and entry["entry"] != "SELL":
        logger.debug(
            "Signal rejected | trend=%s entry=%s confidence=%s",
            trend["trend"],
            entry["entry"],
            confidence,
        )
        return {
            "signal": "NO_TRADE",
            "confidence": confidence,
            "trend": trend,
            "entry": entry,
        }

    if trend["trend"] == "BULLISH":
        return {
            "signal": "BUY",
            "option_type": "CE",
            "confidence": confidence,
            "trend": trend,
            "entry": entry,
        }

    if trend["trend"] == "BEARISH":
        return {
            "signal": "BUY",
            "option_type": "PE",
            "confidence": confidence,
            "trend": trend,
            "entry": entry,
        }

    return {
        "signal": "NO_TRADE",
        "confidence": confidence,
        "trend": trend,
        "entry": entry,
    }
