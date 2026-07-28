"""
config.py

Central application configuration.

All paths, instrument keys, and tunable runtime settings live here so
other modules never hardcode them. Values can be overridden via
environment variables without touching code.
"""

from __future__ import annotations

import os
from pathlib import Path

# ==========================
# Project Paths
# ==========================

BASE_DIR = Path(__file__).resolve().parent.parent

TOKEN_FILE = os.getenv("TOKEN_FILE", str(BASE_DIR / "token.json"))

DATABASE_DIR = BASE_DIR / "database"
PAPER_TRADES_DB_PATH = os.getenv(
    "PAPER_TRADES_DB_PATH", str(DATABASE_DIR / "paper_trades.db")
)

# ==========================
# Upstox API
# ==========================

UPSTOX_BASE_URL = os.getenv("UPSTOX_BASE_URL", "https://api.upstox.com")
REQUEST_TIMEOUT_SECONDS = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "10"))

if REQUEST_TIMEOUT_SECONDS <= 0:
    raise ValueError("REQUEST_TIMEOUT_SECONDS must be greater than zero.")

# ==========================
# Instruments
# ==========================
# Underlying instrument keys the assistant tracks.
# Extend this mapping only with values confirmed live from Upstox;
# never invent an instrument_key.

INSTRUMENTS = {
    "NIFTY": "NSE_INDEX|Nifty 50",
    "BANKNIFTY": "NSE_INDEX|Nifty Bank",
    "SENSEX": "BSE_INDEX|SENSEX",
}

DEFAULT_INSTRUMENT = os.getenv("DEFAULT_INSTRUMENT", "NIFTY")

if DEFAULT_INSTRUMENT not in INSTRUMENTS:
    raise ValueError(f"Unknown DEFAULT_INSTRUMENT: {DEFAULT_INSTRUMENT}")

# ==========================
# Live Loop
# ==========================

LIVE_LOOP_INTERVAL_SECONDS = int(os.getenv("LIVE_LOOP_INTERVAL_SECONDS", "5"))
PRICE_TICK_INTERVAL_SECONDS = int(os.getenv("PRICE_TICK_INTERVAL_SECONDS", "1"))

# ==========================
# Server
# ==========================

API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
if not (1 <= API_PORT <= 65535):
    raise ValueError("API_PORT must be between 1 and 65535.")

# ==========================
# Logging
# ==========================

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

VALID_LOG_LEVELS = {
    "DEBUG",
    "INFO",
    "WARNING",
    "ERROR",
    "CRITICAL",
}

if LOG_LEVEL not in VALID_LOG_LEVELS:
    raise ValueError(
        f"Invalid LOG_LEVEL: {LOG_LEVEL}. "
        f"Must be one of: {', '.join(sorted(VALID_LOG_LEVELS))}"
    )

MIN_PROFIT_RUPEES = float(os.getenv("MIN_PROFIT_RUPEES", "300"))
if MIN_PROFIT_RUPEES < 0:
    raise ValueError("MIN_PROFIT_RUPEES cannot be negative.")
