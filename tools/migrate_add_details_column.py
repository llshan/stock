#!/usr/bin/env python3
"""
One-off migration: ensure download_logs.details column exists in an existing SQLite DB.

Usage:
  python tools/migrate_add_details_column.py --db database/stock_data.db
"""

import argparse
import sqlite3
from pathlib import Path


def ensure_details_column(conn: sqlite3.Connection) -> bool:
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(download_logs)")
    cols = [row[1] for row in cur.fetchall()]
    if 'details' in cols:
        return False
    cur.execute("ALTER TABLE download_logs ADD COLUMN details TEXT")
    conn.commit()
    return True


def main() -> int:
    p = argparse.ArgumentParser(description="Add details column to download_logs if missing")
    p.add_argument("--db", required=True, help="Path to SQLite database file")
    args = p.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"DB not found: {db_path}")
        return 2

    conn = sqlite3.connect(str(db_path))
    try:
        added = ensure_details_column(conn)
        if added:
            print("Added column: download_logs.details")
        else:
            print("Column already exists: download_logs.details")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())

