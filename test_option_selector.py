from pprint import pprint

from app.auth import UpstoxAuth
from app.option_service import OptionService

auth = UpstoxAuth()
token = auth.get_token()

service = OptionService()

chain = service.get_option_chain(
    token,
    "NSE_INDEX|Nifty 50",
)

print("\nATM CE")
pprint(service.get_option(chain, "CE", "ATM"))

print("\nATM PE")
pprint(service.get_option(chain, "PE", "ATM"))

print("\nITM CE")
pprint(service.get_option(chain, "CE", "ITM"))

print("\nOTM CE")
pprint(service.get_option(chain, "CE", "OTM"))

print("\nITM PE")
pprint(service.get_option(chain, "PE", "ITM"))

print("\nOTM PE")
pprint(service.get_option(chain, "PE", "OTM"))
