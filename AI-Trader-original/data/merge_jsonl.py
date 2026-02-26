"""
Merge US stock price data and save to SQLite database.

This script reads individual daily_price JSON files and merges them into the prices database.

Usage:
    python data/merge_jsonl.py
"""

import glob
import json
import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from tools.trading_db import init_db, add_price, get_db_path


all_nasdaq_100_symbols = [
    "NVDA", "MSFT", "AAPL", "GOOG", "GOOGL", "AMZN", "META", "AVGO", "TSLA", "NFLX",
    "PLTR", "COST", "ASML", "AMD", "CSCO", "AZN", "TMUS", "MU", "LIN", "PEP",
    "SHOP", "APP", "INTU", "AMAT", "LRCX", "PDD", "QCOM", "ARM", "INTC", "BKNG",
    "AMGN", "TXN", "ISRG", "GILD", "KLAC", "PANW", "ADBE", "HON", "CRWD", "CEG",
    "ADI", "ADP", "DASH", "CMCSA", "VRTX", "MELI", "SBUX", "CDNS", "ORLY", "SNPS",
    "MSTR", "MDLZ", "ABNB", "MRVL", "CTAS", "TRI", "MAR", "MNST", "CSX", "ADSK",
    "PYPL", "FTNT", "AEP", "WDAY", "REGN", "ROP", "NXPI", "DDOG", "AXON", "ROST",
    "IDXX", "EA", "PCAR", "FAST", "EXC", "TTWO", "XEL", "ZS", "PAYX", "WBD",
    "BKR", "CPRT", "CCEP", "FANG", "TEAM", "CHTR", "KDP", "MCHP", "GEHC", "VRSK",
    "CTSH", "CSGP", "KHC", "ODFL", "DXCM", "TTD", "ON", "BIIB", "LULU", "CDW", "GFS",
]


def merge_to_db():
    """Merge all daily_price JSON files to database."""
    # Initialize database
    db_path = get_db_path("prices")
    init_db(db_path)
    print(f"Database: {db_path}")

    current_dir = os.path.dirname(__file__)
    pattern = os.path.join(current_dir, "daily_price*.json")
    files = sorted(glob.glob(pattern))

    if not files:
        print("No daily_price*.json files found!")
        return

    print(f"Found {len(files)} files to process")

    count = 0
    for fp in files:
        basename = os.path.basename(fp)
        # Only process files containing NASDAQ 100 symbols
        if not any(symbol in basename for symbol in all_nasdaq_100_symbols):
            continue

        with open(fp, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Process and rename fields
        try:
            # Find Time Series key
            series = None
            for key, value in data.items():
                if key.startswith("Time Series"):
                    series = value
                    break

            if isinstance(series, dict) and series:
                # Get symbol from Meta Data
                symbol = data.get("Meta Data", {}).get("2. Symbol", basename)

                # Process each timestamp
                for timestamp, bar in series.items():
                    if not isinstance(bar, dict):
                        continue

                    # Parse prices
                    buy_price = None
                    sell_price = None
                    high_price = None
                    low_price = None
                    volume = None

                    for k, v in bar.items():
                        k_lower = k.lower()
                        if "buy" in k_lower or k == "1. open":
                            try:
                                buy_price = float(v)
                            except (ValueError, TypeError):
                                pass
                        elif "sell" in k_lower or k == "4. close":
                            try:
                                sell_price = float(v)
                            except (ValueError, TypeError):
                                pass
                        elif "high" in k_lower:
                            try:
                                high_price = float(v)
                            except (ValueError, TypeError):
                                pass
                        elif "low" in k_lower:
                            try:
                                low_price = float(v)
                            except (ValueError, TypeError):
                                pass
                        elif "volume" in k_lower:
                            try:
                                volume = float(v)
                            except (ValueError, TypeError):
                                pass

                    # Add to database
                    try:
                        add_price(
                            symbol=symbol,
                            timestamp=timestamp,
                            market="us",
                            buy_price=buy_price,
                            sell_price=sell_price,
                            high_price=high_price,
                            low_price=low_price,
                            volume=volume,
                            raw_data=bar
                        )
                        count += 1
                    except Exception as e:
                        print(f"  Error adding {symbol} at {timestamp}: {e}")

        except Exception as e:
            print(f"  Error processing {basename}: {e}")
            continue

    print(f"Done: Added {count} price records to database")


if __name__ == "__main__":
    merge_to_db()
