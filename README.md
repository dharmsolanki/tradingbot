# Manual Options Trading Assistant (Demo Mode)

A professional, **manual** trading assistant for NIFTY options using the
Upstox API. It analyzes live market data and generates high-quality
CE/PE signals with entry, stop loss, target, and confidence — you
execute trades yourself in the Upstox app.

**This application never places real broker orders.** It runs a fully
live-data Demo Trading Engine (real market, real prices, real option
premiums — virtual capital only) so the strategy can be verified before
any broker integration is added.

## Architecture

```
Market Data → Indicators → Signal Engine → Decision Engine
    → Risk Engine → Option Selection → Paper Trading → Dashboard
```

- `app/market_data.py` — Upstox API client (candles, LTP, option chain/contracts)
- `app/indicators.py`, `indicator_utils.py` — EMA, RSI, MACD, ATR, SuperTrend
- `app/signal_engine.py` — trend + entry detection, single & multi-timeframe signals
- `app/decision_engine.py` — combines signal + liquidity + risk into a final TRADE/WAIT/NO_TRADE/BLOCKED decision
- `app/option_service.py` — ATM/ITM/OTM selection, liquidity/spread filtering
- `app/risk.py` — trade levels, position sizing, daily loss limit, trailing stop
- `app/repositories/trade_repository.py` + `app/db.py` + `app/core/schema.py` — single source of truth for the paper_trades table
- `app/paper_trader.py` — thin facade over the repository (open/close/get trade)
- `app/analytics.py` — win rate, RR, equity curve
- `app/main.py` — FastAPI backend: live loop, REST API, WebSocket
- `frontend/index.html` — dark, TradingView-inspired live dashboard

## Setup

```bash
pip install -r requirements.txt
```

Put a valid Upstox access token in `token.json`:

```json
{ "access_token": "..." }
```

## Run

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000` for the dashboard.

## API

| Endpoint | Description |
|---|---|
| `GET /api/status` | token/market status |
| `GET /api/state` | full live state (same as WebSocket payload) |
| `GET /api/capital` | virtual capital, today's realized P/L |
| `GET /api/position` | current open demo trade |
| `GET /api/trades?status=` | trade book |
| `GET /api/analytics` | win rate, RR, equity curve |
| `WS /ws/live` | live push updates |

## Configuration

All paths, instrument keys, and tunables live in `app/config.py` and
`app/strategy.py`, overridable via environment variables. Nothing is
hardcoded from market data — strikes, expiries, premiums, lot sizes,
and spot prices are always fetched live from Upstox.

## Testing

```bash
python3 test_trade_repository.py
python3 test_risk_management.py
python3 test_analytics.py
```

The remaining `test_*.py` files are live-integration tests that require
a valid `token.json` and an active market/API connection.

## Broker Integration

Not part of this phase. `app/order.py` is a reserved placeholder — no
order-placement logic exists anywhere in this codebase.
