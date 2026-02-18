"""
Market Data API Adapter for real-time and historical price data.

Supports:
- Yahoo Finance (free, delayed ~15min for US stocks)
- Alpaca (real-time for US stocks, requires API key)
- Tushare Pro (China A-shares, requires token)

Configuration:
{
    "data_source": {
        "price": "yahoo",     // yahoo, alpaca, tushare, local
        "search": "local",     // local, jina
        "news": "local"       // local, jina
    },
    "trading_mode": "simulation"  // simulation, paper, live
}

Usage:
    from tools.market_api import get_market_adapter

    adapter = get_market_adapter(config)
    price = adapter.get_price("AAPL", "2025-11-10", "us")
"""

import os
import json
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()


# =============================================================================
# Enums
# =============================================================================

class DataSource(str, Enum):
    """Supported data sources."""
    LOCAL = "local"
    ALPACA = "alpaca"
    YAHOO = "yahoo"
    TUSHARE = "tushare"


class TradingMode(str, Enum):
    """Trading mode options."""
    SIMULATION = "simulation"  # Simulated trading with local data
    PAPER = "paper"           # Paper trading with real-time data
    LIVE = "live"             # Live trading with real money


# =============================================================================
# Configuration
# =============================================================================

class MarketConfig:
    """Configuration for market data source."""

    def __init__(
        self,
        price_source: str = "local",
        search_source: str = "local",
        news_source: str = "local",
        trading_mode: str = "simulation"
    ):
        self.price_source = price_source
        self.search_source = search_source
        self.news_source = news_source
        self.trading_mode = trading_mode

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "MarketConfig":
        """Create from config dictionary."""
        data_source = config.get("data_source", {})
        trading_mode = config.get("trading_mode", "simulation")

        return cls(
            price_source=data_source.get("price", "local"),
            search_source=data_source.get("search", "local"),
            news_source=data_source.get("news", "local"),
            trading_mode=trading_mode
        )

    def is_live_trading(self) -> bool:
        """Check if live trading is enabled."""
        return self.trading_mode == "live"

    def use_real_time_data(self) -> bool:
        """Check if real-time data should be used."""
        return self.trading_mode in ["paper", "live"]

    def need_price_api(self) -> bool:
        """Check if external price API is needed."""
        return self.price_source != "local"


# =============================================================================
# Yahoo Finance API
# =============================================================================

class YahooFinanceAPI:
    """
    Yahoo Finance API for delayed US stock data.

    Features:
    - Free to use
    - Data delayed by ~15 minutes
    - No API key required

    Note: Only supports US stocks
    """

    BASE_URL = "https://query1.finance.yahoo.com/v8/finance"

    def __init__(self):
        pass

    def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get delayed quote for a symbol.

        Args:
            symbol: Stock symbol (e.g., "AAPL", "NVDA")

        Returns:
            Price dictionary or None if not found
        """
        url = f"{self.BASE_URL}/chart/{symbol}"

        try:
            with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                response = client.get(url)
                response.raise_for_status()
                data = response.json()

                result = data.get("chart", {}).get("result", [])
                if not result:
                    return None

                meta = result[0].get("meta", {})

                return {
                    "symbol": symbol,
                    "buy_price": meta.get("regularMarketPrice"),
                    "sell_price": meta.get("regularMarketPrice"),
                    "high_price": meta.get("regularMarketDayHigh"),
                    "low_price": meta.get("regularMarketDayLow"),
                    "volume": meta.get("regularMarketVolume"),
                    "timestamp": meta.get("regularMarketTime"),
                    "source": "yahoo"
                }
        except Exception as e:
            print(f"[Yahoo Finance] Error getting quote for {symbol}: {e}")
            return None

    def get_historical(
        self,
        symbol: str,
        start_date: str = None,
        end_date: str = None,
        interval: str = "1d",
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get historical price data.

        Args:
            symbol: Stock symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            interval: Data interval (1d, 1wk, 1mo)

        Returns:
            List of price records
        """
        url = f"{self.BASE_URL}/{symbol}"

        params = {"interval": interval}

        if start_date:
            params["period1"] = self._date_to_timestamp(start_date)
        if end_date:
            params["period2"] = self._date_to_timestamp(end_date)

        try:
            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                response = client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                result = data.get("chart", {}).get("result", [])
                if not result:
                    return []

                timestamps = result[0].get("timestamp", [])
                quotes = result[0].get("indicators", {}).get("quote", [{}])[0]

                bars = []
                for i, ts in enumerate(timestamps):
                    bars.append({
                        "symbol": symbol,
                        "timestamp": datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S"),
                        "buy_price": quotes.get("open", [None])[i],
                        "sell_price": quotes.get("close", [None])[i],
                        "high_price": quotes.get("high", [None])[i],
                        "low_price": quotes.get("low", [None])[i],
                        "volume": quotes.get("volume", [None])[i],
                        "source": "yahoo"
                    })

                return bars
        except Exception as e:
            print(f"[Yahoo Finance] Error getting historical for {symbol}: {e}")
            return []

    def search_symbol(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for symbols.

        Args:
            query: Search query

        Returns:
            List of matching symbols
        """
        url = f"{self.BASE_URL}/autocomplete"

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(url, params={"q": query})
                response.raise_for_status()
                data = response.json()

                results = []
                for item in data.get("quotes", []):
                    results.append({
                        "symbol": item.get("symbol"),
                        "name": item.get("shortname", ""),
                        "exchange": item.get("exchange"),
                        "type": item.get("quoteType")
                    })

                return results
        except Exception as e:
            print(f"[Yahoo Finance] Error searching for {query}: {e}")
            return []

    def _date_to_timestamp(self, date_str: str) -> int:
        """Convert date string to timestamp."""
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return int(dt.timestamp())


# =============================================================================
# Alpaca API
# =============================================================================

class AlpacaAPI:
    """
    Alpaca Trade API for US stocks.

    Features:
    - Real-time data (paper or live)
    - Trading support (create orders)
    - Free tier available

    Documentation: https://alpaca.markets/docs/

    Environment Variables:
    - ALPACA_API_KEY: Your Alpaca API key
    - ALPACA_API_SECRET: Your Alpaca API secret
    - ALPACA_BASE_URL:
        - https://paper-api.alpaca.markets (paper trading)
        - https://api.alpaca.markets (live trading)
    """

    def __init__(self, is_paper: bool = True):
        self.api_key = os.getenv("ALPACA_API_KEY")
        self.api_secret = os.getenv("ALPACA_API_SECRET")
        self.base_url = os.getenv(
            "ALPACA_BASE_URL",
            "https://paper-api.alpaca.markets" if is_paper else "https://api.alpaca.markets"
        )
        self.is_paper = is_paper

        if not self.api_key or not self.api_secret:
            raise ValueError(
                "[Alpaca] API credentials not found. "
                "Set ALPACA_API_KEY and ALPACA_API_SECRET environment variables."
            )

        self.headers = {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.api_secret,
            "Content-Type": "application/json"
        }

    def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get real-time quote for a symbol."""
        url = f"{self.base_url}/v2/stocks/{symbol}/quotes/latest"

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(url, headers=self.headers)
                response.raise_for_status()
                data = response.json()

                quote = data.get("quote", {})

                return {
                    "symbol": symbol,
                    "buy_price": quote.get("ask_price"),
                    "sell_price": quote.get("bid_price"),
                    "high_price": None,
                    "low_price": None,
                    "volume": None,
                    "ask_size": quote.get("ask_size"),
                    "bid_size": quote.get("bid_size"),
                    "source": "alpaca"
                }
        except Exception as e:
            print(f"[Alpaca] Error getting quote for {symbol}: {e}")
            return None

    def get_bars(
        self,
        symbol: str,
        start: str = None,
        end: str = None,
        timeframe: str = "1Day",
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get historical bars for a symbol."""
        url = f"{self.base_url}/v2/stocks/{symbol}/bars"

        params = {
            "timeframe": timeframe,
            "limit": limit
        }

        if start:
            params["start"] = start
        if end:
            params["end"] = end

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(url, headers=self.headers, params=params)
                response.raise_for_status()
                data = response.json()

                bars = []
                for bar in data.get("bars", []):
                    bars.append({
                        "symbol": symbol,
                        "timestamp": bar.get("t"),
                        "buy_price": bar.get("o"),  # open
                        "sell_price": bar.get("c"),  # close
                        "high_price": bar.get("h"),
                        "low_price": bar.get("l"),
                        "volume": bar.get("v"),
                        "source": "alpaca"
                    })

                return bars
        except Exception as e:
            print(f"[Alpaca] Error getting bars for {symbol}: {e}")
            return []

    def get_account(self) -> Optional[Dict[str, Any]]:
        """Get account information."""
        url = f"{self.base_url}/v2/account"

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(url, headers=self.headers)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            print(f"[Alpaca] Error getting account: {e}")
            return None

    def create_order(
        self,
        symbol: str,
        qty: int,
        side: str,  # buy or sell
        order_type: str = "market",
        time_in_force: str = "day"
    ) -> Optional[Dict[str, Any]]:
        """Create a trading order."""
        url = f"{self.base_url}/v2/orders"

        order_data = {
            "symbol": symbol,
            "qty": str(qty),
            "side": side,
            "type": order_type,
            "time_in_force": time_in_force
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(url, headers=self.headers, json=order_data)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            print(f"[Alpaca] Error creating order: {e}")
            return None

    def get_positions(self) -> List[Dict[str, Any]]:
        """Get all positions."""
        url = f"{self.base_url}/v2/positions"

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(url, headers=self.headers)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            print(f"[Alpaca] Error getting positions: {e}")
            return []


# =============================================================================
# Tushare Pro API
# =============================================================================

class TushareAPI:
    """
    Tushare Pro API for China A-shares.

    Features:
    - Comprehensive A-share data
    - High quality and reliable
    - Requires token (paid service)

    Documentation: https://tushare.pro/document/1

    Environment Variables:
    - TUSHARE_TOKEN: Your Tushare Pro token
    """

    BASE_URL = "https://api.tushare.pro"

    def __init__(self):
        self.token = os.getenv("TUSHARE_TOKEN")
        self.is_available = False

        if not self.token:
            print("[Tushare] Token not found. Set TUSHARE_TOKEN to enable.")
            return

        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        self.is_available = True

    def _call(self, api_name: str, params: Dict = None) -> Dict:
        """Make API call to Tushare."""
        if not self.is_available:
            print("[Tushare] API not available. Set TUSHARE_TOKEN environment variable.")
            return {}

        payload = {
            "api_name": api_name,
            "token": self.token,
            "params": params or {}
        }

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(self.BASE_URL, json=payload)
                response.raise_for_status()
                data = response.json()

                if data.get("code") != 0:
                    print(f"[Tushare] API error: {data.get('msg')}")
                    return {}

                return data.get("response", {})
        except Exception as e:
            print(f"[Tushare] Error calling {api_name}: {e}")
            return {}

    def get_daily(
        self,
        ts_code: str,
        start_date: str = None,
        end_date: str = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get daily bar data for a stock.

        Args:
            ts_code: Stock code (e.g., "000001.SZ", "600000.SH")
            start_date: Start date (YYYYMMDD)
            end_date: End date (YYYYMMDD)
            limit: Maximum number of records

        Returns:
            List of daily bars
        """
        if not self.is_available:
            return []

        params = {"ts_code": ts_code, "limit": limit}

        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        data = self._call("daily", params)

        bars = []
        for row in data:
            bars.append({
                "symbol": ts_code.split(".")[0],  # Extract code without exchange
                "ts_code": ts_code,
                "timestamp": row.get("trade_date"),
                "buy_price": float(row.get("open", 0)),
                "sell_price": float(row.get("close", 0)),
                "high_price": float(row.get("high", 0)),
                "low_price": float(row.get("low", 0)),
                "volume": float(row.get("vol", 0)),
                "amount": float(row.get("amount", 0)),
                "source": "tushare"
            })

        return bars

    def get_quote(self, ts_code: str) -> Optional[Dict[str, Any]]:
        """Get real-time quote for a stock."""
        if not self.is_available:
            return None

        params = {"ts_code": ts_code}
        data = self._call("quotation", params)

        if not data:
            return None

        row = data[0] if data else {}

        return {
            "symbol": ts_code.split(".")[0],
            "ts_code": ts_code,
            "buy_price": float(row.get("bid_p1", 0)),
            "sell_price": float(row.get("ask_p1", 0)),
            "high_price": float(row.get("high", 0)),
            "low_price": float(row.get("low", 0)),
            "volume": float(row.get("vol", 0)),
            "source": "tushare"
        }

    def get_stock_basic(
        self,
        exchange: str = None,
        list_status: str = "L",
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get stock basic information.

        Args:
            exchange: Exchange (SSE, SZSE) or None for all
            list_status: L (listed), D (delisted), P (pre-IPO)
            limit: Maximum number of records

        Returns:
            List of stock information
        """
        if not self.is_available:
            return []

        params = {"list_status": list_status, "limit": limit}
        if exchange:
            params["exchange"] = exchange

        data = self._call("stock_basic", params)

        stocks = []
        for row in data:
            stocks.append({
                "ts_code": row.get("ts_code"),
                "symbol": row.get("symbol"),
                "name": row.get("name"),
                "exchange": row.get("exchange"),
                "list_date": row.get("list_date")
            })

        return stocks

    def get_trading_dates(
        self,
        start_date: str = None,
        end_date: str = None
    ) -> List[str]:
        """
        Get trading dates.

        Args:
            start_date: Start date (YYYYMMDD)
            end_date: End date (YYYYMMDD)

        Returns:
            List of trading dates
        """
        if not self.is_available:
            return []

        params = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        data = self._call("trade_cal", params)

        dates = []
        for row in data:
            if row.get("is_trading") == 1:
                dates.append(row.get("cal_date"))

        return dates


# =============================================================================
# Unified Market Data Adapter
# =============================================================================

class MarketDataAdapter:
    """
    Unified interface for market data access.

    Automatically selects the appropriate data source based on configuration.

    Usage:
        adapter = get_market_adapter(config)
        price = adapter.get_price("AAPL", "2025-11-10", "us")
    """

    def __init__(self, config: MarketConfig):
        self.config = config
        self._init_apis()

    def _init_apis(self):
        """Initialize API clients based on configuration."""
        self.yahoo = None
        self.alpaca = None
        self.tushare = None

        # Initialize Yahoo Finance
        if self.config.price_source == "yahoo":
            self.yahoo = YahooFinanceAPI()

        # Initialize Alpaca (only if using real-time data)
        if self.config.need_price_api():
            if self.config.price_source == "alpaca":
                try:
                    self.alpaca = AlpacaAPI(is_paper=(self.config.trading_mode == "paper"))
                except ValueError as e:
                    print(f"[Market API] {e}")
                    print("[Market API] Falling back to local data.")

        # Initialize Tushare for A-shares
        if self.config.price_source == "tushare":
            try:
                self.tushare = TushareAPI()
                if not self.tushare.is_available:
                    print("[Market API] Tushare not available. Falling back to local data.")
                    self.tushare = None
            except Exception as e:
                print(f"[Market API] Tushare initialization failed: {e}")
                print("[Market API] Falling back to local data.")
                self.tushare = None

    def get_price(
        self,
        symbol: str,
        timestamp: str,
        market: str = "us"
    ) -> Optional[Dict[str, Any]]:
        """
        Get price for a symbol at a specific time.

        Args:
            symbol: Stock symbol (e.g., "AAPL", "000001")
            timestamp: Date/time string (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
            market: Market type (us, astock)

        Returns:
            Price dictionary or None if not found
        """
        # Use API based on market
        if market == "us":
            return self._get_us_price(symbol, timestamp)
        elif market == "astock":
            return self._get_astock_price(symbol, timestamp)

        return None

    def _get_us_price(self, symbol: str, timestamp: str) -> Optional[Dict[str, Any]]:
        """Get US stock price."""
        # Try real-time API first
        if self.config.need_price_api():
            if self.alpaca:
                return self.alpaca.get_quote(symbol)
            elif self.yahoo:
                return self.yahoo.get_quote(symbol)

        # Fall back to local database
        return self._get_local_price(symbol, timestamp, "us")

    def _get_astock_price(self, symbol: str, timestamp: str) -> Optional[Dict[str, Any]]:
        """Get A-share price."""
        # Try Tushare first
        if self.tushare:
            return self.tushare.get_quote(symbol)

        # Fall back to local database
        return self._get_local_price(symbol, timestamp, "astock")

    def get_prices_range(
        self,
        symbol: str,
        start_time: str,
        end_time: str,
        market: str = "us"
    ) -> List[Dict[str, Any]]:
        """
        Get price range for a symbol.

        Args:
            symbol: Stock symbol
            start_time: Start time (YYYY-MM-DD HH:MM:SS)
            end_time: End time (YYYY-MM-DD HH:MM:SS)
            market: Market type

        Returns:
            List of price records
        """
        if market == "us":
            return self._get_us_prices_range(symbol, start_time, end_time)
        elif market == "astock":
            return self._get_astock_prices_range(symbol, start_time, end_time)

        return []

    def _get_us_prices_range(
        self,
        symbol: str,
        start_time: str,
        end_time: str
    ) -> List[Dict[str, Any]]:
        """Get US stock price range."""
        # Try API first
        if self.config.need_price_api():
            if self.alpaca:
                start = start_time.split()[0] if " " in start_time else start_time
                end = end_time.split()[0] if " " in end_time else end_time
                return self.alpaca.get_bars(symbol, start, end)
            elif self.yahoo:
                start_date = start_time.split()[0] if " " in start_time else start_time
                end_date = end_time.split()[0] if " " in end_time else end_time
                return self.yahoo.get_historical(symbol, start_date, end_date)

        # Fall back to local database
        return self._get_local_prices_range(symbol, start_time, end_time, "us")

    def _get_astock_prices_range(
        self,
        symbol: str,
        start_time: str,
        end_time: str
    ) -> List[Dict[str, Any]]:
        """Get A-share price range."""
        if self.tushare:
            start_date = start_time.split()[0].replace("-", "")
            end_date = end_time.split()[0].replace("-", "")
            ts_code = self._symbol_to_ts_code(symbol)
            return self.tushare.get_daily(ts_code, start_date, end_date)

        # Fall back to local database
        return self._get_local_prices_range(symbol, start_time, end_time, "astock")

    def get_latest_price(self, symbol: str, market: str = "us") -> Optional[Dict[str, Any]]:
        """Get latest price for a symbol."""
        return self.get_price(symbol, datetime.now().strftime("%Y-%m-%d"), market)

    def search_symbol(self, query: str, market: str = "us") -> List[Dict[str, Any]]:
        """Search for symbols."""
        if market == "us" and self.yahoo:
            return self.yahoo.search_symbol(query)

        return []

    def get_trading_dates(
        self,
        market: str = "us",
        start_date: str = None,
        end_date: str = None
    ) -> List[str]:
        """Get trading dates."""
        if market == "astock" and self.tushare:
            start = start_date.replace("-", "") if start_date else None
            end = end_date.replace("-", "") if end_date else None
            return self.tushare.get_trading_dates(start, end)

        return self._get_local_trading_dates(market)

    def _symbol_to_ts_code(self, symbol: str) -> str:
        """Convert symbol to Tushare ts_code."""
        # A-shares need exchange suffix
        symbol = symbol.upper()

        # Shenzhen stocks usually start with 0 or 3
        if symbol.startswith(("0", "3")):
            return f"{symbol}.SZ"
        # Shanghai stocks start with 6
        elif symbol.startswith("6"):
            return f"{symbol}.SH"

        return symbol

    def _get_local_price(
        self,
        symbol: str,
        timestamp: str,
        market: str
    ) -> Optional[Dict[str, Any]]:
        """Get price from local database."""
        from tools.trading_db import get_price, init_db, get_db_path

        db_path = get_db_path("prices")
        init_db(db_path)

        return get_price(symbol, timestamp, market, db_path)

    def _get_local_prices_range(
        self,
        symbol: str,
        start_time: str,
        end_time: str,
        market: str
    ) -> List[Dict[str, Any]]:
        """Get price range from local database."""
        from tools.trading_db import get_prices_range, init_db, get_db_path

        db_path = get_db_path("prices")
        init_db(db_path)

        return get_prices_range(symbol, start_time, end_time, market, db_path)

    def _get_local_trading_dates(self, market: str) -> List[str]:
        """Get trading dates from local database."""
        from tools.trading_db import get_all_timestamps, init_db, get_db_path

        db_path = get_db_path("prices")
        init_db(db_path)

        timestamps = get_all_timestamps(market, db_path)

        # Extract unique dates
        unique_dates = set()
        for ts in timestamps:
            date = ts.split()[0]
            unique_dates.add(date)

        return sorted(list(unique_dates))


# =============================================================================
# Factory Function
# =============================================================================

def get_market_adapter(config: Dict[str, Any]) -> MarketDataAdapter:
    """
    Create a MarketDataAdapter from config dictionary.

    Args:
        config: Configuration dictionary with data_source and trading_mode

    Returns:
        MarketDataAdapter instance
    """
    market_config = MarketConfig.from_config(config)
    return MarketDataAdapter(market_config)


# =============================================================================
# Direct API Access
# =============================================================================

def get_yahoo_api() -> YahooFinanceAPI:
    """Get Yahoo Finance API instance."""
    return YahooFinanceAPI()


def get_alpaca_api(is_paper: bool = True) -> AlpacaAPI:
    """Get Alpaca API instance."""
    return AlpacaAPI(is_paper)


def get_tushare_api() -> TushareAPI:
    """Get Tushare API instance."""
    return TushareAPI()
