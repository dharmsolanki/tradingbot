from pprint import pprint

from app.auth import UpstoxAuth
from app.market_data import MarketData

auth = UpstoxAuth()
token = auth.get_token()

market = MarketData()

contracts = market.get_option_contracts(
    token=token,
    instrument_key="NSE_INDEX|Nifty 50",
)

print(type(contracts))
print(len(contracts))

pprint(contracts[0])
expiries = sorted({c["expiry"] for c in contracts})

print(f"Total Expiries: {len(expiries)}")

print()

for expiry in expiries:
    print(expiry)
