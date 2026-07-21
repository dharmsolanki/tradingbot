from app.auth import UpstoxAuth
from app.market_data import MarketData
from app.signal_engine import (
    calculate_indicators,
    generate_signal,
)

auth = UpstoxAuth()
token = auth.get_token()

market = MarketData()

# Automatically uses intraday on market days
# and historical candles on weekends
candles = market.get_latest_candles(
    token=token,
    instrument_key="NSE_INDEX|Nifty 50",
)

# Calculate indicators
indicators = calculate_indicators(candles)

# Generate signal
signal = generate_signal(indicators)

print("=" * 60)
print("TRADING SIGNAL")
print("=" * 60)

print(f"Signal      : {signal['signal']}")
print(f"Option Type : {signal['option_type']}")
print(f"Score       : {signal['score']}")
print(f"Confidence  : {signal['confidence']}%")

print("\nReasons:")
for reason in signal["reasons"]:
    print(f" - {reason}")
