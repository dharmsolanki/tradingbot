"""
Base Broker Interface

Every broker implementation (Upstox, Zerodha, Angel One, Shoonya)
must implement this interface.

The rest of the application should never directly depend on a broker SDK.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BaseBroker(ABC):
    """Abstract interface for broker integrations."""

    @abstractmethod
    def is_connected(self) -> bool:
        """Return True if broker authentication is valid."""
        raise NotImplementedError

    @abstractmethod
    def get_profile(self) -> Dict[str, Any]:
        """Return logged-in user profile."""
        raise NotImplementedError

    @abstractmethod
    def get_funds(self) -> Dict[str, Any]:
        """Return available funds and margin information."""
        raise NotImplementedError

    @abstractmethod
    def get_positions(self) -> List[Dict[str, Any]]:
        """Return all open positions."""
        raise NotImplementedError

    @abstractmethod
    def get_orders(self) -> List[Dict[str, Any]]:
        """Return today's orders."""
        raise NotImplementedError

    @abstractmethod
    def get_tradebook(self) -> List[Dict[str, Any]]:
        """Return executed trades."""
        raise NotImplementedError

    @abstractmethod
    def place_order(self, **kwargs) -> Dict[str, Any]:
        """Place a live order."""
        raise NotImplementedError

    @abstractmethod
    def exit_position(self, **kwargs) -> Dict[str, Any]:
        """Exit an existing position."""
        raise NotImplementedError

    @abstractmethod
    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel a pending order."""
        raise NotImplementedError
