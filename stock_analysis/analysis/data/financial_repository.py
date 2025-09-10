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
        try:
            fin = self._db.get_financial_data(symbol)
            if fin is None or not getattr(fin, 'financial_statements', None):
                return pd.DataFrame()
            rows: List[Dict[str, Any]] = []
            for stmt_type, stmt in fin.financial_statements.items():
                if statement_type and stmt_type != statement_type:
                    continue
                periods = list(getattr(stmt, 'periods', []) or [])
                items = getattr(stmt, 'items', {}) or {}
                for idx, period in enumerate(periods):
                    for item_name, values in items.items():
                        val = None
                        try:
                            if idx < len(values):
                                val = values[idx]
                        except Exception:
                            val = None
                        rows.append(
                            {
                                'statement_type': stmt_type,
                                'period_date': period,
                                'item_name': item_name,
                                'value': val,
                            }
                        )
            df = pd.DataFrame(rows)
            # 规范列类型
            if not df.empty:
                if 'period_date' in df.columns:
                    try:
                        df['period_date'] = pd.to_datetime(df['period_date']).dt.date.astype(str)
                    except Exception:
                        pass
            return df
        except Exception as e:
            self._logger.error(f"get_statements 失败: {symbol}: {e}")
            return pd.DataFrame()

    def get_pivot(self, symbol: str, statement_type: str) -> pd.DataFrame:
        df = self.get_statements(symbol, statement_type)
        if df is None or df.empty:
            return pd.DataFrame()
        pivot = df.pivot_table(
            index='item_name',
            columns='period_date',
            values='value',
            aggfunc='first',
        )
        return pivot
