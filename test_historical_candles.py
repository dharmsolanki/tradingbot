from pprint import pprint

from app.auth import UpstoxAuth
from app.market_data import MarketData

auth = UpstoxAuth()
token = auth.get_token()

market = MarketData()

data = market._get(
    endpoint="/v3/historical-candle/NSE_INDEX|Nifty 50/minutes/5/2026-07-17",
    token=token,
)

pprint(data)
