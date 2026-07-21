from app.auth import UpstoxAuth
from app.market_data import MarketData
from app.signal_engine import (
    calculate_indicators_multi_timeframe,
    generate_signal_v2,
)

auth = UpstoxAuth()
market = MarketData()

token = auth.get_token()

candles = market.get_multi_timeframe_candles(
    token=token,
    instrument_key="NSE_INDEX|Nifty 50",
)

indicators = calculate_indicators_multi_timeframe(
    candles["5m"],
    candles["15m"],
)

signal = generate_signal_v2(
    indicators["5m"],
    indicators["15m"],
)

print(signal)
