#!/usr/bin/env python3
"""
Repository layer for reading market (price) data from the database.
This abstracts away the underlying schema and provides a clean OHLCV interface.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol
import logging
import pandas as pd


logger = logging.getLogger(__name__)


@dataclass
class TimeRange:
    start: Optional[str] = None  # 'YYYY-MM-DD'
    end: Optional[str] = None    # 'YYYY-MM-DD'


class MarketDataRepository(Protocol):
    def exists(self, symbol: str) -> bool: ...
    def get_ohlcv(self, symbol: str, time_range: Optional[TimeRange] = None) -> pd.DataFrame: ...


class DatabaseMarketDataRepository:
    """Repository backed by data_service.database.StockDatabase."""

    def __init__(self, db_path: str = "stock_data.db", db_type: str = "sqlite"):
        from data_service.database import StockDatabase  # lazy import to avoid cycles
        self._db = StockDatabase(db_path=db_path, db_type=db_type)
        self._logger = logging.getLogger(__name__)

    def exists(self, symbol: str) -> bool:
        try:
            symbols = self._db.get_existing_symbols()
            return symbol in symbols
        except Exception as e:
            self._logger.error(f"exists() failed for {symbol}: {e}")
            return False

    def get_ohlcv(self, symbol: str, time_range: Optional[TimeRange] = None) -> pd.DataFrame:
        start = time_range.start if time_range else None
        end = time_range.end if time_range else None
        df = self._db.get_stock_prices(symbol, start_date=start, end_date=end)
        if df is None or len(df) == 0:
            return pd.DataFrame()
        # Normalize to common OHLCV columns and DateTime index
        mapping = {
            'open_price': 'Open',
            'high_price': 'High',
            'low_price': 'Low',
            'close_price': 'Close',
            'adj_close': 'Adj Close',
            'volume': 'Volume',
            'date': 'Date',
        }
        out = df.rename(columns=mapping)
        if 'Date' in out.columns:
            out['Date'] = pd.to_datetime(out['Date'])
            out = out.set_index('Date').sort_index()
        # Keep only OHLCV
        cols = [c for c in ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume'] if c in out.columns]
        return out[cols]

