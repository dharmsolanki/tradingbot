from app.auth import UpstoxAuth
from app.market_data import MarketData

auth = UpstoxAuth()
market = MarketData()

token = auth.get_token()

candles = market.get_intraday_candles(
    token=token,
    instrument_key="NSE_INDEX|Nifty 50",
)

print(f"Total Candles: {len(candles)}")

print(candles[0])
