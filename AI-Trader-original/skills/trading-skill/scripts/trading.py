"""
Trading execution tools.
"""

import fcntl
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[3]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from tools.general_tools import get_config_value, write_config_value
from tools.price_tools import get_open_prices
from tools.trading_db import (
    get_latest_position, append_position, get_db_path, init_db
)


def buy(symbol: str, amount: int) -> dict:
    """Buy stocks."""
    signature = get_config_value("SIGNATURE")
    today_date = get_config_value("TODAY_DATE")

    if not signature or not today_date:
        return {"error": "SIGNATURE or TODAY_DATE not set"}

    market = _get_market(symbol)

    try:
        amount = int(amount)
    except ValueError:
        return {"error": "Amount must be integer"}

    if amount <= 0:
        return {"error": "Amount must be positive"}

    if market == "cn" and amount % 100 != 0:
        return {"error": "China A-shares: multiples of 100 only"}

    db_path, db_market = _get_db()

    with _lock(signature):
        position, _ = get_latest_position(signature, db_path, db_market)

    try:
        price = get_open_prices(today_date, [symbol], market=market)[f"{symbol}_price"]
    except KeyError:
        return {"error": f"Symbol {symbol} not found"}

    if price is None:
        return {"error": f"Price not available for {symbol}"}

    if position.get("CASH", 0) < price * amount:
        return {"error": "Insufficient cash"}

    new_pos = position.copy()
    new_pos["CASH"] -= price * amount
    new_pos[symbol] = new_pos.get(symbol, 0) + amount

    append_position(signature, today_date, "buy", symbol, amount, new_pos, db_path, db_market)
    write_config_value("IF_TRADE", True)
    return new_pos


def sell(symbol: str, amount: int) -> dict:
    """Sell stocks."""
    signature = get_config_value("SIGNATURE")
    today_date = get_config_value("TODAY_DATE")

    if not signature or not today_date:
        return {"error": "SIGNATURE or TODAY_DATE not set"}

    market = _get_market(symbol)

    try:
        amount = int(amount)
    except ValueError:
        return {"error": "Amount must be integer"}

    if amount <= 0:
        return {"error": "Amount must be positive"}

    db_path, db_market = _get_db()
    position, _ = get_latest_position(signature, db_path, db_market)

    if symbol not in position:
        return {"error": f"No position for {symbol}"}

    if position[symbol] < amount:
        return {"error": "Insufficient shares"}

    try:
        price = get_open_prices(today_date, [symbol], market=market)[f"{symbol}_price"]
    except KeyError:
        return {"error": f"Symbol {symbol} not found"}

    new_pos = position.copy()
    new_pos[symbol] -= amount
    new_pos["CASH"] = new_pos.get("CASH", 0) + price * amount

    append_position(signature, today_date, "sell", symbol, amount, new_pos, db_path, db_market)
    write_config_value("IF_TRADE", True)
    return new_pos


def buy_crypto(symbol: str, amount: float) -> dict:
    """Buy cryptocurrency."""
    return buy(symbol, int(amount))


def sell_crypto(symbol: str, amount: float) -> dict:
    """Sell cryptocurrency."""
    return sell(symbol, int(amount))


def _get_market(symbol: str) -> str:
    """Determine market from symbol."""
    if symbol.endswith((".SH", ".SZ")):
        return "cn"
    return "us"


def _get_db():
    """Get database path."""
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


def _lock(signature: str):
    """File lock context manager."""
    class Lk:
        def __init__(self, name):
            log_path = get_config_value("LOG_PATH", "./data/agent_data")
            base_dir = Path(project_root) / "data" / log_path.split("/")[-1] / name
            base_dir.mkdir(parents=True, exist_ok=True)
            self.path = base_dir / ".lock"
            self.fh = open(self.path, "a+")

        def __enter__(self):
            fcntl.flock(self.fh.fileno(), fcntl.LOCK_EX)
            return self

        def __exit__(self, *args):
            fcntl.flock(self.fh.fileno(), fcntl.LOCK_UN)
            self.fh.close()

    return Lk(signature)
