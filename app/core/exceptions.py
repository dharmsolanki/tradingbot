"""
Custom exceptions for the trading framework.
"""


class TradingError(Exception):
    """Base exception for all trading-related errors."""


# ==========================
# Database Exceptions
# ==========================


class DatabaseError(TradingError):
    """Raised when a database operation fails."""


# ==========================
# Trade Exceptions
# ==========================


class InvalidTradeError(TradingError):
    """Raised when a trade is invalid."""


class TradeAlreadyOpenError(TradingError):
    """Raised when an open trade already exists."""


class TradeNotFoundError(TradingError):
    """Raised when a trade cannot be found."""


class TradeClosedError(TradingError):
    """Raised when attempting to modify a closed trade."""


# ==========================
# Market Data Exceptions
# ==========================


class MarketDataError(TradingError):
    """Raised when market data cannot be retrieved."""


class InstrumentNotFoundError(MarketDataError):
    """Raised when an instrument key is invalid."""


# ==========================
# Authentication Exceptions
# ==========================


class AuthenticationError(TradingError):
    """Raised when authentication fails."""


class TokenExpiredError(AuthenticationError):
    """Raised when access token has expired."""


# ==========================
# Risk Exceptions
# ==========================


class RiskValidationError(TradingError):
    """Raised when risk rules fail."""
