from pprint import pprint

from app.auth import UpstoxAuth
from app.market_data import MarketData

auth = UpstoxAuth()
token = auth.get_token()

market = MarketData()

data = market.get_option_chain(
    token=token,
    instrument_key="NSE_INDEX|Nifty 50",
)

print(type(data))
print(len(data))

pprint(data[0])
