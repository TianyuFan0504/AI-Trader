"""
Migration script: Convert JSONL files to SQLite database.
Run this script once to migrate existing data.
"""

import json
import os
from pathlib import Path

from tools.trading_db import init_db, append_position, append_log, get_db_path


def migrate_position_file(jsonl_path: str, signature: str, market: str = "agent_data"):
    """Migrate a single position.jsonl file to database."""
    if not os.path.exists(jsonl_path):
        print(f"  Skipping: {jsonl_path} does not exist")
        return

    print(f"  Migrating: {jsonl_path}")

    with open(jsonl_path, "r") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                positions = record.get("positions", {})
                action = record.get("this_action", {})
                symbol = action.get("symbol", "")
                amount = action.get("amount", 0)
                action_type = action.get("action", "unknown")

                append_position(
                    signature=signature,
                    date=record.get("date", ""),
                    action_type=action_type,
                    symbol=symbol,
                    amount=amount,
                    positions=positions,
                    market=market
                )
            except json.JSONDecodeError:
                continue

    print(f"  Done: Migrated {jsonl_path}")


def migrate_log_file(log_path: str, signature: str, market: str = "agent_data"):
    """Migrate a single log.jsonl file to database."""
    if not os.path.exists(log_path):
        print(f"  Skipping: {log_path} does not exist")
        return

    print(f"  Migrating: {log_path}")

    # Extract date from log path (format: .../log/YYYY-MM-DD HH:MM:SS/log.jsonl)
    log_dir = os.path.dirname(log_path)
    date_str = os.path.basename(log_dir)

    with open(log_path, "r") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                new_messages = record.get("new_messages", [])
                if isinstance(new_messages, list):
                    for msg in new_messages:
                        role = msg.get("role", "")
                        content = msg.get("content", "")
                        append_log(
                            signature=signature,
                            log_date=date_str,
                            role=role,
                            content=content,
                            market=market
                        )
            except json.JSONDecodeError:
                continue

    print(f"  Done: Migrated {log_path}")


def migrate_agent_data(agent_data_dir: str, market: str = "agent_data"):
    """Migrate all data for a single agent."""
    if not os.path.exists(agent_data_dir):
        print(f"Skipping: {agent_data_dir} does not exist")
        return

    print(f"\nMigrating: {agent_data_dir}")

    # Get signature from directory name
    signature = os.path.basename(agent_data_dir)

    # Migrate position file
    position_file = os.path.join(agent_data_dir, "position", "position.jsonl")
    migrate_position_file(position_file, signature, market)

    # Migrate log files
    log_dir = os.path.join(agent_data_dir, "log")
    if os.path.exists(log_dir):
        for date_dir in os.listdir(log_dir):
            log_path = os.path.join(log_dir, date_dir, "log.jsonl")
            migrate_log_file(log_path, signature, market)


def main():
    """Main migration function."""
    project_root = Path(__file__).resolve().parent.parent
    data_dir = project_root / "data"

    print("=" * 60)
    print("Migrating AI-Trader data from JSONL to SQLite")
    print("=" * 60)

    # Initialize databases
    print("\nInitializing databases...")
    init_db(get_db_path("agent_data"))
    init_db(get_db_path("crypto"))
    init_db(get_db_path("astock"))
    print("Done")

    # Migrate US stock data
    print("\n" + "-" * 60)
    print("Migrating US Stock data...")
    agent_data_dir = data_dir / "agent_data"
    if agent_data_dir.exists():
        for entry in os.listdir(str(agent_data_dir)):
            entry_path = agent_data_dir / entry
            if entry_path.is_dir():
                migrate_agent_data(str(entry_path), "agent_data")

    # Migrate crypto data
    print("\n" + "-" * 60)
    print("Migrating Cryptocurrency data...")
    agent_data_dir = data_dir / "agent_data_crypto"
    if agent_data_dir.exists():
        for entry in os.listdir(str(agent_data_dir)):
            entry_path = agent_data_dir / entry
            if entry_path.is_dir():
                migrate_agent_data(str(entry_path), "crypto")

    # Migrate A-stock data
    print("\n" + "-" * 60)
    print("Migrating A-Share data...")
    agent_data_dir = data_dir / "agent_data_astock"
    if agent_data_dir.exists():
        for entry in os.listdir(str(agent_data_dir)):
            entry_path = agent_data_dir / entry
            if entry_path.is_dir():
                migrate_agent_data(str(entry_path), "astock")

    print("\n" + "=" * 60)
    print("Migration completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
