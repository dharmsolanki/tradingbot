from app.auth import UpstoxAuth
from app.market_data import MarketData
from app.option_service import OptionService

auth = UpstoxAuth()
token = auth.get_token()

market = MarketData()

contracts = market.get_option_contracts(
    token=token,
    instrument_key="NSE_INDEX|Nifty 50",
)

service = OptionService()

print()

print(service.get_available_expiries(contracts))

print()

print("Nearest Expiry :", service.get_nearest_expiry(contracts))
