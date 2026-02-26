"""
Trading tools - Buy and sell operations.

Supports US stocks, China A-shares, and cryptocurrency.
"""

import fcntl
import sys
from pathlib import Path
from typing import Any, Dict

from tools import tool

# Ensure project root is in path
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from tools.general_tools import get_config_value, write_config_value
from tools.price_tools import get_open_prices
from tools.trading_db import (
    get_latest_position,
    append_position,
    get_total_bought_today,
    get_db_path,
    init_db,
)


def _position_lock(signature: str):
    """Context manager for file-based lock."""
    class _Lock:
        def __init__(self, name: str):
            log_path = get_config_value("LOG_PATH", "./data/agent_data")
            if log_path.startswith("./data/"):
                log_rel = log_path[7:]
            else:
                log_rel = log_path
            base_dir = Path(project_root) / "data" / log_rel / name
            base_dir.mkdir(parents=True, exist_ok=True)
            self.lock_path = base_dir / ".position.lock"
            self._fh = open(self.lock_path, "a+")

        def __enter__(self):
            fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX)
            return self

        def __exit__(self, exc_type, exc, tb):
            try:
                fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
            finally:
                self._fh.close()

    return _Lock(signature)


def _get_db_info():
    """Get database path and market type."""
    log_path = get_config_value("LOG_PATH", "./data/agent_data")

    if "astock" in str(log_path).lower():
        db_market = "astock"
    elif "crypto" in str(log_path).lower():
        db_market = "crypto"
    else:
        db_market = "agent_data"

    db_path = get_db_path(db_market)
    init_db(db_path)
    return db_path, db_market


def _get_market_type(symbol: str) -> str:
    """Determine market type from symbol."""
    if symbol.endswith((".SH", ".SZ")):
        return "cn"
    return "us"


@tool(description="Buy stocks")
def buy(symbol: str, amount: int) -> Dict[str, Any]:
    """Buy stocks.

    Args:
        symbol: Stock symbol (e.g., "AAPL", "600519.SH")
        amount: Number of shares to buy
                Chinese A-shares: must be multiples of 100

    Returns:
        Updated position dictionary or error
    """
    signature = get_config_value("SIGNATURE")
    today_date = get_config_value("TODAY_DATE")

    if not signature:
        raise ValueError("SIGNATURE not set")
    if not today_date:
        raise ValueError("TODAY_DATE not set")

    market = _get_market_type(symbol)

    # Validate amount
    try:
        amount = int(amount)
    except ValueError:
        return {"error": "Amount must be an integer", "symbol": symbol}

    if amount <= 0:
        return {"error": "Amount must be positive", "symbol": symbol, "amount": amount}

    # Chinese A-shares: multiples of 100
    if market == "cn" and amount % 100 != 0:
        return {
            "error": "Chinese A-shares must be multiples of 100",
            "symbol": symbol,
            "suggestion": f"Use {(amount // 100) * 100} or {((amount // 100) + 1) * 100}"
        }

    db_path, db_market = _get_db_info()

    # Get current position
    with _position_lock(signature):
        current_position, _ = get_latest_position(signature, db_path, db_market)

    # Get price
    try:
        price = get_open_prices(today_date, [symbol], market=market)[f"{symbol}_price"]
    except KeyError:
        return {"error": f"Symbol {symbol} not found", "symbol": symbol}

    if price is None:
        return {"error": f"Price not available for {symbol}", "symbol": symbol}

    # Check cash
    cash_needed = price * amount
    if current_position.get("CASH", 0) < cash_needed:
        return {
            "error": "Insufficient cash",
            "required": cash_needed,
            "available": current_position.get("CASH", 0)
        }

    # Execute buy
    new_position = current_position.copy()
    new_position["CASH"] -= cash_needed
    new_position[symbol] = new_position.get(symbol, 0) + amount

    append_position(
        signature=signature, date=today_date, action_type="buy",
        symbol=symbol, amount=amount, positions=new_position,
        db_path=db_path, market=db_market
    )

    write_config_value("IF_TRADE", True)
    return new_position


@tool(description="Sell stocks")
def sell(symbol: str, amount: int) -> Dict[str, Any]:
    """Sell stocks.

    Args:
        symbol: Stock symbol (e.g., "AAPL")
        amount: Number of shares to sell

    Returns:
        Updated position dictionary or error
    """
    signature = get_config_value("SIGNATURE")
    today_date = get_config_value("TODAY_DATE")

    if not signature:
        raise ValueError("SIGNATURE not set")
    if not today_date:
        raise ValueError("TODAY_DATE not set")

    market = _get_market_type(symbol)

    # Validate amount
    try:
        amount = int(amount)
    except ValueError:
        return {"error": "Amount must be an integer", "symbol": symbol}

    if amount <= 0:
        return {"error": "Amount must be positive", "symbol": symbol}

    db_path, db_market = _get_db_info()

    # Get current position
    current_position, _ = get_latest_position(signature, db_path, db_market)

    # Check position
    if symbol not in current_position:
        return {"error": f"No position for {symbol}", "symbol": symbol}

    if current_position[symbol] < amount:
        return {
            "error": "Insufficient shares",
            "held": current_position.get(symbol, 0),
            "requested": amount
        }

    # Get price
    try:
        price = get_open_prices(today_date, [symbol], market=market)[f"{symbol}_price"]
    except KeyError:
        return {"error": f"Symbol {symbol} not found", "symbol": symbol}

    # Execute sell
    new_position = current_position.copy()
    new_position[symbol] -= amount
    new_position["CASH"] = new_position.get("CASH", 0) + price * amount

    append_position(
        signature=signature, date=today_date, action_type="sell",
        symbol=symbol, amount=amount, positions=new_position,
        db_path=db_path, market=db_market
    )

    write_config_value("IF_TRADE", True)
    return new_position


@tool(description="Buy cryptocurrency")
def buy_crypto(symbol: str, amount: float) -> Dict[str, Any]:
    """Buy cryptocurrency (e.g., BTC-USDT).

    Args:
        symbol: Crypto symbol (e.g., "BTC-USDT")
        amount: Amount to buy

    Returns:
        Updated position dictionary
    """
    return buy(symbol, int(amount))


@tool(description="Sell cryptocurrency")
def sell_crypto(symbol: str, amount: float) -> Dict[str, Any]:
    """Sell cryptocurrency.

    Args:
        symbol: Crypto symbol (e.g., "BTC-USDT")
        amount: Amount to sell

    Returns:
        Updated position dictionary
    """
    return sell(symbol, int(amount))
