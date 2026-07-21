from app.auth import UpstoxAuth
from app.market_data import MarketData

auth = UpstoxAuth()
token = auth.get_token()

market = MarketData()

candles = market.get_latest_candles(
    token=token,
    instrument_key="NSE_INDEX|Nifty 50",
)

print("Total Candles:", len(candles))

print("\nLatest Candle:")
print(candles[0])

print("\nOldest Candle:")
print(candles[-1])
