"""
test_recommendation_engine.py

Offline tests for RecommendationEngine + NotificationService.
No network required — mocks DecisionEngine and MarketData.
"""

from unittest.mock import MagicMock, patch
from app.recommendation_engine import (
    RecommendationEngine,
    STATUS_WAITING,
    STATUS_ACTIVE,
    STATUS_TARGET_HIT,
    STATUS_SL_HIT,
    STATUS_EXPIRED,
)
from app.notifier import NotificationService, Notification, format_recommendation


# ==========================
# Helpers
# ==========================

def _mock_trade_result(confidence=85, option_type="CE"):
    """Return a fake TRADE decision result matching DecisionEngine output."""
    return {
        "decision": "TRADE",
        "signal": {
            "signal": "BUY",
            "confidence": confidence,
            "option_type": option_type,
            "trend": "BULLISH",
            "entry": {"score": 6, "reasons": ["EMA crossover", "MACD bullish"]},
            "indicators": {"ema_fast": 24200, "ema_slow": 24150, "rsi": 62, "macd": 10, "atr": 45},
        },
        "trade_plan": {
            "stop_loss": 100.0,
            "target": 140.0,
            "risk": 20.0,
            "quantity": 65,
            "lots": 1,
            "lot_size": 65,
            "symbol": "25000 CE",
        },
        "option": {
            "strike": 25000,
            "option_type": option_type,
            "instrument_key": "NSE_FO|NIFTY-CE-25000",
            "expiry": "2026-07-31",
            "ltp": 120.0,
            "lot_size": 65,
        },
        "reasons": ["High-probability setup confirmed."],
    }


def _make_engine(decision="TRADE", confidence=85):
    """Build a RecommendationEngine with mocked dependencies."""
    mock_de = MagicMock()
    mock_de.evaluate.return_value = (
        _mock_trade_result(confidence) if decision == "TRADE"
        else {"decision": "NO_TRADE", "signal": None, "trade_plan": None, "reasons": ["No setup."]}
    )
    mock_market = MagicMock()
    mock_market.get_ltp.return_value = 120.0
    return RecommendationEngine(decision_engine=mock_de, market_data=mock_market)


# ==========================
# Tests
# ==========================

def test_generates_recommendation_on_trade():
    engine = _make_engine(decision="TRADE", confidence=88)
    rec = engine.try_generate(
        token="tok", instrument_key="NSE_INDEX|Nifty 50",
        candles_5m=[], candles_15m=[], capital=100000,
        realized_pnl_today=0, trades_today_count=0, has_open_trade=False,
    )
    assert rec is not None
    assert rec["confidence"] == 88
    assert rec["status"] == STATUS_WAITING
    assert rec["target_2"] > rec["target_1"]
    assert rec["entry_range"]["low"] < rec["entry_range"]["high"]
    print("PASS: generates recommendation on TRADE decision")


def test_no_recommendation_on_no_trade():
    engine = _make_engine(decision="NO_TRADE")
    rec = engine.try_generate(
        token="tok", instrument_key="NSE_INDEX|Nifty 50",
        candles_5m=[], candles_15m=[], capital=100000,
        realized_pnl_today=0, trades_today_count=0, has_open_trade=False,
    )
    assert rec is None
    print("PASS: no recommendation when NO_TRADE")


def test_lifecycle_waiting_to_active():
    engine = _make_engine(decision="TRADE")
    rec = engine.try_generate(
        token="tok", instrument_key="NSE_INDEX|Nifty 50",
        candles_5m=[], candles_15m=[], capital=100000,
        realized_pnl_today=0, trades_today_count=0, has_open_trade=False,
    )
    assert rec["status"] == STATUS_WAITING

    engine.market.get_ltp.return_value = rec["entry_range"]["low"] + 1
    updated = engine.update_lifecycle("tok", rec["rec_id"])
    assert updated["status"] == STATUS_ACTIVE
    print("PASS: recommendation moves WAITING -> ACTIVE when LTP >= entry_range.low")


def test_lifecycle_target_hit():
    engine = _make_engine(decision="TRADE")
    rec = engine.try_generate(
        token="tok", instrument_key="NSE_INDEX|Nifty 50",
        candles_5m=[], candles_15m=[], capital=100000,
        realized_pnl_today=0, trades_today_count=0, has_open_trade=False,
    )
    # Activate first
    engine.market.get_ltp.return_value = rec["entry_range"]["low"] + 1
    engine.update_lifecycle("tok", rec["rec_id"])

    # Now hit target 2
    engine.market.get_ltp.return_value = rec["target_2"] + 1
    updated = engine.update_lifecycle("tok", rec["rec_id"])
    assert updated["status"] == STATUS_TARGET_HIT
    print("PASS: recommendation marked TARGET_HIT when LTP >= target_2")


def test_lifecycle_sl_hit():
    engine = _make_engine(decision="TRADE")
    rec = engine.try_generate(
        token="tok", instrument_key="NSE_INDEX|Nifty 50",
        candles_5m=[], candles_15m=[], capital=100000,
        realized_pnl_today=0, trades_today_count=0, has_open_trade=False,
    )
    engine.market.get_ltp.return_value = rec["entry_range"]["low"] + 1
    engine.update_lifecycle("tok", rec["rec_id"])

    engine.market.get_ltp.return_value = rec["stop_loss"] - 1
    updated = engine.update_lifecycle("tok", rec["rec_id"])
    assert updated["status"] == STATUS_SL_HIT
    print("PASS: recommendation marked SL_HIT when LTP <= stop_loss")


def test_expire_open():
    engine = _make_engine(decision="TRADE")
    engine.try_generate(
        token="tok", instrument_key="NSE_INDEX|Nifty 50",
        candles_5m=[], candles_15m=[], capital=100000,
        realized_pnl_today=0, trades_today_count=0, has_open_trade=False,
    )
    engine.expire_open()
    for rec in engine.all_recommendations():
        assert rec["status"] == STATUS_EXPIRED
    print("PASS: expire_open marks all WAITING/ACTIVE as EXPIRED")


def test_notification_formatting():
    engine = _make_engine(decision="TRADE")
    rec = engine.try_generate(
        token="tok", instrument_key="NSE_INDEX|Nifty 50",
        candles_5m=[], candles_15m=[], capital=100000,
        realized_pnl_today=0, trades_today_count=0, has_open_trade=False,
    )
    msg = format_recommendation(rec)
    assert "BUY" in msg
    assert "Stop Loss" in msg
    assert "Target 1" in msg
    assert "Target 2" in msg
    assert "Confidence" in msg
    print("PASS: notification formatted with all required fields")


def test_today_recommendations_only_today():
    engine = _make_engine(decision="TRADE")
    engine.try_generate(
        token="tok", instrument_key="NSE_INDEX|Nifty 50",
        candles_5m=[], candles_15m=[], capital=100000,
        realized_pnl_today=0, trades_today_count=0, has_open_trade=False,
    )
    recs = engine.today_recommendations()
    assert len(recs) == 1
    print("PASS: today_recommendations returns only today's recs")


if __name__ == "__main__":
    test_generates_recommendation_on_trade()
    test_no_recommendation_on_no_trade()
    test_lifecycle_waiting_to_active()
    test_lifecycle_target_hit()
    test_lifecycle_sl_hit()
    test_expire_open()
    test_notification_formatting()
    test_today_recommendations_only_today()
    print("\nAll recommendation engine tests PASSED.")
