"""
backtest.py

Standalone backtester using existing signal engine + live Upstox
historical data. No project code is modified — only reads data and
runs signals.

Run:
    python3 backtest.py

Output:
    - Total signals generated
    - Win rate (based on RR achieved)
    - Per-trade breakdown
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

from app.auth import UpstoxAuth
from app.market_data import MarketData
from app.signal_engine import (
    calculate_indicators,
    generate_signal_v2,
)
from app import strategy

# ==========================
# Config
# ==========================

INSTRUMENT_KEY = "NSE_INDEX|Nifty 50"
LOOKBACK_DAYS = 30  # How many days of history to test
CANDLE_INTERVAL_5M = 5
CANDLE_INTERVAL_15M = 15
MIN_RR = 1.5  # Minimum RR to count as "good" trade

# ==========================
# Helpers
# ==========================


def group_by_day(candles: list) -> dict:
    """Group candle list by date string."""
    days = defaultdict(list)
    for c in candles:
        date = c[0][:10]  # first 10 chars = YYYY-MM-DD
        days[date].append(c)
    return dict(sorted(days.items()))


def simulate_trade(
    candles_after_signal: list, option_type: str, entry: float, sl: float, target: float
) -> str:
    """
    Walk forward candle by candle after signal.
    CE: NIFTY must go UP to hit target, DOWN to hit SL.
    PE: NIFTY must go DOWN to hit target, UP to hit SL.
    """
    for c in candles_after_signal:
        low = c[3]
        high = c[2]
        if option_type == "CE":
            if low <= sl:
                return "LOSS"
            if high >= target:
                return "WIN"
        else:  # PE
            if high >= sl:
                return "LOSS"
            if low <= target:
                return "WIN"
    return "OPEN"


# ==========================
# Main
# ==========================


def run():
    print("=" * 60)
    print("BACKTEST — Last", LOOKBACK_DAYS, "days")
    print("Instrument:", INSTRUMENT_KEY)
    print("=" * 60)

    auth = UpstoxAuth()
    market = MarketData()
    token = auth.get_token()

    print("Fetching historical candles...")

    candles_5m_all = market.get_historical_candles(
        token=token,
        instrument_key=INSTRUMENT_KEY,
        unit="minutes",
        interval=CANDLE_INTERVAL_5M,
        days=LOOKBACK_DAYS,
    )

    candles_15m_all = market.get_historical_candles(
        token=token,
        instrument_key=INSTRUMENT_KEY,
        unit="minutes",
        interval=CANDLE_INTERVAL_15M,
        days=LOOKBACK_DAYS,
    )

    if not candles_5m_all or not candles_15m_all:
        print("ERROR: No candle data returned. Check token and instrument key.")
        return

    # Sort ascending (oldest first)
    candles_5m_all = sorted(candles_5m_all, key=lambda c: c[0])
    candles_15m_all = sorted(candles_15m_all, key=lambda c: c[0])

    days_5m = group_by_day(candles_5m_all)
    days_15m = group_by_day(candles_15m_all)

    print(f"Data loaded: {len(days_5m)} trading days\n")

    # Build a full sorted 15m candle list for rolling trend calculation
    all_15m_sorted = sorted(candles_15m_all, key=lambda c: c[0])

    # ==========================
    # Per-day signal scan
    # ==========================

    results = []
    total_signals = 0
    wins = 0
    losses = 0
    opens = 0

    MIN_CANDLES_PER_DAY = 20  # ~1.5 hrs warmup within the day

    for date in sorted(days_5m.keys()):
        day_5m = days_5m[date]
        day_15m = days_15m.get(date, [])

        if not day_15m:
            continue

        # For trend: use all 15m candles UP TO end of this day
        # (walk-forward — no future data)
        day_end = date + "T23:59:59"
        rolling_15m = [c for c in all_15m_sorted if c[0] <= day_end]

        if len(rolling_15m) < strategy.EMA_SLOW:
            continue

        # Scan each candle of the day (walk-forward, no lookahead)
        for i in range(MIN_CANDLES_PER_DAY, len(day_5m)):
            candles_5m_slice = day_5m[: i + 1]
            candles_15m_slice = rolling_15m

            try:
                ind_5m = calculate_indicators(candles_5m_slice)
                ind_15m = calculate_indicators(candles_15m_slice)
                signal = generate_signal_v2(ind_5m, ind_15m)
            except Exception:
                continue

            # Debug: print every non-zero score so we can see how close
            # we are to generating signals
            trend_score = (
                signal.get("trend", {}).get("score", 0)
                if isinstance(signal.get("trend"), dict)
                else 0
            )
            entry_score = (
                signal.get("entry", {}).get("score", 0)
                if isinstance(signal.get("entry"), dict)
                else 0
            )
            if i == MIN_CANDLES_PER_DAY:  # print first candle of each day
                print(
                    f"  {date} {day_5m[i][0][11:16]} | trend={signal.get('trend',{}).get('trend','?')}({trend_score}) entry={signal.get('entry',{}).get('entry','?')}({entry_score}) conf={signal.get('confidence','?')}"
                )

            if signal["signal"] != "BUY":
                continue

            if signal["confidence"] < strategy.MIN_CONFIDENCE:
                continue

            # Signal found — simulate trade
            entry_candle = day_5m[i]
            entry_price = entry_candle[4]  # NIFTY spot close

            # SL/Target on NIFTY index points (not option premium)
            # Using fixed point-based levels typical for intraday
            SL_POINTS = 50  # 50 NIFTY points SL
            TARGET_POINTS = 100  # 100 NIFTY points target (1:2 RR)

            if signal.get("option_type") == "CE":
                sl = entry_price - SL_POINTS
                target = entry_price + TARGET_POINTS
            else:  # PE
                sl = entry_price + SL_POINTS
                target = entry_price - TARGET_POINTS

            future_candles = day_5m[i + 1 :]
            outcome = simulate_trade(
                future_candles, signal.get("option_type", "CE"), entry_price, sl, target
            )

            total_signals += 1
            if outcome == "WIN":
                wins += 1
            elif outcome == "LOSS":
                losses += 1
            else:
                opens += 1

            results.append(
                {
                    "date": date,
                    "time": entry_candle[0][11:16],
                    "option_type": signal.get("option_type", "?"),
                    "entry": entry_price,
                    "sl": sl,
                    "target": target,
                    "confidence": signal["confidence"],
                    "outcome": outcome,
                    "trend": (
                        signal.get("trend", {}).get("trend", "?")
                        if isinstance(signal.get("trend"), dict)
                        else "?"
                    ),
                }
            )

            # Only one trade per day (like real trading)
            break

    # ==========================
    # Results
    # ==========================

    print(
        f"{'Date':<12} {'Time':<6} {'Type':<4} {'Entry':>8} {'SL':>8} {'Target':>8} {'Conf':>5} {'Trend':<10} {'Result'}"
    )
    print("-" * 80)

    for r in results:
        print(
            f"{r['date']:<12} {r['time']:<6} {r['option_type']:<4} "
            f"{r['entry']:>8.1f} {r['sl']:>8.1f} {r['target']:>8.1f} "
            f"{r['confidence']:>5} {r['trend']:<10} {r['outcome']}"
        )

    print("-" * 80)
    print(f"\nTotal Signals : {total_signals}")
    print(f"Wins          : {wins}")
    print(f"Losses        : {losses}")
    print(f"Open/Unclear  : {opens}")

    if total_signals > 0:
        win_rate = round(wins / total_signals * 100, 1)
        print(f"Win Rate      : {win_rate}%")
    else:
        print("Win Rate      : N/A (no signals)")

    print("\nDone.")


if __name__ == "__main__":
    run()
