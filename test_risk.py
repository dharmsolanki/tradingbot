from app.auth import UpstoxAuth
from app.market_data import MarketData
from app.option_service import OptionService
from app.signal_engine import (
    calculate_indicators,
    generate_signal,
)
from app.risk import calculate_trade_levels

auth = UpstoxAuth()
token = auth.get_token()

market = MarketData()
option_service = OptionService()

instrument = "NSE_INDEX|Nifty 50"

candles = market.get_latest_candles(
    token,
    instrument,
)

indicators = calculate_indicators(candles)

signal = generate_signal(indicators)

chain = option_service.get_option_chain(
    token,
    instrument,
)

option = option_service.get_option(
    chain,
    option_type=signal["option_type"],
    moneyness="ATM",
)

trade = calculate_trade_levels(
    signal,
    option,
)

print("=" * 60)
print("TRADE PLAN")
print("=" * 60)

for key, value in trade.items():
    print(f"{key:15}: {value}")
