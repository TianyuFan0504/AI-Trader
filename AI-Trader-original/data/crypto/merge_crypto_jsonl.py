#!/usr/bin/env python3
"""
Merge crypto daily price JSON files to SQLite database.

This script:
1. Reads individual crypto daily price JSON files from coin/ directory
2. Saves them to the prices database
3. Automatically adds -USDT suffix to crypto symbols

Usage:
    python data/crypto/merge_crypto_jsonl.py

The individual crypto files should be located in the 'coin/' subdirectory
and follow the naming pattern: daily_prices_{SYMBOL}.json
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


# Major cryptocurrencies against USDT
crypto_symbols_usdt = [
    "BTC",   # Bitcoin/USDT
    "ETH",   # Ethereum/USDT
    "XRP",   # Ripple/USDT
    "SOL",   # Solana/USDT
    "ADA",   # Cardano/USDT
    "SUI",   # Sui/USDT
    "LINK",  # Chainlink/USDT
    "AVAX",  # Avalanche/USDT
    "LTC",   # Litecoin/USDT
    "DOT",   # Polkadot/USDT
]


def merge_to_db():
    """Merge crypto JSON files to database."""
    # Initialize database
    db_path = get_db_path("prices")
    init_db(db_path)
    print(f"Database: {db_path}")

    current_dir = Path(__file__).parent
    coin_dir = current_dir / "coin"

    if not coin_dir.exists():
        print(f"Error: coin/ directory not found: {coin_dir}")
        return

    pattern = coin_dir / "daily_prices_*.json"
    files = sorted(glob.glob(str(pattern)))

    if not files:
        print("No crypto daily price files found!")
        return

    print(f"Found {len(files)} crypto files to process")

    count = 0
    processed = 0
    skipped = 0

    for fp in files:
        basename = Path(fp).name

        # Only process files that contain our crypto symbols
        if not any(symbol in basename for symbol in crypto_symbols_usdt):
            skipped += 1
            print(f"  Skipping: {basename}")
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

                # Fix crypto symbol by adding -USDT suffix
                if symbol and not symbol.endswith("-USDT"):
                    new_symbol = f"{symbol}-USDT"
                    symbol = new_symbol

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
                            market="crypto",
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

                processed += 1
                print(f"  Processed: {basename}")

        except Exception as e:
            print(f"  Error processing {basename}: {e}")
            continue

    print(f"\nDone: Added {count} price records to database")
    print(f"Statistics: {processed} files processed, {skipped} files skipped")


if __name__ == "__main__":
    print("=" * 60)
    print("Crypto Data Merger to Database")
    print("=" * 60)
    merge_to_db()
    print("=" * 60)
