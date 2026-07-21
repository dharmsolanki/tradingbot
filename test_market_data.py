from app.auth import UpstoxAuth
from app.market_data import MarketData

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

print(f"5m Candles : {len(candles_5m)}")
print(f"15m Candles: {len(candles_15m)}")

if candles_5m:
    print("Latest 5m:", candles_5m[0])

if candles_15m:
    print("Latest 15m:", candles_15m[0])
