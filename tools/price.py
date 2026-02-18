"""
Price tools - Get stock prices from multiple data sources.

Supported sources:
- local: Local SQLite database (default)
- yahoo: Yahoo Finance (free, delayed ~15min)
- alpaca: Alpaca (real-time, requires API key)
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from tools import tool

# Ensure project root is in path
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from tools.general_tools import get_config_value
from tools.market_api import (
    get_market_adapter,
    MarketConfig,
)


def _get_adapter() -> Any:
    """Get market adapter with config from environment."""
    import os
    import json

    config_json = os.getenv("MARKET_API_CONFIG")
    if config_json:
        try:
            config = json.loads(config_json)
        except json.JSONDecodeError:
            config = {}
    else:
        data_source_price = os.getenv("DATA_SOURCE_PRICE", "local")
        trading_mode = os.getenv("TRADING_MODE", "simulation")
        config = {
            "data_source": {"price": data_source_price},
            "trading_mode": trading_mode
        }

    return get_market_adapter(config)


def _get_market_type(symbol: str) -> str:
    """Determine market type from symbol."""
    if symbol.endswith((".SH", ".SZ")):
        return "astock"
    elif symbol.endswith("-USDT"):
        return "crypto"
    return "us"


@tool(description="Get OHLCV price data for a stock at a specific date")
def get_price(symbol: str, date: str) -> Dict[str, Any]:
    """Get OHLCV price data for a stock symbol at a specific date.

    Args:
        symbol: Stock symbol (e.g., "AAPL", "600519.SH")
        date: Date in "YYYY-MM-DD" format

    Returns:
        Dictionary with symbol, date, ohlcv data, and source
    """
    market = _get_market_type(symbol)
    adapter = _get_adapter()
    price_data = adapter.get_price(symbol, date, market)

    if price_data:
        return {
            "symbol": symbol,
            "date": date,
            "ohlcv": {
                "open": price_data.get("buy_price"),
                "high": price_data.get("high_price") or price_data.get("high"),
                "low": price_data.get("low_price") or price_data.get("low"),
                "close": price_data.get("sell_price") or price_data.get("close"),
                "volume": price_data.get("volume"),
            },
            "source": price_data.get("source", "unknown"),
        }
    return {"error": f"Price not found for {symbol} on {date}", "symbol": symbol, "date": date}


@tool(description="Get OHLCV price data for a stock over a date range")
def get_prices_range(symbol: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """Get OHLCV price data for a stock over a date range.

    Args:
        symbol: Stock symbol (e.g., "AAPL")
        start_date: Start date in "YYYY-MM-DD" format
        end_date: End date in "YYYY-MM-DD" format

    Returns:
        List of price records
    """
    market = _get_market_type(symbol)
    adapter = _get_adapter()
    start_time = f"{start_date} 00:00:00"
    end_time = f"{end_date} 23:59:59"

    prices = adapter.get_prices_range(symbol, start_time, end_time, market)

    result = []
    for p in prices:
        result.append({
            "symbol": symbol,
            "date": p.get("timestamp", "").split()[0] if p.get("timestamp") else "",
            "ohlcv": {
                "open": p.get("buy_price") or p.get("open"),
                "high": p.get("high_price") or p.get("high"),
                "low": p.get("low_price") or p.get("low"),
                "close": p.get("sell_price") or p.get("close"),
                "volume": p.get("volume"),
            },
            "source": p.get("source", "unknown"),
        })
    return result


@tool(description="Get the latest price for a stock symbol")
def get_latest_price(symbol: str) -> Dict[str, Any]:
    """Get the latest price for a stock symbol.

    Args:
        symbol: Stock symbol (e.g., "AAPL")

    Returns:
        Dictionary with current price info
    """
    import datetime
    market = _get_market_type(symbol)
    adapter = _get_adapter()
    price_data = adapter.get_latest_price(symbol, market)

    if price_data:
        return {
            "symbol": symbol,
            "timestamp": datetime.datetime.now().isoformat(),
            "buy_price": price_data.get("buy_price") or price_data.get("ask_price"),
            "sell_price": price_data.get("sell_price") or price_data.get("bid_price"),
            "source": price_data.get("source", "unknown"),
        }
    return {"error": f"Price not available for {symbol}", "symbol": symbol}


@tool(description="Search for stock symbols matching a query")
def search_symbol(query: str) -> List[Dict[str, Any]]:
    """Search for stock symbols matching a query.

    Args:
        query: Search query (e.g., "Apple")

    Returns:
        List of matching symbols
    """
    adapter = _get_adapter()
    results = adapter.search_symbol(query, "us")

    if results:
        return results

    # Fallback
    return [
        {"symbol": "AAPL", "name": "Apple Inc.", "exchange": "NASDAQ"},
        {"symbol": "MSFT", "name": "Microsoft Corporation", "exchange": "NASDAQ"},
    ]
