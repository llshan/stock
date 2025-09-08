#!/usr/bin/env python3
"""
行情数据仓储（Market Repository）

职责：
- 从数据库读取股票行情（OHLCV）数据
- 标准化列名与索引（DateTimeIndex + [Open, High, Low, Close, Adj Close, Volume]）

说明：
- 依赖 data_service.database.StockDatabase 提供的读接口
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol
import logging
import pandas as pd


logger = logging.getLogger(__name__)


@dataclass
class TimeRange:
    """时间范围（可选）"""
    start: Optional[str] = None  # 'YYYY-MM-DD'
    end: Optional[str] = None    # 'YYYY-MM-DD'


class PriceDataRepository(Protocol):
    """行情数据仓储接口（OHLCV）"""

    def exists(self, symbol: str) -> bool:
        """数据库是否已存在该股票的行情数据"""
        ...

    def get_ohlcv(self, symbol: str, time_range: Optional[TimeRange] = None) -> pd.DataFrame:
        """读取 OHLCV 数据并标准化列名与索引"""
        ...


class DatabasePriceDataRepository:
    """基于数据库实现的行情数据仓储"""

    def __init__(self, db_path: str = "database/stock_data.db", db_type: str = "sqlite"):
        from data_service.database import StockDatabase  # 延迟导入以避免循环依赖
        self._db = StockDatabase(db_path=db_path, db_type=db_type)
        self._logger = logging.getLogger(__name__)

    def exists(self, symbol: str) -> bool:
        try:
            symbols = self._db.get_existing_symbols()
            return symbol in symbols
        except Exception as e:
            self._logger.error(f"exists() 失败: {symbol}: {e}")
            return False

    def get_ohlcv(self, symbol: str, time_range: Optional[TimeRange] = None) -> pd.DataFrame:
        start = time_range.start if time_range else None
        end = time_range.end if time_range else None
        df = self._db.get_stock_prices(symbol, start_date=start, end_date=end)
        return _normalize_ohlcv(df)


def _normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """标准化 OHLCV 列与索引（空数据返回空 DataFrame）"""
    if df is None or df.empty:
        return pd.DataFrame()
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
    cols = [c for c in ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume'] if c in out.columns]
    return out[cols]
