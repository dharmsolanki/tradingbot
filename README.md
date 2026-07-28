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
Market Data
      │
      ▼
Indicators
      │
      ▼
Signal Engine (EMA / ORB)
      │
      ▼
Decision Engine
      │
      ▼
Risk Engine
      │
      ▼
Recommendation Engine
      │
      ▼
Option Selection
      │
      ▼
Paper Trading
      │
      ▼
Analytics + Dashboard
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
Representative tests:

python test_auth.py
python test_market_data.py
python test_signal_engine.py
python test_option_service.py
python test_trade_repository.py
python test_analytics.py
python test_risk.py
```

The remaining `test_*.py` files are live-integration tests that require
a valid `token.json` and an active market/API connection.

## Broker Integration

Broker integration is **not part of the current project scope**.

This application is a **manual, demo-only trading assistant**. It uses live market data from the Upstox API together with a paper trading engine for strategy validation. **No real broker orders are placed.**

The `app/order.py` module is intentionally reserved for future broker integration. It currently contains **no order-placement logic** and serves as a placeholder so that real broker routing can be added in a future phase without changing the existing architecture.


- app/recommendation_engine.py — generates actionable trade recommendations
- app/signal_engine_orb.py — Opening Range Breakout strategy
- app/strategy_orb.py — ORB configuration
- app/notifier.py — notification framework
- app/models.py — shared dataclasses
- app/core/exceptions.py — project-wide exceptions

## Features

- Live Upstox market data
- EMA strategy
- ORB strategy
- Multi-timeframe analysis
- Dynamic option selection
- Risk management
- Paper trading engine
- Live dashboard
- Trade analytics
- Trade recommendations
- WebSocket live updates
- Manual exit
- Instrument switching

trading_bot/
│
├── app/
├── frontend/
├── database/
├── backtest.py
├── backtest_orb.py
├── requirements.txt
└── README.md

## Dashboard

The web dashboard provides:

- Live candlestick chart
- Market status
- Signal display
- Current paper position
- Recommendations
- Trade history
- Capital and P/L
- Analytics

## Current Status

Current mode:

- Live market data
- Live option chain
- Live recommendations
- Paper trading
- Manual execution only

Real broker order placement is intentionally disabled.

## Roadmap

- Broker integration
- Docker deployment
- PostgreSQL support
- Automated testing
- Telegram notifications
- Multi-account support