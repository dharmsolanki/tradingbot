"""
main.py

FastAPI application entry point for the Manual Options Trading
Assistant.

This app NEVER places real broker orders. It continuously:
  1. Fetches live market data from Upstox.
  2. Calculates indicators and signals.
  3. Runs the decision engine (signal + option selection + risk).
  4. Opens/manages/closes DEMO trades only (virtual capital).
  5. Streams live state to the dashboard over WebSocket.

Run with:
    uvicorn app.main:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import asyncio
from functools import partial
from datetime import datetime, time as dtime
from typing import Any, Dict, List, Optional
from app.constants import TRADE_CLOSED
from app.constants import TRADE_OPEN
from app.constants import MANUAL_EXIT
from app.constants import TIME_EXIT

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import config, constants, strategy
from app.analytics import Analytics
from app.auth import UpstoxAuth
from app.core.exceptions import (
    AuthenticationError,
    MarketDataError,
    TradingError,
)
from app.db import DatabaseManager
from app.decision_engine import DecisionEngine
from app.market_data import MarketData
from app.paper_trader import PaperTrader
from app.repositories.trade_repository import TradeRepository
from app.recommendation_engine import RecommendationEngine
from app.utils import get_logger

logger = get_logger(__name__)

app = FastAPI(title="Manual Options Trading Assistant", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================
# Shared State
# ==========================

auth = UpstoxAuth(token_file=config.TOKEN_FILE)
market = MarketData(timeout=config.REQUEST_TIMEOUT_SECONDS)
db = DatabaseManager(db_path=config.PAPER_TRADES_DB_PATH)
repository = TradeRepository(db=db)
paper_trader = PaperTrader(db_path=config.PAPER_TRADES_DB_PATH)
paper_trader.repository = repository  # share the same underlying table
decision_engine = DecisionEngine()
recommendation_engine = RecommendationEngine(
    decision_engine=decision_engine,
    market_data=market,
)
analytics = Analytics(repository)

INSTRUMENT_KEY = config.INSTRUMENTS[config.DEFAULT_INSTRUMENT]
_current_instrument = config.DEFAULT_INSTRUMENT

_connected_clients: List[WebSocket] = []
_latest_state: Dict[str, Any] = {
    "market_status": "UNKNOWN",
    "spot_price": None,
    "candles_5m": [],
    "signal": None,
    "decision": None,
    "open_position": None,
    "reasons": [],
    "instrument": config.DEFAULT_INSTRUMENT,
    "updated_at": None,
}


# ==========================
# Helpers
# ==========================


def is_market_hours(now: Optional[datetime] = None) -> bool:
    """
    Basic NSE trading-window check (weekday + 09:15-15:30 IST).

    This is a coarse filter only — actual holidays/closures are
    detected from live API responses (empty candles), never assumed.
    """

    now = now or datetime.now()

    if now.weekday() >= 5:  # Saturday=5, Sunday=6
        return False

    return dtime(9, 15) <= now.time() <= dtime(15, 30)


def _today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def get_today_closed_trades() -> List[Dict[str, Any]]:
    """All trades closed today, used for daily loss / trade-count limits."""

    closed = repository.list_trades(status=TRADE_CLOSED)
    today = _today_str()

    return [t for t in closed if (t.get("entry_time") or "").startswith(today)]


def get_capital_state() -> Dict[str, float]:
    """
    Derive current virtual capital from starting capital + realized P/L.
    No separate mutable balance is stored, avoiding a second source of
    truth that could drift from the trade ledger.
    """

    closed_today = get_today_closed_trades()

    realized_today = round(sum(t["net_pnl"] or 0 for t in closed_today), 2)

    all_closed = repository.list_trades(status=TRADE_CLOSED)
    realized_total = round(sum(t["net_pnl"] or 0 for t in all_closed), 2)

    capital = round(strategy.STARTING_CAPITAL + realized_total, 2)

    return {
        "capital": capital,
        "realized_pnl_today": realized_today,
        "realized_pnl_total": realized_total,
        "trades_today_count": len(closed_today),
        "daily_target_reached": realized_today >= strategy.MIN_DAILY_PROFIT_RUPEES,
    }


async def run_blocking(func, *args, **kwargs):
    """
    Run blocking/synchronous work in a background thread so the asyncio
    event loop remains responsive.
    """
    return await asyncio.to_thread(partial(func, *args, **kwargs))


async def broadcast_state() -> None:
    """Push the latest state to all connected dashboard clients."""

    stale = []

    for ws in _connected_clients:
        try:
            await ws.send_json(_latest_state)
        except Exception:
            stale.append(ws)

    for ws in stale:
        _connected_clients.remove(ws)


# ==========================
# Background Live Loop
# ==========================


async def price_ticker_loop() -> None:
    """
    Lightweight fast loop — updates only the live spot price every
    PRICE_TICK_INTERVAL_SECONDS. Kept separate from the heavier
    decision loop (candles + option chain) to avoid hitting Upstox
    rate limits on the option-chain/contract endpoints.
    """

    while True:
        try:
            if is_market_hours():
                token = auth.get_token()
                spot_price = await run_blocking(
                    market.get_ltp,
                    token,
                    INSTRUMENT_KEY,
                )
                _latest_state["spot_price"] = spot_price
                await broadcast_state()

        except (AuthenticationError, MarketDataError) as exc:
            logger.warning("Price ticker data issue: %s", exc)

        except Exception as exc:  # noqa: BLE001 - keep the ticker alive
            logger.exception("Unexpected error in price ticker: %s", exc)

        await asyncio.sleep(config.PRICE_TICK_INTERVAL_SECONDS)


async def live_loop() -> None:
    """
    Continuously polls live candles, evaluates the decision engine,
    manages the open demo trade, and broadcasts state — while the
    market is open. Spot price itself is updated more frequently by
    price_ticker_loop(); this loop handles everything that needs
    5-minute candle data.
    """

    while True:
        try:
            if not is_market_hours():
                _latest_state.update(
                    {
                        "market_status": TRADE_CLOSED,
                        "updated_at": datetime.now().isoformat(),
                    }
                )
                await broadcast_state()
                await asyncio.sleep(30)
                continue

            token = auth.get_token()

            candles_5m = await run_blocking(
                market.get_intraday_candles,
                token=token,
                instrument_key=INSTRUMENT_KEY,
                unit="minutes",
                interval=5,
            )
            _latest_state["candles_5m"] = candles_5m

            open_trade = repository.get_open_trade()

            if open_trade is not None:
                await _manage_open_trade(token, open_trade)
            else:
                await _evaluate_new_trade(token)

            _latest_state["market_status"] = TRADE_OPEN
            _latest_state["updated_at"] = datetime.now().isoformat()

        except (AuthenticationError, MarketDataError) as exc:
            logger.warning("Live loop data issue: %s", exc)
            _latest_state["market_status"] = "DATA_ERROR"
            _latest_state["reasons"] = [str(exc)]

        except TradingError as exc:
            logger.error("Live loop trading error: %s", exc)
            _latest_state["reasons"] = [str(exc)]

        except Exception as exc:  # noqa: BLE001 - keep the loop alive
            logger.exception("Unexpected error in live loop: %s", exc)

        await broadcast_state()
        await asyncio.sleep(config.LIVE_LOOP_INTERVAL_SECONDS)


async def _evaluate_new_trade(token: str) -> None:
    """Run the decision engine, open a demo trade, and generate a recommendation if warranted."""

    candles = await run_blocking(
        market.get_multi_timeframe_candles,
        token,
        INSTRUMENT_KEY,
    )

    if strategy.SIGNAL_MODE == "ORB":
        candles_5m_today = await run_blocking(
            market.get_intraday_candles,
            token=token,
            instrument_key=INSTRUMENT_KEY,
            unit="minutes",
            interval=5,
        )
    else:
        candles_5m_today = candles["5m"]
    capital_state = get_capital_state()

    # Daily profit target check
    if capital_state["realized_pnl_today"] >= strategy.MIN_DAILY_PROFIT_RUPEES:
        _latest_state["decision"] = "BLOCKED"
        _latest_state["reasons"] = [
            f"Daily profit target ₹{strategy.MIN_DAILY_PROFIT_RUPEES} reached. Trade band karo aaj ke liye!"
        ]
        return

    result = decision_engine.evaluate(
        token=token,
        instrument_key=INSTRUMENT_KEY,
        candles_5m=candles_5m_today,
        candles_15m=candles["15m"],
        capital=capital_state["capital"],
        realized_pnl_today=capital_state["realized_pnl_today"],
        trades_today_count=capital_state["trades_today_count"],
        has_open_trade=False,
    )

    _latest_state["signal"] = result.get("signal")
    _latest_state["decision"] = result["decision"]
    _latest_state["reasons"] = result["reasons"]
    _latest_state["open_position"] = None

    # Debug: log signal scores every cycle so we can see why NO_TRADE
    sig = result.get("signal")
    if sig:
        trend = sig.get("trend", {})
        entry = sig.get("entry", {})
        logger.info(
            "SIGNAL DEBUG | trend=%s(score=%s) entry=%s(score=%s) confidence=%s decision=%s",
            trend.get("trend") if isinstance(trend, dict) else trend,
            trend.get("score") if isinstance(trend, dict) else "?",
            entry.get("entry") if isinstance(entry, dict) else entry,
            entry.get("score") if isinstance(entry, dict) else "?",
            sig.get("confidence"),
            result["decision"],
        )

    if result["decision"] == "TRADE":
        trade_plan = result["trade_plan"]
        option = result["option"]

        trade_id = repository.create_trade(
            option=option,
            trade_plan=trade_plan,
            quantity=trade_plan["quantity"],
        )

        logger.info("Opened demo trade %s: %s", trade_id, trade_plan.get("symbol", ""))

        # Generate recommendation (enriches result with entry range,
        # target 2, indicator snapshot, lifecycle tracking).
        # try_generate re-uses the same result via a fresh evaluate() call
        # internally so we call it once from the live loop — not twice.
        try:
            await run_blocking(
                recommendation_engine.try_generate,
                token=token,
                instrument_key=INSTRUMENT_KEY,
                candles_5m=candles["5m"],
                candles_15m=candles["15m"],
                capital=capital_state["capital"],
                realized_pnl_today=capital_state["realized_pnl_today"],
                trades_today_count=capital_state["trades_today_count"],
                has_open_trade=False,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Recommendation generation failed: %s", exc)

    # Update lifecycle of any WAITING/ACTIVE recommendations.
    for rec in recommendation_engine.today_recommendations():
        if rec["status"] in ("WAITING", "ACTIVE"):
            try:
                await run_blocking(
                    recommendation_engine.update_lifecycle,
                    token,
                    rec["rec_id"],
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Recommendation lifecycle update failed: %s", exc)


async def _manage_open_trade(token: str, open_trade: Dict[str, Any]) -> None:
    """
    Manage open trade with:
    1. Trailing SL — locks profit as premium rises
    2. Minimum profit lock — once MIN_PROFIT_RUPEES earned, SL moves to breakeven+
    3. Time exit — force close at 3:15 PM
    4. Manual exit via API
    """

    from app.config import MIN_PROFIT_RUPEES

    instrument_key = open_trade["instrument_key"]
    current_premium = await run_blocking(
        market.get_ltp,
        token,
        instrument_key,
    )

    entry = open_trade["entry_price"]
    stop_loss = open_trade["stop_loss"]
    target = open_trade["target"]
    quantity = open_trade["quantity"]

    live_pnl = round((current_premium - entry) * quantity, 2)

    original_risk = entry * strategy.STOP_LOSS_PERCENT / 100

    new_stop_loss = stop_loss

    # Phase 1: Min profit achieved — move SL to breakeven+
    if live_pnl >= MIN_PROFIT_RUPEES:
        breakeven = round(entry + (MIN_PROFIT_RUPEES / quantity), 2)
        new_stop_loss = max(stop_loss, breakeven)

    # Phase 2: Trail SL behind current premium by original risk distance
    # SL is always original_risk points below current premium — never hits instantly
    if live_pnl >= MIN_PROFIT_RUPEES:
        trail_sl = round(current_premium - original_risk, 2)
        new_stop_loss = max(new_stop_loss, trail_sl)

    # Update SL in DB if changed
    if new_stop_loss != stop_loss:
        db.execute(
            "UPDATE paper_trades SET stop_loss = ? WHERE trade_id = ?",
            (new_stop_loss, open_trade["trade_id"]),
        )
        stop_loss = new_stop_loss
        logger.info("Trailing SL updated to %.2f (live_pnl=%.2f)", stop_loss, live_pnl)

    # ==========================
    # Exit Conditions
    # ==========================

    exit_reason = None
    current_time = datetime.now().strftime("%H:%M")

    if current_time >= "15:15":
        exit_reason = TIME_EXIT
    elif current_premium <= stop_loss:
        exit_reason = constants.STOP_LOSS_HIT
    elif current_premium >= target:
        exit_reason = constants.TARGET_HIT

    if exit_reason:
        net_pnl = repository.close_trade(
            trade_id=open_trade["trade_id"],
            exit_price=current_premium,
            exit_reason=exit_reason,
        )
        logger.info(
            "Closed trade %s: %s (net_pnl=%.2f)",
            open_trade["trade_id"],
            exit_reason,
            net_pnl,
        )
        _latest_state["open_position"] = None
        _latest_state["decision"] = "NO_TRADE"
        _latest_state["reasons"] = [f"Trade closed: {exit_reason} | P/L: ₹{net_pnl}"]
        return

    _latest_state["open_position"] = {
        **open_trade,
        "current_premium": current_premium,
        "live_pnl": live_pnl,
        "trailing_sl": stop_loss,
    }
    _latest_state["decision"] = "WAIT"
    _latest_state["reasons"] = [
        f"Managing position | Premium: ₹{current_premium} | "
        f"Trailing SL: ₹{stop_loss} | Live P/L: ₹{live_pnl}"
    ]


@app.on_event("startup")
async def on_startup() -> None:
    asyncio.create_task(price_ticker_loop())
    asyncio.create_task(live_loop())


# ==========================
# REST Endpoints
# ==========================


@app.get("/api/status")
def get_status() -> Dict[str, Any]:
    """Overall app + auth + market status."""

    return {
        "token_valid": auth.is_valid(),
        "market_status": _latest_state["market_status"],
        "instrument": config.DEFAULT_INSTRUMENT,
        "updated_at": _latest_state["updated_at"],
    }


@app.get("/api/token")
def get_token_status() -> Dict[str, Any]:
    """
    Returns token configuration status.
    The actual token is never exposed.
    """

    return {
        "configured": auth.is_valid(),
        "token": auth.get_masked_token() if auth.is_valid() else None,
    }


@app.post("/api/token")
def update_token(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update Upstox access token.
    """

    token = payload.get("access_token", "").strip()

    if not token:
        return {"success": False, "message": "Access token is required."}

    try:
        auth.save_token(token)

        logger.info("Access token updated successfully.")

        return {"success": True, "message": "Access token updated successfully."}

    except Exception as exc:
        logger.exception("Failed to update access token.")

        return {"success": False, "message": str(exc)}


@app.get("/api/state")
def get_state() -> Dict[str, Any]:
    """Full latest live state (same payload pushed over WebSocket)."""

    return _latest_state


@app.post("/api/instrument")
async def set_instrument(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Switch active instrument (NIFTY / SENSEX / BANKNIFTY)."""
    global INSTRUMENT_KEY, _current_instrument

    name = payload.get("instrument", "").upper()

    if name not in config.INSTRUMENTS:
        return {
            "success": False,
            "message": f"Unknown instrument. Choose from: {list(config.INSTRUMENTS.keys())}",
        }

    INSTRUMENT_KEY = config.INSTRUMENTS[name]
    _current_instrument = name

    _latest_state["instrument"] = name

    logger.info("Instrument switched to %s (%s)", name, INSTRUMENT_KEY)

    return {"success": True, "instrument": name, "key": INSTRUMENT_KEY}


@app.get("/api/instrument")
def get_instrument() -> Dict[str, Any]:
    """Get currently active instrument."""
    return {"instrument": _current_instrument, "key": INSTRUMENT_KEY}


@app.get("/api/capital")
def get_capital() -> Dict[str, Any]:
    """Virtual capital and today's realized P/L."""

    return get_capital_state()


@app.get("/api/position")
def get_position() -> Dict[str, Any]:
    """Currently open demo trade, if any."""

    return {"open_position": _latest_state["open_position"]}


@app.get("/api/trades")
def get_trades(status: Optional[str] = None) -> Dict[str, Any]:
    """Trade book. Optional ?status=OPEN|CLOSED|CANCELLED filter."""

    return {"trades": repository.list_trades(status=status)}


@app.get("/api/analytics")
def get_analytics() -> Dict[str, Any]:
    """Win rate, RR, equity curve, and other performance stats."""

    return analytics.summary()


@app.get("/api/recommendations")
def get_recommendations(period: str = "today") -> Dict[str, Any]:
    """
    Today's trading recommendations with full lifecycle status.

    Query params:
        period: "today" (default) | "all"
    """

    if period == "all":
        recs = recommendation_engine.all_recommendations()
    else:
        recs = recommendation_engine.today_recommendations()

    return {"recommendations": recs, "count": len(recs)}


@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket) -> None:
    """Streams the live state to the dashboard as it updates."""

    await websocket.accept()
    _connected_clients.append(websocket)

    try:
        await websocket.send_json(_latest_state)

        while True:
            # Keep the connection alive; all pushes happen from live_loop.
            await websocket.receive_text()

    except WebSocketDisconnect:
        if websocket in _connected_clients:
            _connected_clients.remove(websocket)


@app.post("/api/trade/exit")
async def manual_exit() -> Dict[str, Any]:
    """Manually close the open trade at current market price."""

    open_trade = repository.get_open_trade()

    if open_trade is None:
        return {"success": False, "message": "No open trade to exit."}

    try:
        token = auth.get_token()
        current_premium = await run_blocking(
            market.get_ltp,
            token,
            open_trade["instrument_key"],
        )

        net_pnl = repository.close_trade(
            trade_id=open_trade["trade_id"],
            exit_price=current_premium,
            exit_reason=MANUAL_EXIT,
        )

        _latest_state["open_position"] = None
        _latest_state["decision"] = "NO_TRADE"
        _latest_state["reasons"] = [f"Manual exit | P/L: ₹{net_pnl}"]

        return {"success": True, "exit_price": current_premium, "net_pnl": net_pnl}

    except Exception as exc:
        return {"success": False, "message": str(exc)}


# Serve the dashboard frontend at "/"
app.mount(
    "/",
    StaticFiles(directory=str(config.BASE_DIR / "frontend"), html=True),
    name="frontend",
)
