#!/usr/bin/env python3
"""
Validate that SQLiteStorage initializes schema correctly and tables exist.
This does not perform any network operations.

Usage:
  python tools/validate_schema.py --db database/stock_data.db
"""

import argparse
from pathlib import Path

from stock_analysis.data import create_storage


def main() -> int:
    p = argparse.ArgumentParser(description="Validate SQLite schema for stock_analysis")
    p.add_argument("--db", default="database/stock_data.db", help="Path to SQLite database file")
    args = p.parse_args()

    storage = create_storage('sqlite', db_path=str(Path(args.db)))
    try:
        symbols = storage.get_existing_symbols()
        print(f"Schema OK. Existing symbols: {len(symbols)}")
        return 0
    finally:
        storage.close()


if __name__ == "__main__":
    raise SystemExit(main())

