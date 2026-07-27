"""
Live integration test for DecisionEngine — requires a valid token.json
and live market data, consistent with the other test_*.py files in
this project.
"""

from app.auth import UpstoxAuth
from app.decision_engine import DecisionEngine
from app.market_data import MarketData

auth = UpstoxAuth()
token = auth.get_token()

market = MarketData()
engine = DecisionEngine()

instrument = "NSE_INDEX|Nifty 50"

candles = market.get_multi_timeframe_candles(token, instrument)

result = engine.evaluate(
    token=token,
    instrument_key=instrument,
    candles_5m=candles["5m"],
    candles_15m=candles["15m"],
    capital=10000,
    realized_pnl_today=0,
    trades_today_count=0,
    has_open_trade=False,
)

print("=" * 60)
print("DECISION ENGINE RESULT")
print("=" * 60)

for key, value in result.items():
    print(f"{key:12}: {value}")
