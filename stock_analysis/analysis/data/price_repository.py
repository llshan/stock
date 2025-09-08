#!/usr/bin/env python3
"""
价格数据仓储（统一版本）

职责：
- 从数据库读取股票行情（OHLCV）数据
- 标准化列名与索引（DateTimeIndex + [Open, High, Low, Close, Adj Close, Volume]）
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol, Tuple

import pandas as pd

from stock_analysis.data.storage import create_storage


@dataclass
class TimeRange:
    """时间范围（可选，使用字符串）"""

    start: Optional[str] = None  # 'YYYY-MM-DD'
    end: Optional[str] = None  # 'YYYY-MM-DD'


class PriceDataRepository(Protocol):
    """行情数据仓储接口（与 runner 保持一致）"""

    def exists(self, symbol: str) -> bool: ...

    def get_ohlcv(self, symbol: str, time_range: Optional[TimeRange] = None) -> pd.DataFrame: ...


class DatabasePriceDataRepository(PriceDataRepository):
    """基于数据库实现的行情数据仓储（使用 storage 接口）"""

    def __init__(self, db_path: str = "database/stock_data.db"):
        self._db = create_storage('sqlite', db_path=db_path)
        self._symbols_cache: Optional[set[str]] = None
        self._cache: Dict[Tuple[str, Optional[str], Optional[str]], pd.DataFrame] = {}

    def __enter__(self) -> DatabasePriceDataRepository:
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        try:
            self.close()
        except Exception:
            pass

    def exists(self, symbol: str) -> bool:
        try:
            if self._symbols_cache is None:
                self._symbols_cache = set(self._db.get_existing_symbols())
            return symbol in self._symbols_cache
        except Exception:
            return False

    def get_ohlcv(self, symbol: str, time_range: Optional[TimeRange] = None) -> pd.DataFrame:
        start = time_range.start if time_range else None
        end = time_range.end if time_range else None
        key = (symbol, start, end)
        if key in self._cache:
            return self._cache[key]
        stock = self._db.get_stock_data(symbol, start, end)
        if not stock or stock.data_points == 0:
            df = pd.DataFrame()
            self._cache[key] = df
            return df
        df = pd.DataFrame(
            {
                'Date': pd.to_datetime(stock.price_data.dates),
                'Open': stock.price_data.open,
                'High': stock.price_data.high,
                'Low': stock.price_data.low,
                'Close': stock.price_data.close,
                'Adj Close': stock.price_data.adj_close or stock.price_data.close,
                'Volume': stock.price_data.volume,
            }
        )
        df = df.set_index('Date').sort_index()
        df = df[['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']]
        self._cache[key] = df
        return df

    def close(self) -> None:
        try:
            close = getattr(self._db, 'close', None)
            if callable(close):
                close()
        except Exception:
            pass
