import numpy as np


def true_range(
    high: list[float],
    low: list[float],
    close: list[float],
) -> np.ndarray:
    """
    Calculate True Range.
    """

    high = np.asarray(high, dtype=float)
    low = np.asarray(low, dtype=float)
    close = np.asarray(close, dtype=float)

    if not (len(high) == len(low) == len(close)):
        raise ValueError("high, low and close must have the same length.")

    if len(close) == 0:
        raise ValueError("Input data cannot be empty.")

    tr = np.zeros(len(close))

    tr[0] = high[0] - low[0]

    for i in range(1, len(close)):
        tr[i] = max(
            high[i] - low[i],
            abs(high[i] - close[i - 1]),
            abs(low[i] - close[i - 1]),
        )

    return tr


def wilder_smoothing(
    values: np.ndarray,
    period: int,
) -> np.ndarray:
    """
    Wilder's Moving Average.
    """

    if period <= 0:
        raise ValueError("Period must be greater than zero.")

    if len(values) <= period:
        raise ValueError("Not enough data for Wilder smoothing.")

    result = np.full(len(values), np.nan)

    result[period] = values[: period + 1].mean()

    for i in range(period + 1, len(values)):
        result[i] = (result[i - 1] * (period - 1) + values[i]) / period

    return result
