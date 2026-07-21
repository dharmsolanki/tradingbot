from app.auth import UpstoxAuth
from app.market_data import MarketData

auth = UpstoxAuth()
market = MarketData()

token = auth.get_token()

contracts = market.get_option_contracts(
    token=token,
    instrument_key="NSE_INDEX|Nifty 50",
)

nearest_expiry = min(c["expiry"] for c in contracts)

chain = market.get_option_chain(
    token=token,
    instrument_key="NSE_INDEX|Nifty 50",
    expiry_date=nearest_expiry,
)

print(f"Nearest Expiry : {nearest_expiry}")
print(f"Total Contracts: {len(contracts)}")
print(f"Option Chain   : {len(chain)}")
print(chain[0])
