"""
News tools - Get market news using Alpha Vantage API.
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from tools import tool

# Ensure project root is in path
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from tools.general_tools import get_config_value


@tool(description="Get market news articles")
def get_market_news(
    query: str = "",
    tickers: Optional[str] = None,
    topics: Optional[str] = None
) -> str:
    """Get market news from Alpha Vantage.

    Args:
        query: Search query description
        tickers: Stock symbols to filter (e.g., "AAPL")
        topics: News topics (e.g., "technology")

    Returns:
        Formatted news articles
    """
    api_key = os.getenv("ALPHAADVANTAGE_API_KEY")
    if not api_key:
        return "Alpha Vantage API key not set. Set ALPHAADVANTAGE_API_KEY."

    base_url = "https://www.alphavantage.co/query"
    today_date = get_config_value("TODAY_DATE")

    # Calculate time range
    time_to = None
    time_from = None
    if today_date:
        try:
            if " " in today_date:
                dt = datetime.strptime(today_date, "%Y-%m-%d %H:%M:%S")
            else:
                dt = datetime.strptime(today_date, "%Y-%m-%d")
            time_to = dt.strftime("%Y%m%dT%H%M")
            time_from = (dt - timedelta(days=30)).strftime("%Y%m%dT%H%M")
        except Exception:
            pass

    params = {
        "function": "NEWS_SENTIMENT",
        "apikey": api_key,
        "sort": "LATEST",
        "limit": 20,
    }

    if tickers:
        params["tickers"] = tickers
    if topics:
        params["topics"] = topics
    if time_from:
        params["time_from"] = time_from
    if time_to:
        params["time_to"] = time_to

    try:
        resp = requests.get(base_url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        if "Error Message" in data:
            return f"API Error: {data['Error Message']}"
        if "Note" in data:
            return f"API Limit: {data['Note']}"

        feed = data.get("feed", [])
        if not feed:
            return "No news articles found."

        results = []
        for article in feed[:10]:
            title = article.get("title", "N/A")
            summary = article.get("summary", "")[:500]
            source = article.get("source", "N/A")
            sentiment = article.get("overall_sentiment_label", "N/A")
            url = article.get("url", "")

            results.append(
                f"Title: {title}\n"
                f"Summary: {summary}...\n"
                f"Source: {source} | Sentiment: {sentiment}\n"
                f"URL: {url}\n"
                f"{'='*50}"
            )

        return "\n".join(results)

    except Exception as e:
        return f"Failed to fetch news: {str(e)}"
