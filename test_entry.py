from app.auth import UpstoxAuth
from app.market_data import MarketData
from app.signal_engine import calculate_indicators, get_entry

auth = UpstoxAuth()
market = MarketData()

token = auth.get_token()

candles = market.get_latest_candles(
    token=token,
    instrument_key="NSE_INDEX|Nifty 50",
    interval=5,
)

indicators = calculate_indicators(candles)

entry = get_entry(indicators)

print(entry)
