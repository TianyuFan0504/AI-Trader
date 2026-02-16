"""
Simple SQLite database for trading records.
Replaces JSONL file storage with a lightweight database.

Tables:
- positions: Trading records (buy/sell/no_trade actions)
- logs: Agent conversation logs
- prices: Market price data (OHLCV)
"""

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Get project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "trading.db"


def get_db_path(market: str = "agent_data") -> Path:
    """Get database path for specific market."""
    if market == "crypto":
        return PROJECT_ROOT / "data" / "crypto" / "trading.db"
    elif market == "astock":
        return PROJECT_ROOT / "data" / "A_stock" / "trading.db"
    elif market == "prices":
        return PROJECT_ROOT / "data" / "prices.db"
    return PROJECT_ROOT / "data" / "trading.db"


def init_db(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Initialize database and create tables if they don't exist."""
    if db_path is None:
        db_path = DB_PATH

    # Ensure directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Create positions table (trading records)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signature TEXT NOT NULL,
            date TEXT NOT NULL,
            action_type TEXT,
            symbol TEXT,
            amount INTEGER,
            positions_json TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create logs table (agent conversation logs)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signature TEXT NOT NULL,
            log_date TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create prices table (market price data)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            market TEXT NOT NULL,
            buy_price REAL,
            sell_price REAL,
            high_price REAL,
            low_price REAL,
            volume REAL,
            raw_data TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(symbol, timestamp, market)
        )
    """)

    # Create indexes for faster queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_positions_signature_date
        ON positions(signature, date)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_logs_signature_date
        ON logs(signature, log_date)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_prices_symbol_timestamp
        ON prices(symbol, timestamp, market)
    """)

    conn.commit()
    return conn


# ==================== Position Functions ====================

def get_latest_position(signature: str, db_path: Optional[Path] = None, market: str = "agent_data") -> Tuple[Dict[str, Any], int]:
    """Get the latest position record for a signature."""
    if db_path is None:
        db_path = get_db_path(market)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, positions_json FROM positions
        WHERE signature = ?
        ORDER BY id DESC LIMIT 1
    """, (signature,))

    row = cursor.fetchone()
    conn.close()

    if row:
        return json.loads(row["positions_json"]), row["id"]
    else:
        return {"CASH": 0}, 0


def append_position(
    signature: str,
    date: str,
    action_type: str,
    symbol: str,
    amount: int,
    positions: Dict[str, Any],
    db_path: Optional[Path] = None,
    market: str = "agent_data"
) -> int:
    """Append a new position record."""
    if db_path is None:
        db_path = get_db_path(market)

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO positions (signature, date, action_type, symbol, amount, positions_json)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (signature, date, action_type, symbol, amount, json.dumps(positions)))

    new_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return new_id


def append_no_trade_record(
    signature: str,
    date: str,
    positions: Dict[str, Any],
    current_id: int,
    db_path: Optional[Path] = None,
    market: str = "agent_data"
) -> int:
    """Append a no-trade record."""
    return append_position(
        signature=signature,
        date=date,
        action_type="no_trade",
        symbol="",
        amount=0,
        positions=positions,
        db_path=db_path,
        market=market
    )


def get_position_history(
    signature: str,
    db_path: Optional[Path] = None
) -> List[Dict[str, Any]]:
    """Get all position history for a signature."""
    if db_path is None:
        db_path = DB_PATH

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, signature, date, action_type, symbol, amount, positions_json, created_at
        FROM positions
        WHERE signature = ?
        ORDER BY id ASC
    """, (signature,))

    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "id": row["id"],
            "signature": row["signature"],
            "date": row["date"],
            "action_type": row["action_type"],
            "symbol": row["symbol"],
            "amount": row["amount"],
            "positions": json.loads(row["positions_json"]),
            "created_at": row["created_at"]
        }
        for row in rows
    ]


def check_position_exists(signature: str, db_path: Optional[Path] = None) -> bool:
    """Check if any position record exists for the signature."""
    if db_path is None:
        db_path = DB_PATH

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 1 FROM positions WHERE signature = ? LIMIT 1
    """, (signature,))

    exists = cursor.fetchone() is not None
    conn.close()

    return exists


# ==================== Log Functions ====================

def append_log(
    signature: str,
    log_date: str,
    role: str,
    content: str,
    db_path: Optional[Path] = None,
    market: str = "agent_data"
) -> int:
    """Append a log entry."""
    if db_path is None:
        db_path = get_db_path(market)

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO logs (signature, log_date, role, content)
        VALUES (?, ?, ?, ?)
    """, (signature, log_date, role, content))

    new_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return new_id


def get_logs(
    signature: str,
    log_date: str,
    db_path: Optional[Path] = None
) -> List[Dict[str, Any]]:
    """Get all logs for a signature and date."""
    if db_path is None:
        db_path = DB_PATH

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, signature, log_date, role, content, created_at
        FROM logs
        WHERE signature = ? AND log_date = ?
        ORDER BY id ASC
    """, (signature, log_date))

    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "id": row["id"],
            "signature": row["signature"],
            "log_date": row["log_date"],
            "role": row["role"],
            "content": row["content"],
            "created_at": row["created_at"]
        }
        for row in rows
    ]


def get_all_logs(
    signature: str,
    db_path: Optional[Path] = None
) -> List[Dict[str, Any]]:
    """Get all logs for a signature."""
    if db_path is None:
        db_path = DB_PATH

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, signature, log_date, role, content, created_at
        FROM logs
        WHERE signature = ?
        ORDER BY log_date ASC, id ASC
    """, (signature,))

    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "id": row["id"],
            "signature": row["signature"],
            "log_date": row["log_date"],
            "role": row["role"],
            "content": row["content"],
            "created_at": row["created_at"]
        }
        for row in rows
    ]


# ==================== Price Functions ====================

def add_price(
    symbol: str,
    timestamp: str,
    market: str,
    buy_price: Optional[float] = None,
    sell_price: Optional[float] = None,
    high_price: Optional[float] = None,
    low_price: Optional[float] = None,
    volume: Optional[float] = None,
    raw_data: Optional[Dict[str, Any]] = None,
    db_path: Optional[Path] = None
) -> int:
    """Add a price record. Uses UPSERT to handle duplicates."""
    if db_path is None:
        db_path = get_db_path("prices")

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO prices (symbol, timestamp, market, buy_price, sell_price, high_price, low_price, volume, raw_data)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(symbol, timestamp, market) DO UPDATE SET
            buy_price = COALESCE(EXCLUDED.buy_price, prices.buy_price),
            sell_price = COALESCE(EXCLUDED.sell_price, prices.sell_price),
            high_price = COALESCE(EXCLUDED.high_price, prices.high_price),
            low_price = COALESCE(EXCLUDED.low_price, prices.low_price),
            volume = COALESCE(EXCLUDED.volume, prices.volume),
            raw_data = COALESCE(EXCLUDED.raw_data, prices.raw_data)
    """, (
        symbol,
        timestamp,
        market,
        buy_price,
        sell_price,
        high_price,
        low_price,
        volume,
        json.dumps(raw_data) if raw_data else None
    ))

    new_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return new_id


def get_price(
    symbol: str,
    timestamp: str,
    market: str,
    db_path: Optional[Path] = None
) -> Optional[Dict[str, Any]]:
    """Get a specific price record."""
    if db_path is None:
        db_path = get_db_path("prices")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM prices
        WHERE symbol = ? AND timestamp = ? AND market = ?
    """, (symbol, timestamp, market))

    row = cursor.fetchone()
    conn.close()

    if row:
        return dict(row)
    return None


def get_prices_range(
    symbol: str,
    start_time: str,
    end_time: str,
    market: str,
    db_path: Optional[Path] = None
) -> List[Dict[str, Any]]:
    """Get all price records for a symbol within a time range."""
    if db_path is None:
        db_path = get_db_path("prices")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM prices
        WHERE symbol = ? AND timestamp >= ? AND timestamp <= ? AND market = ?
        ORDER BY timestamp ASC
    """, (symbol, start_time, end_time, market))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_prices_by_symbol(
    symbol: str,
    market: str,
    limit: int = 1000,
    db_path: Optional[Path] = None
) -> List[Dict[str, Any]]:
    """Get all price records for a symbol."""
    if db_path is None:
        db_path = get_db_path("prices")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM prices
        WHERE symbol = ? AND market = ?
        ORDER BY timestamp DESC
        LIMIT ?
    """, (symbol, market, limit))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_all_prices(
    market: str,
    db_path: Optional[Path] = None
) -> List[Dict[str, Any]]:
    """Get all price records for a market."""
    if db_path is None:
        db_path = get_db_path("prices")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM prices
        WHERE market = ?
        ORDER BY symbol ASC, timestamp ASC
    """, (market,))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_symbols(market: str, db_path: Optional[Path] = None) -> List[str]:
    """Get all unique symbols for a market."""
    if db_path is None:
        db_path = get_db_path("prices")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT symbol FROM prices
        WHERE market = ?
        ORDER BY symbol
    """, (market,))

    rows = cursor.fetchall()
    conn.close()

    return [row["symbol"] for row in rows]


def get_all_timestamps(market: str, db_path: Optional[Path] = None) -> List[str]:
    """Get all unique timestamps for a market."""
    if db_path is None:
        db_path = get_db_path("prices")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT timestamp FROM prices
        WHERE market = ?
        ORDER BY timestamp
    """, (market,))

    rows = cursor.fetchall()
    conn.close()

    return [row["timestamp"] for row in rows]


def get_timestamps_for_symbol(
    symbol: str,
    market: str,
    db_path: Optional[Path] = None
) -> List[str]:
    """Get all timestamps for a specific symbol."""
    if db_path is None:
        db_path = get_db_path("prices")

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT timestamp FROM prices
        WHERE symbol = ? AND market = ?
        ORDER BY timestamp
    """, (symbol, market))

    rows = cursor.fetchall()
    conn.close()

    return [row["timestamp"] for row in rows]


def check_price_exists(
    symbol: str,
    timestamp: str,
    market: str,
    db_path: Optional[Path] = None
) -> bool:
    """Check if a price record exists."""
    if db_path is None:
        db_path = get_db_path("prices")

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 1 FROM prices
        WHERE symbol = ? AND timestamp = ? AND market = ?
        LIMIT 1
    """, (symbol, timestamp, market))

    exists = cursor.fetchone() is not None
    conn.close()

    return exists


def close_db(conn: sqlite3.Connection):
    """Close database connection."""
    if conn:
        conn.close()


def get_total_bought_today(
    signature: str,
    today_date: str,
    symbol: str,
    db_path: Optional[Path] = None
) -> int:
    """Get total amount bought today for a specific symbol.

    Args:
        signature: Agent signature
        today_date: Date string (YYYY-MM-DD)
        symbol: Stock symbol
        db_path: Database path

    Returns:
        Total amount bought today
    """
    if db_path is None:
        db_path = DB_PATH

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COALESCE(SUM(amount), 0) as total
        FROM positions
        WHERE signature = ? AND date = ? AND action_type = 'buy' AND symbol = ?
    """, (signature, today_date, symbol))

    result = cursor.fetchone()
    conn.close()

    return result[0] if result else 0
