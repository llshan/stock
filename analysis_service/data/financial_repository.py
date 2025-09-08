#!/usr/bin/env python3
"""
财务数据仓储（Financial Repository）

职责：
- 从数据库读取财务报表明细
- 提供透视后的“科目×期间”表

说明：
- 依赖 data_service.database.StockDatabase 提供的读接口
"""

from __future__ import annotations

from typing import Optional, Protocol
import logging
import pandas as pd


logger = logging.getLogger(__name__)


class FinancialDataRepository(Protocol):
    """财务数据仓储接口"""

    def get_statements(self, symbol: str, statement_type: Optional[str] = None) -> pd.DataFrame:
        """读取原始财务报表记录（行式）"""
        ...

    def get_pivot(self, symbol: str, statement_type: str) -> pd.DataFrame:
        """读取并透视为 科目×期间 的 DataFrame"""
        ...


class DatabaseFinancialRepository:
    """基于数据库实现的财务数据仓储"""

    def __init__(self, db_path: str = 'database/stock_data.db', db_type: str = 'sqlite'):
        from data_service.database import StockDatabase  # 延迟导入避免循环依赖
        self._db = StockDatabase(db_path=db_path, db_type=db_type)
        self._logger = logging.getLogger(__name__)

    def get_statements(self, symbol: str, statement_type: Optional[str] = None) -> pd.DataFrame:
        return self._db.get_financial_data(symbol, statement_type=statement_type)

    def get_pivot(self, symbol: str, statement_type: str) -> pd.DataFrame:
        df = self.get_statements(symbol, statement_type)
        if df is None or df.empty:
            return pd.DataFrame()
        pivot = df.pivot_table(index='item_name', columns='period_date', values='value', aggfunc='first')
        return pivot
