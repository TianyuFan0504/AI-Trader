---
name: price-skill
description: Get stock prices and market data. Use for retrieving historical prices, latest quotes, and searching for stock symbols. Supports US stocks, China A-shares, and cryptocurrency.
---

# Price Skill

## Overview
This skill provides access to stock prices and market data from multiple sources:
- **local**: Historical data from local database
- **yahoo**: Yahoo Finance (free, delayed ~15min)
- **alpaca**: Alpaca API (real-time, requires API key)

## Available Tools
- `get_price(symbol, date)` - Get OHLCV price for a specific date
- `get_prices_range(symbol, start_date, end_date)` - Get price history over a range
- `get_latest_price(symbol)` - Get current market price
- `search_symbol(query)` - Search for stock symbols

## Usage Examples

### Get historical price
```python
price = get_price(symbol="AAPL", date="2025-11-10")
```

### Get price range for analysis
```python
prices = get_prices_range(
    symbol="NVDA",
    start_date="2025-11-01",
    end_date="2025-11-10"
)
```

### Get latest quote
```python
quote = get_latest_price(symbol="TSLA")
```

## Symbol Formats
- **US stocks**: `AAPL`, `MSFT`, `GOOGL`
- **China A-shares**: `600519.SH`, `000001.SZ`
- **Cryptocurrency**: `BTC-USDT`, `ETH-USDT`

## Data Sources
Configure via environment variables:
- `DATA_SOURCE_PRICE` - `local`, `yahoo`, or `alpaca`
- `ALPACA_API_KEY` / `ALPACA_API_SECRET` - For Alpaca access
