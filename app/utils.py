"""
utils.py

Shared, generic helper functions used across the application.
No trading logic lives here — only cross-cutting concerns like
logging setup and defensive response validation.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Iterable

from app.config import LOG_LEVEL
from app.core.exceptions import MarketDataError


def get_logger(name: str) -> logging.Logger:
    """
    Return a configured logger.

    Ensures a single, consistent log format across the app instead of
    each module configuring logging independently.

    Args:
        name: Usually __name__ of the calling module.

    Returns:
        logging.Logger
    """

    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler()

        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(LOG_LEVEL)
        logger.propagate = False

    return logger


def require_fields(data: Dict[str, Any], fields: Iterable[str], context: str) -> None:
    """
    Ensure required fields are present and non-None in an API response.

    Args:
        data: Parsed response dict to validate.
        fields: Field names that must be present.
        context: Human-readable label for the error message
            (e.g. "option chain response").

    Raises:
        MarketDataError: If any required field is missing or None.
    """

    missing = [field for field in fields if data.get(field) is None]

    if missing:
        raise MarketDataError(
            f"Missing required field(s) {missing} in {context}."
        )


def safe_round(value: Any, digits: int = 2) -> float | None:
    """
    Round a numeric value defensively.

    Returns None instead of raising when value is None or not numeric,
    so callers can decide how to handle absent data explicitly.

    Args:
        value: Value to round.
        digits: Decimal places.

    Returns:
        Rounded float, or None if value is not a valid number.
    """

    if value is None:
        return None

    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return None
