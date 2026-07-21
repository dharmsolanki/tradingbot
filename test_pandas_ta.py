import pandas as pd
import pandas_ta as ta

from app.auth import UpstoxAuth
from app.market_data import MarketData

# Authentication
auth = UpstoxAuth()
token = auth.get_token()

# Fetch market data
market = MarketData()

candles = market.get_intraday_candles(token=token, instrument_key="NSE_INDEX|Nifty 50")

# Convert to DataFrame
df = pd.DataFrame(
    candles,
    columns=[
        "datetime",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "oi",
    ],
)

# Convert numeric columns
for col in ["open", "high", "low", "close", "volume"]:
    df[col] = pd.to_numeric(df[col])

# SuperTrend
st = ta.supertrend(
    high=df["high"], low=df["low"], close=df["close"], length=10, multiplier=3
)

print(df.tail())

print("\n")

print(st.tail())
