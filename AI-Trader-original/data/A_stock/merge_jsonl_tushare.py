"""
Convert A-share CSV data to SQLite database.

This script reads A-share daily price CSV files and saves them to the prices database.

Usage:
    python data/A_stock/merge_jsonl_tushare.py
"""

import json
import os
import sys
from pathlib import Path

import pandas as pd

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from tools.trading_db import init_db, add_price, get_db_path


def convert_a_stock_to_db(
    csv_path: str = "A_stock_data/daily_prices_sse_50.csv",
    stock_name_csv: str = "A_stock_data/sse_50_weight.csv",
) -> None:
    """Convert A-share CSV data to database.

    Args:
        csv_path: Path to the A-share daily price CSV file
        stock_name_csv: Path to SSE 50 weight CSV containing stock names
    """
    csv_path = Path(csv_path)
    stock_name_csv = Path(stock_name_csv)

    if not csv_path.exists():
        print(f"Error: CSV file not found: {csv_path}")
        return

    # Initialize database
    db_path = get_db_path("prices")
    init_db(db_path)
    print(f"Database: {db_path}")

    print(f"Reading CSV file: {csv_path}")

    # Read CSV data
    df = pd.read_csv(csv_path)

    # Read stock name mapping
    stock_name_map = {}
    if stock_name_csv.exists():
        print(f"Reading stock names from: {stock_name_csv}")
        name_df = pd.read_csv(stock_name_csv)
        # Create mapping from con_code (ts_code) to stock_name
        stock_name_map = dict(zip(name_df["con_code"], name_df["stock_name"]))
        print(f"Loaded {len(stock_name_map)} stock names")
    else:
        print(f"Warning: Stock name file not found: {stock_name_csv}")

    print(f"Total records: {len(df)}")
    print(f"Columns: {df.columns.tolist()}")

    # Group by stock symbol
    grouped = df.groupby("ts_code")

    print(f"Processing {len(grouped)} stocks...")

    count = 0
    for ts_code, group_df in grouped:
        # Sort by date ascending
        group_df = group_df.sort_values("trade_date", ascending=True)

        for idx, row in group_df.iterrows():
            date_str = str(row["trade_date"])
            date_formatted = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"

            # Parse prices
            buy_price = None
            sell_price = None
            high_price = None
            low_price = None
            volume = None

            try:
                if pd.notna(row.get("open")):
                    buy_price = float(row["open"])
            except (ValueError, TypeError):
                pass

            try:
                if pd.notna(row.get("close")):
                    sell_price = float(row["close"])
            except (ValueError, TypeError):
                pass

            try:
                if pd.notna(row.get("high")):
                    high_price = float(row["high"])
            except (ValueError, TypeError):
                pass

            try:
                if pd.notna(row.get("low")):
                    low_price = float(row["low"])
            except (ValueError, TypeError):
                pass

            try:
                if pd.notna(row.get("vol")):
                    volume = float(row["vol"] * 100)  # Convert 手 to shares
            except (ValueError, TypeError):
                pass

            # Add to database
            try:
                add_price(
                    symbol=ts_code,
                    timestamp=date_formatted,
                    market="astock",
                    buy_price=buy_price,
                    sell_price=sell_price,
                    high_price=high_price,
                    low_price=low_price,
                    volume=volume
                )
                count += 1
            except Exception as e:
                print(f"  Error adding {ts_code} at {date_formatted}: {e}")

    print(f"Done: Added {count} price records to database")


if __name__ == "__main__":
    print("=" * 60)
    print("A-Share Data Converter to Database")
    print("=" * 60)

    current_dir = Path(__file__).parent
    csv_path = current_dir / "A_stock_data" / "daily_prices_sse_50.csv"
    stock_name_csv = current_dir / "A_stock_data" / "sse_50_weight.csv"

    convert_a_stock_to_db(str(csv_path), str(stock_name_csv))

    print("=" * 60)
