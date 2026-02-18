"""
Price data retrieval tools.
"""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[3]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from tools.market_api import get_market_adapter


def get_price(symbol: str, date: str) -> dict:
    """Get OHLCV price for a specific date."""
    market = _get_market(symbol)
    adapter = _get_adapter()
    data = adapter.get_price(symbol, date, market)

    if data:
        return {
            "symbol": symbol,
            "date": date,
            "open": data.get("buy_price"),
            "close": data.get("sell_price"),
            "high": data.get("high_price"),
            "low": data.get("low_price"),
            "volume": data.get("volume"),
            "source": data.get("source", "unknown"),
        }
    return {"error": f"Price not found for {symbol} on {date}"}


def get_prices_range(symbol: str, start_date: str, end_date: str) -> list:
    """Get price history over a date range."""
    market = _get_market(symbol)
    adapter = _get_adapter()
    start = f"{start_date} 00:00:00"
    end = f"{end_date} 23:59:59"

    prices = adapter.get_prices_range(symbol, start, end, market)
    return [{"symbol": symbol, "date": p.get("timestamp", ""), **p} for p in prices]


def get_latest_price(symbol: str) -> dict:
    """Get current market price."""
    import datetime
    market = _get_market(symbol)
    adapter = _get_adapter()
    data = adapter.get_latest_price(symbol, market)

    if data:
        return {
            "symbol": symbol,
            "timestamp": datetime.datetime.now().isoformat(),
            "buy": data.get("buy_price"),
            "sell": data.get("sell_price"),
            "source": data.get("source", "unknown"),
        }
    return {"error": f"Price not available for {symbol}"}


def search_symbol(query: str) -> list:
    """Search for stock symbols."""
    adapter = _get_adapter()
    results = adapter.search_symbol(query, "us")
    return results or [{"symbol": "AAPL", "name": "Apple Inc."}]


def _get_market(symbol: str) -> str:
    """Determine market type from symbol."""
    if symbol.endswith((".SH", ".SZ")):
        return "astock"
    elif symbol.endswith("-USDT"):
        return "crypto"
    return "us"


def _get_adapter():
    """Get market adapter with config."""
    import os
    import json

    config_json = os.getenv("MARKET_API_CONFIG")
    if config_json:
        try:
            config = json.loads(config_json)
        except json.JSONDecodeError:
            config = {}
    else:
        config = {
            "data_source": {"price": os.getenv("DATA_SOURCE_PRICE", "local")},
            "trading_mode": os.getenv("TRADING_MODE", "simulation")
        }
    return get_market_adapter(config)
