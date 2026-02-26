---
name: news-skill
description: Get market news and sentiment analysis. Use for retrieving latest financial news, company announcements, and market sentiment. Powered by Alpha Vantage.
---

# News Skill

## Overview
This skill provides access to market news and sentiment analysis from Alpha Vantage API.

## Available Tools
- `get_market_news(query, tickers, topics)` - Get news articles

## Usage Examples

### Get news for a specific stock
```python
news = get_market_news(
    query="Apple stock analysis",
    tickers="AAPL",
    topics="technology"
)
```

### Get market-wide news
```python
news = get_market_news(
    query="US stock market",
    topics="financial_markets"
)
```

## Parameters
- `query` - Description of news interest (for logging)
- `tickers` - Stock symbols to filter (e.g., `"AAPL,MSFT"`)
- `topics` - News topics (comma-separated)

## Supported Topics
- `blockchain` - Blockchain news
- `earnings` - Earnings reports
- `financial_markets` - Market news
- `technology` - Tech sector news
- `economy_macro` - Macro economy
- `energy_transportation` - Energy/transport
- `life_sciences` - Healthcare/pharma
- `mergers_and_acquisitions` - M&A news

## Return Format
```
Title: Article headline
Summary: Brief description...
Source: News source | Sentiment: Bullish/Bearish/Neutral
URL: Link to full article
==================================================
```

## Environment
- `ALPHAADVANTAGE_API_KEY` - API key required
- `TODAY_DATE` - For date filtering (returns last 30 days)
