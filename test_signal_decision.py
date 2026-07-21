from pprint import pprint

from app.auth import UpstoxAuth
from app.market_data import MarketData
from app.signal_engine import (
    calculate_indicators,
    generate_signal,
)

auth = UpstoxAuth()
token = auth.get_token()

market = MarketData()

candles = market.get_intraday_candles(
    token=token,
    instrument_key="NSE_INDEX|Nifty 50",
)

indicators = calculate_indicators(candles)

signal = generate_signal(indicators)

print()

pprint(signal)
