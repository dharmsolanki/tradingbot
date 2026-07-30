"""
order.py

Business logic for broker order operations.
"""

from __future__ import annotations

from typing import Any, Dict

from app.auth import UpstoxAuth
from app.market_data import MarketData


class OrderService:
    """
    Handles broker order operations.

    This layer contains business rules.
    It should be used by FastAPI endpoints instead of calling
    MarketData directly.
    """

    def __init__(self) -> None:
        self.auth = UpstoxAuth()
        self.market = MarketData()

    def place_order(
        self,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Place an order after loading the broker token.
        """

        token = self.auth.get_token()

        return self.market.place_order(
            token=token,
            payload=payload,
        )
