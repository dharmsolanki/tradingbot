"""
backtest_orb.py

Backtests the ORB strategy using Upstox historical data.
No existing files modified.

Run:
    py backtest_orb.py
"""

from __future__ import annotations
from collections import defaultdict
from app.auth import UpstoxAuth
from app.market_data import MarketData
from app.signal_engine_orb import generate_orb_signal
from app.constants import TRADE_OPEN

INSTRUMENT_KEY = "NSE_INDEX|Nifty 50"
LOOKBACK_DAYS = 30


def group_by_day(candles: list) -> dict:
    days = defaultdict(list)
    for c in candles:
        days[c[0][:10]].append(c)
    return dict(sorted(days.items()))


def simulate(
    candles_after: list,
    option_type: str,
    sl: float,
    target: float,
) -> str:
    for c in candles_after:
        if option_type == "CE":
            if c[3] <= sl:
                return "LOSS"
            if c[2] >= target:
                return "WIN"
        else:
            if c[2] >= sl:
                return "LOSS"
            if c[3] <= target:
                return "WIN"
    return TRADE_OPEN


def run() -> None:
    print("=" * 60)
    print("ORB BACKTEST — Last", LOOKBACK_DAYS, "days")
    print("Instrument:", INSTRUMENT_KEY)
    print("=" * 60)

    auth = UpstoxAuth()
    market = MarketData()
    token = auth.get_token()

    print("Fetching candles...")
    candles_all = market.get_historical_candles(
        token=token,
        instrument_key=INSTRUMENT_KEY,
        unit="minutes",
        interval=5,
        days=LOOKBACK_DAYS,
    )

    if not candles_all:
        print("ERROR: No data.")
        return

    candles_all = sorted(candles_all, key=lambda c: c[0])
    days = group_by_day(candles_all)
    print(f"Data: {len(days)} trading days\n")

    results = []
    wins = losses = opens = 0

    for date, day_candles in days.items():
        signal_taken = False

        hist = [c for c in candles_all if c[0][:10] < date]
        for i in range(1, len(day_candles)):
            candles_so_far = day_candles[: i + 1]
            # Historical candles for trend lookback (all candles before today)
            try:
                signal = generate_orb_signal(
                    candles=candles_so_far,
                    already_traded=signal_taken,
                    historical_candles=hist,
                )
            except Exception as exc:
                print(f"Signal generation failed: {exc}")
                continue

            if signal["signal"] != "BUY":
                continue

            entry = signal["entry"]
            sl = signal["stop_loss"]
            target = signal["target"]
            option_type = signal["option_type"]

            future = day_candles[i + 1 :]
            outcome = simulate(future, option_type, sl, target)

            results.append(
                {
                    "date": date,
                    "time": day_candles[i][0][11:16],
                    "type": option_type,
                    "entry": entry,
                    "sl": sl,
                    "target": target,
                    "range_h": signal["range_high"],
                    "range_l": signal["range_low"],
                    "outcome": outcome,
                    "reason": signal["reason"],
                }
            )

            if outcome == "WIN":
                wins += 1
            elif outcome == "LOSS":
                losses += 1
            else:
                opens += 1

            signal_taken = True
            break  # one trade per day

    print(
        f"{'Date':<12} {'Time':<6} {'Type':<4} {'Entry':>8} {'SL':>8} {'Target':>9} {'Result'}"
    )
    print("-" * 65)
    for r in results:
        print(
            f"{r['date']:<12} {r['time']:<6} {r['type']:<4} {r['entry']:>8.1f} {r['sl']:>8.1f} {r['target']:>9.1f} {r['outcome']}"
        )

    total = len(results)
    print("-" * 65)
    print(f"\nTotal Signals : {total}")
    print(f"Wins          : {wins}")
    print(f"Losses        : {losses}")
    print(f"Open/Unclear  : {opens}")
    if total > 0:
        print(f"Win Rate      : {round(wins/total*100,1)}%")
    else:
        print("Win Rate      : N/A")
    print("\nDone.")


if __name__ == "__main__":
    run()
