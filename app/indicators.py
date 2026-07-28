from typing import Dict, List
from app.indicator_utils import true_range, wilder_smoothing

import numpy as np
import pandas as pd
import pandas_ta as ta


def sma(data: List[float], period: int) -> List[float]:
    """
    Calculate Simple Moving Average (SMA).

    Args:
        data: List of prices.
        period: SMA period.

    Returns:
        List containing SMA values.
        Values before enough data is available are np.nan.
    """

    if period <= 0:
        raise ValueError("Period must be greater than zero.")

    if len(data) < period:
        raise ValueError("Not enough data to calculate SMA.")

    prices = np.asarray(data, dtype=float)

    sma_values = np.full(len(prices), np.nan)

    for i in range(period - 1, len(prices)):
        sma_values[i] = prices[i - period + 1 : i + 1].mean()

    return sma_values.tolist()


def ema(data: List[float], period: int) -> List[float]:
    """
    Calculate Exponential Moving Average (EMA).

    Supports leading NaN values.

    Args:
        data: List of values.
        period: EMA period.

    Returns:
        List of EMA values.
    """

    if period <= 0:
        raise ValueError("Period must be greater than zero.")

    values = np.asarray(data, dtype=float)

    ema_values = np.full(len(values), np.nan)

    valid_idx = np.where(~np.isnan(values))[0]

    if len(valid_idx) < period:
        raise ValueError("Not enough valid data to calculate EMA.")

    start = valid_idx[0]

    first_window = values[start : start + period]

    ema_values[start + period - 1] = first_window.mean()

    multiplier = 2 / (period + 1)

    for i in range(start + period, len(values)):
        ema_values[i] = (values[i] - ema_values[i - 1]) * multiplier + ema_values[i - 1]

    return ema_values.tolist()


def rsi(data: List[float], period: int = 14) -> List[float]:
    """
    Calculate Relative Strength Index (RSI).

    Args:
        data: List of closing prices.
        period: RSI period.

    Returns:
        List of RSI values.
        Values before initialization are np.nan.
    """

    if period <= 0:
        raise ValueError("Period must be greater than zero.")

    if len(data) <= period:
        raise ValueError("Not enough data to calculate RSI.")

    prices = np.asarray(data, dtype=float)

    deltas = np.diff(prices)

    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    rsi_values = np.full(len(prices), np.nan)

    avg_gain = gains[:period].mean()
    avg_loss = losses[:period].mean()

    if avg_loss == 0:
        rsi_values[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi_values[period] = 100 - (100 / (1 + rs))

    for i in range(period + 1, len(prices)):
        avg_gain = ((avg_gain * (period - 1)) + gains[i - 1]) / period
        avg_loss = ((avg_loss * (period - 1)) + losses[i - 1]) / period

        if avg_loss == 0:
            rsi_values[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi_values[i] = 100 - (100 / (1 + rs))

    return rsi_values.tolist()


def macd(
    data: List[float],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> Dict[str, List[float]]:
    """
    Calculate MACD.

    Returns:
        {
            "macd": [...],
            "signal": [...],
            "histogram": [...]
        }
    """

    if fast_period >= slow_period:
        raise ValueError("fast_period must be smaller than slow_period.")

    if len(data) < slow_period:
        raise ValueError("Not enough data to calculate MACD.")

    fast = np.asarray(ema(data, fast_period), dtype=float)
    slow = np.asarray(ema(data, slow_period), dtype=float)

    macd_line = fast - slow

    signal_line = np.asarray(
        ema(macd_line.tolist(), signal_period),
        dtype=float,
    )

    histogram = macd_line - signal_line

    return {
        "macd": macd_line.tolist(),
        "signal": signal_line.tolist(),
        "histogram": histogram.tolist(),
    }


def atr(
    high: List[float],
    low: List[float],
    close: List[float],
    period: int = 14,
) -> List[float]:
    """
    Calculate Average True Range (ATR) using Wilder's smoothing.

    Args:
        high: High prices.
        low: Low prices.
        close: Closing prices.
        period: ATR period.

    Returns:
        List of ATR values.
        Values before initialization are np.nan.
    """

    if period <= 0:
        raise ValueError("Period must be greater than zero.")

    if not (len(high) == len(low) == len(close)):
        raise ValueError("Input lists must have the same length.")

    if len(close) <= period:
        raise ValueError("Not enough data to calculate ATR.")

    tr = true_range(high, low, close)

    atr_values = wilder_smoothing(tr, period)

    return atr_values.tolist()


def vwap(
    high: List[float],
    low: List[float],
    close: List[float],
    volume: List[float],
) -> List[float]:
    """
    Calculate Volume Weighted Average Price (VWAP).

    Args:
        high: High prices.
        low: Low prices.
        close: Closing prices.
        volume: Volume data.

    Returns:
        List of VWAP values.
    """

    if not (len(high) == len(low) == len(close) == len(volume)):
        raise ValueError("All input lists must have the same length.")

    if len(close) == 0:
        raise ValueError("Input data cannot be empty.")

    high = np.asarray(high, dtype=float)
    low = np.asarray(low, dtype=float)
    close = np.asarray(close, dtype=float)
    volume = np.asarray(volume, dtype=float)

    typical_price = (high + low + close) / 3

    tpv = typical_price * volume

    cumulative_tpv = np.cumsum(tpv)
    cumulative_volume = np.cumsum(volume)

    if np.any(cumulative_volume == 0):
        raise ValueError("Cumulative volume contains zero.")

    vwap_values = cumulative_tpv / cumulative_volume

    return vwap_values.tolist()


def supertrend(
    high: List[float],
    low: List[float],
    close: List[float],
    length: int = 10,
    multiplier: float = 3.0,
) -> Dict[str, List[float]]:
    """
    TradingView-compatible SuperTrend using pandas-ta.

    Returns:
    {
        "supertrend": [...],
        "direction": [...],
        "long": [...],
        "short": [...]
    }
    """

    if not (len(high) == len(low) == len(close)):
        raise ValueError("high, low and close must have the same length.")

    if len(close) < length:
        raise ValueError(f"Need at least {length} candles.")

    df = pd.DataFrame(
        {
            "high": high,
            "low": low,
            "close": close,
        }
    )

    # Candles are already in oldest -> newest order.
    # Do NOT reverse them.

    st = ta.supertrend(
        high=df["high"],
        low=df["low"],
        close=df["close"],
        length=length,
        multiplier=multiplier,
    )

    if st is None or st.empty:
        raise ValueError("Unable to calculate SuperTrend.")

    return {
        "supertrend": st[f"SUPERT_{length}_{multiplier}"].tolist(),
        "direction": st[f"SUPERTd_{length}_{multiplier}"].tolist(),
        "long": st[f"SUPERTl_{length}_{multiplier}"].tolist(),
        "short": st[f"SUPERTs_{length}_{multiplier}"].tolist(),
    }
