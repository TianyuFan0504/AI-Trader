"""
Merge A-share Alpha Vantage JSON files to SQLite database.

This script reads individual A-share daily price JSON files and saves them to the prices database.

Usage:
    python data/A_stock/merge_jsonl_alphavantage.py
"""

import glob
import json
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from tools.trading_db import init_db, add_price, get_db_path


sse_50_codes = [
    "600519.SHH", "601318.SHH", "600036.SHH", "601899.SHH", "600900.SHH",
    "601166.SHH", "600276.SHH", "600030.SHH", "603259.SHH", "688981.SHH",
    "688256.SHH", "601398.SHH", "688041.SHH", "601211.SHH", "601288.SHH",
    "601328.SHH", "688008.SHH", "600887.SHH", "600150.SHH", "601816.SHH",
    "601127.SHH", "600031.SHH", "688012.SHH", "603501.SHH", "601088.SHH",
    "600309.SHH", "601601.SHH", "601668.SHH", "603993.SHH", "601012.SHH",
    "601728.SHH", "600690.SHH", "600809.SHH", "600941.SHH", "600406.SHH",
    "601857.SHH", "601766.SHH", "601919.SHH", "600050.SHH", "600760.SHH",
    "601225.SHH", "600028.SHH", "601988.SHH", "688111.SHH", "601985.SHH",
    "601888.SHH", "601628.SHH", "601600.SHH", "601658.SHH", "600048.SHH"
]


def load_stock_name_mapping():
    """Load stock name mapping from CSV."""
    current_dir = Path(__file__).parent
    csv_path = current_dir / "A_stock_data" / "sse_50_weight.csv"

    name_mapping = {}
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            import csv
            reader = csv.DictReader(f)
            for row in reader:
                con_code = row.get('con_code', '')
                stock_name = row.get('stock_name', '')
                if con_code and stock_name:
                    name_mapping[con_code] = stock_name
    except FileNotFoundError:
        print(f"Warning: {csv_path} not found")

    return name_mapping


def merge_to_db():
    """Merge A-share JSON files to database."""
    # Initialize database
    db_path = get_db_path("prices")
    init_db(db_path)
    print(f"Database: {db_path}")

    current_dir = Path(__file__).parent
    pattern = current_dir / "A_stock_data" / "daily_price*.json"
    files = sorted(current_dir.glob("daily_price*.json"))

    if not files:
        print("No daily_price*.json files found!")
        return

    print(f"Found {len(files)} files to process")

    # Load stock name mapping
    stock_name_map = load_stock_name_mapping()

    processed_count = 0
    skipped_count = 0
    count = 0

    for fp in files:
        basename = fp.name
        # Only process files containing SSE 50 symbols
        if not any(symbol in basename for symbol in sse_50_codes):
            skipped_count += 1
            continue

        with open(fp, "r", encoding="utf-8") as f:
            data = json.load(f)

        try:
            # Find Time Series key
            series = None
            for key, value in data.items():
                if key.startswith("Time Series"):
                    series = value
                    break

            if isinstance(series, dict) and series:
                # Get symbol from Meta Data
                meta = data.get("Meta Data", {})
                symbol = meta.get("2. Symbol", basename)
                # Replace .SHH with .SH
                symbol = symbol.replace(".SHH", ".SH")

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
                            market="astock",
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

                processed_count += 1

        except Exception as e:
            print(f"  Error processing {basename}: {e}")
            continue

    print(f"Done: Added {count} price records to database")
    print(f"Statistics: {processed_count} files processed, {skipped_count} files skipped")


if __name__ == "__main__":
    print("=" * 60)
    print("A-Share (Alpha Vantage) Data Merger to Database")
    print("=" * 60)
    merge_to_db()
    print("=" * 60)
