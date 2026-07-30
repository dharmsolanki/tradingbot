from app.constants import (
    TRADE_OPEN,
    TRADE_CLOSED,
    TRADE_CANCELLED,
)

"""
Database schema definitions.

All CREATE TABLE statements live here.
"""

CREATE_PAPER_TRADES_TABLE = f"""
CREATE TABLE IF NOT EXISTS paper_trades (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    trade_id TEXT NOT NULL UNIQUE,

    symbol TEXT NOT NULL,
    instrument_key TEXT NOT NULL,

    option_type TEXT NOT NULL,

    strike REAL NOT NULL,
    expiry TEXT NOT NULL,

    quantity INTEGER NOT NULL CHECK(quantity > 0),

    entry_price REAL NOT NULL,
    exit_price REAL,

    stop_loss REAL NOT NULL,
    target REAL NOT NULL,

    status TEXT NOT NULL
    CHECK(status IN ('{TRADE_OPEN}', '{TRADE_CLOSED}', '{TRADE_CANCELLED}')),

    confidence INTEGER DEFAULT 0,
    score INTEGER DEFAULT 0,

    entry_reason TEXT,
    exit_reason TEXT,

    entry_time TEXT NOT NULL,
    exit_time TEXT,

    gross_pnl REAL DEFAULT 0,
    brokerage REAL DEFAULT 0,
    charges REAL DEFAULT 0,
    net_pnl REAL DEFAULT 0
);
"""


CREATE_INDEXES = [
    """
    CREATE INDEX IF NOT EXISTS idx_trade_status
    ON paper_trades(status);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_trade_symbol
    ON paper_trades(symbol);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_trade_entry_time
    ON paper_trades(entry_time);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_trade_trade_id
    ON paper_trades(trade_id);
    """,
]
CREATE_BROKER_ORDERS_TABLE = """
CREATE TABLE IF NOT EXISTS broker_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    broker_order_id TEXT UNIQUE NOT NULL,
    recommendation_id TEXT,

    instrument_key TEXT NOT NULL,
    symbol TEXT,

    transaction_type TEXT NOT NULL,
    product TEXT NOT NULL,
    order_type TEXT NOT NULL,

    quantity INTEGER NOT NULL,

    requested_price REAL,
    average_price REAL,

    status TEXT NOT NULL,

    exchange_order_id TEXT,

    raw_response TEXT,

    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""
