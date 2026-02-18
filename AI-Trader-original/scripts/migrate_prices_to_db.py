"""
Migrate price data from JSONL files to SQLite database.

This script migrates:
- data/merged.jsonl -> prices database (market: us)
- data/A_stock/merged.jsonl -> prices database (market: astock)
- data/A_stock/merged_hourly.jsonl -> prices database (market: astock_hourly)
- data/crypto/crypto_merged.jsonl -> prices database (market: crypto)

Usage:
    python scripts/migrate_prices_to_db.py
"""

import json
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from tools.trading_db import (
    init_db, add_price, get_db_path
)


def migrate_price_file(jsonl_path: str, market: str):
    """
    Migrate a single price JSONL file to database.

    Args:
        jsonl_path: Path to the JSONL file
        market: Market identifier (us, astock, crypto)
    """
    if not os.path.exists(jsonl_path):
        print(f"  Skipping: {jsonl_path} does not exist")
        return 0

    print(f"  Migrating: {jsonl_path}")

    count = 0
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                doc = json.loads(line)

                # Extract symbol from Meta Data
                symbol = doc.get("Meta Data", {}).get("2. Symbol")
                if not symbol:
                    continue

                # Find the Time Series key
                time_series_key = None
                for key in doc.keys():
                    if key.startswith("Time Series"):
                        time_series_key = key
                        break

                if not time_series_key:
                    continue

                time_series = doc.get(time_series_key, {})
                for timestamp, data in time_series.items():
                    # Parse prices
                    buy_price = None
                    sell_price = None
                    high_price = None
                    low_price = None
                    volume = None

                    # Handle different field naming conventions
                    for k, v in data.items():
                        k_lower = k.lower()
                        if "buy" in k_lower:
                            try:
                                buy_price = float(v)
                            except (ValueError, TypeError):
                                pass
                        elif "sell" in k_lower:
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

                    # Store in database
                    try:
                        add_price(
                            symbol=symbol,
                            timestamp=timestamp,
                            market=market,
                            buy_price=buy_price,
                            sell_price=sell_price,
                            high_price=high_price,
                            low_price=low_price,
                            volume=volume,
                            raw_data=data
                        )
                        count += 1
                    except Exception as e:
                        print(f"    Error adding price for {symbol} at {timestamp}: {e}")

            except json.JSONDecodeError:
                continue

    print(f"  Done: Migrated {count} price records from {jsonl_path}")
    return count


def migrate_all_prices():
    """Migrate all price data files to database."""
    print("=" * 60)
    print("Migrating AI-Trader price data from JSONL to SQLite")
    print("=" * 60)

    # Initialize prices database
    print("\nInitializing prices database...")
    db_path = get_db_path("prices")
    init_db(db_path)
    print(f"  Database: {db_path}")
    print("Done")

    total_count = 0

    # Migrate US stock data
    print("\n" + "-" * 60)
    print("Migrating US Stock price data...")
    jsonl_path = project_root / "data" / "merged.jsonl"
    total_count += migrate_price_file(str(jsonl_path), "us")

    # Migrate A-share daily data
    print("\n" + "-" * 60)
    print("Migrating A-Share daily price data...")
    jsonl_path = project_root / "data" / "A_stock" / "merged.jsonl"
    total_count += migrate_price_file(str(jsonl_path), "astock")

    # Migrate A-share hourly data
    print("\n" + "-" * 60)
    print("Migrating A-Share hourly price data...")
    jsonl_path = project_root / "data" / "A_stock" / "merged_hourly.jsonl"
    total_count += migrate_price_file(str(jsonl_path), "astock_hourly")

    # Migrate crypto data
    print("\n" + "-" * 60)
    print("Migrating Cryptocurrency price data...")
    jsonl_path = project_root / "data" / "crypto" / "crypto_merged.jsonl"
    total_count += migrate_price_file(str(jsonl_path), "crypto")

    print("\n" + "=" * 60)
    print(f"Migration completed! Total records: {total_count}")
    print("=" * 60)


if __name__ == "__main__":
    migrate_all_prices()
