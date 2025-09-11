#!/usr/bin/env python3
"""
财务数据仓储（Financial Repository）

职责：
- 从数据库读取财务报表明细
- 提供透视后的“科目×期间”表

说明：
- 基于 data_service.storage 接口读取财务数据（FinancialData dataclass）
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Protocol

import pandas as pd

from stock_analysis.data.storage import create_storage

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

    def __init__(self, db_path: str = 'database/stock_data.db'):
        self._db = create_storage('sqlite', db_path=db_path)
        self._logger = logging.getLogger(__name__)

    def get_statements(self, symbol: str, statement_type: Optional[str] = None) -> pd.DataFrame:
        """从新的分离表结构中读取财务报表数据"""
        try:
            import sqlite3
            
            # 直接查询数据库的分离表
            conn = sqlite3.connect(self._db.db_path)
            conn.row_factory = sqlite3.Row
            
            # 构建查询
            tables = []
            if statement_type is None:
                tables = ['income_statement', 'balance_sheet', 'cash_flow']
            else:
                tables = [statement_type]
            
            rows = []
            for table_name in tables:
                query = f"SELECT period, metric_name, metric_value FROM {table_name} WHERE symbol = ? ORDER BY period DESC"
                try:
                    cursor = conn.execute(query, (symbol,))
                    for row in cursor:
                        rows.append({
                            'statement_type': table_name,
                            'period_date': row['period'],
                            'item_name': row['metric_name'],
                            'value': row['metric_value']
                        })
                except sqlite3.OperationalError as e:
                    self._logger.warning(f"Table {table_name} not found or query failed: {e}")
                    continue
            
            conn.close()
            
            df = pd.DataFrame(rows)
            # 规范列类型
            if not df.empty:
                if 'period_date' in df.columns:
                    try:
                        df['period_date'] = pd.to_datetime(df['period_date']).dt.date.astype(str)
                    except Exception:
                        pass
                        
                # Normalize metric names to handle Unicode quote variations
                # Replace curly quotes with straight quotes for consistency
                df['item_name'] = df['item_name'].str.replace(chr(8217), chr(39), regex=False)  # ' -> '
                df['item_name'] = df['item_name'].str.replace(chr(8216), chr(39), regex=False)  # ' -> '
                df['item_name'] = df['item_name'].str.replace(chr(8220), '"', regex=False)     # " -> "
                df['item_name'] = df['item_name'].str.replace(chr(8221), '"', regex=False)     # " -> "
            return df
        except Exception as e:
            self._logger.error(f"get_statements 失败: {symbol}: {e}")
            return pd.DataFrame()

    def get_pivot(self, symbol: str, statement_type: str) -> pd.DataFrame:
        df = self.get_statements(symbol, statement_type)
        if df is None or df.empty:
            return pd.DataFrame()
        
        # After normalization, we may have duplicate metric names for the same periods
        # Keep only the most recent data for each metric_name/period combination
        df = df.sort_values('period_date', ascending=False)
        df_deduped = df.drop_duplicates(subset=['item_name', 'period_date'], keep='first')
        
        pivot = df_deduped.pivot_table(
            index='item_name',
            columns='period_date',
            values='value',
            aggfunc='first',
        )
        return pivot
