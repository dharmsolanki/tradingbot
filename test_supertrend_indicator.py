from app.auth import UpstoxAuth
from app.market_data import MarketData
from app.indicators import supertrend

auth = UpstoxAuth()
token = auth.get_token()

market = MarketData()

candles = market.get_intraday_candles(
    token=token,
    instrument_key="NSE_INDEX|Nifty 50",
)

high = [c[2] for c in candles]
low = [c[3] for c in candles]
close = [c[4] for c in candles]

st = supertrend(
    high,
    low,
    close,
)

print(st["supertrend"][:10])
print(st["direction"][:10])
