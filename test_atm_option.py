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

atm = service.get_atm_option(chain)

print()

pprint(atm)
