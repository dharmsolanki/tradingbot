from app.auth import UpstoxAuth
from app.market_data import MarketData
from app.signal_engine import calculate_indicators_multi_timeframe

auth = UpstoxAuth()
market = MarketData()

token = auth.get_token()

candles_5m = market.get_latest_candles(
    token=token,
    instrument_key="NSE_INDEX|Nifty 50",
    interval=5,
)

candles_15m = market.get_latest_candles(
    token=token,
    instrument_key="NSE_INDEX|Nifty 50",
    interval=15,
)

indicators = calculate_indicators_multi_timeframe(
    candles_5m,
    candles_15m,
)

print(indicators.keys())
print(indicators["5m"].keys())
print(indicators["15m"].keys())
