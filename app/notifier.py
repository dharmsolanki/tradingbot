"""
notifier.py

Generic internal notification layer.

Architecture is channel-agnostic: a Notification is a plain dataclass;
NotificationService formats it and dispatches to registered handlers.

Current handlers:
  - InternalLogHandler  (always active — writes to app logger)

Future handlers (not implemented yet — credentials must come from env):
  - TelegramHandler
  - WhatsAppHandler
  - EmailHandler
  - PushNotificationHandler

To add a channel later, implement NotificationHandler and register it
with NotificationService.register_handler().  No changes needed in the
rest of the codebase — recommendation_engine calls notify() and the
service takes care of dispatch.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List

from app.utils import get_logger

logger = get_logger(__name__)


# ==========================
# Notification Data Model
# ==========================


@dataclass
class Notification:
    """
    Immutable payload representing one notification event.
    All fields are plain Python types so any handler can serialise them.
    """

    event: str                        # e.g. "RECOMMENDATION_GENERATED"
    title: str                        # Short headline
    body: str                         # Full human-readable message
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )


# ==========================
# Handler Interface
# ==========================


class NotificationHandler(abc.ABC):
    """Base class every notification channel must implement."""

    @abc.abstractmethod
    def send(self, notification: Notification) -> None:
        """Deliver the notification through this channel."""


# ==========================
# Built-in Handlers
# ==========================


class InternalLogHandler(NotificationHandler):
    """
    Writes every notification to the application logger.
    Always registered — provides an audit trail even when no external
    channel is configured.
    """

    def send(self, notification: Notification) -> None:
        logger.info(
            "[NOTIFICATION] %s | %s | %s",
            notification.event,
            notification.title,
            notification.body,
        )


# ==========================
# Notification Service
# ==========================


class NotificationService:
    """
    Dispatches notifications to all registered handlers.

    Usage:
        service = NotificationService()
        service.notify(Notification(
            event="RECOMMENDATION_GENERATED",
            title="BUY NIFTY 25000 CE",
            body="Entry: ₹145–148 | SL: ₹132 | T1: ₹165 | T2: ₹182",
            metadata={"confidence": 91, "instrument": "NIFTY"},
        ))
    """

    def __init__(self) -> None:
        self._handlers: List[NotificationHandler] = [InternalLogHandler()]

    def register_handler(self, handler: NotificationHandler) -> None:
        """
        Register a new notification channel.

        Args:
            handler: Any NotificationHandler implementation.
        """
        self._handlers.append(handler)

    def notify(self, notification: Notification) -> None:
        """
        Dispatch a notification to all registered handlers.

        Failures in one handler do not stop delivery to others.
        """
        for handler in self._handlers:
            try:
                handler.send(notification)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Notification handler %s failed: %s",
                    type(handler).__name__,
                    exc,
                )


# ==========================
# Message Formatters
# ==========================


def format_recommendation(rec: Dict[str, Any]) -> str:
    """
    Format a recommendation dict into a clean, human-readable string
    suitable for any notification channel (log, Telegram, email, etc).

    Args:
        rec: Output of RecommendationEngine.build_recommendation().

    Returns:
        Formatted multi-line string.
    """

    reasons_text = "\n".join(f"  • {r}" for r in rec.get("reasons", []))

    entry_range = rec.get("entry_range", "—")
    if isinstance(entry_range, dict):
        entry_range = f"₹{entry_range['low']}–{entry_range['high']}"

    return (
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 {rec.get('strategy_name', 'Signal')}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Instrument : {rec.get('instrument', '—')}\n"
        f"Signal     : {rec.get('signal', '—')}\n"
        f"Trend      : {rec.get('market_trend', '—')}\n"
        f"Confidence : {rec.get('confidence', '—')}%\n"
        f"\n"
        f"Strike     : {rec.get('strike', '—')}\n"
        f"Expiry     : {rec.get('expiry', '—')}\n"
        f"Entry      : {entry_range}\n"
        f"Stop Loss  : ₹{rec.get('stop_loss', '—')}\n"
        f"Target 1   : ₹{rec.get('target_1', '—')}\n"
        f"Target 2   : ₹{rec.get('target_2', '—')}\n"
        f"RR Ratio   : 1:{rec.get('rr_ratio', '—')}\n"
        f"\n"
        f"Reasons:\n{reasons_text}\n"
        f"\n"
        f"Generated  : {rec.get('generated_at', '—')}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
