"""
News retrieval tools using Alpha Vantage API.
"""

import os
from datetime import datetime, timedelta

import requests

from tools.general_tools import get_config_value


def get_market_news(query: str = "", tickers: str = None, topics: str = None) -> str:
    """Get market news from Alpha Vantage."""
    api_key = os.getenv("ALPHAADVANTAGE_API_KEY")
    if not api_key:
        return "Alpha Vantage API key not set. Set ALPHAADVANTAGE_API_KEY."

    url = "https://www.alphavantage.co/query"
    today = get_config_value("TODAY_DATE")

    # Calculate time range
    time_to, time_from = None, None
    if today:
        try:
            dt = datetime.strptime(today, "%Y-%m-%d %H:%M:%S" if " " in today else "%Y-%m-%d")
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
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        if "Error Message" in data:
            return f"API Error: {data['Error Message']}"
        if "Note" in data:
            return f"API Limit: {data['Note']}"

        feed = data.get("feed", [])
        if not feed:
            return "No news articles found."

        lines = []
        for article in feed[:10]:
            lines.append(
                f"Title: {article.get('title', 'N/A')}\n"
                f"Summary: {article.get('summary', '')[:500]}...\n"
                f"Source: {article.get('source', 'N/A')} | "
                f"Sentiment: {article.get('overall_sentiment_label', 'N/A')}\n"
                f"URL: {article.get('url', '')}\n"
                "=" * 50
            )

        return "\n".join(lines)

    except Exception as e:
        return f"Failed to fetch news: {str(e)}"
