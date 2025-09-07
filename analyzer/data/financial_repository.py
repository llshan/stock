#!/usr/bin/env python3
from __future__ import annotations

from typing import Dict, Optional
import logging
import pandas as pd


logger = logging.getLogger(__name__)


class FinancialRepository:
    """Read financial statements stored in data_service.database.StockDatabase."""

    def __init__(self, db_path: str = 'stock_data.db', db_type: str = 'sqlite'):
        from data_service.database import StockDatabase
        self._db = StockDatabase(db_path=db_path, db_type=db_type)
        self._logger = logging.getLogger(__name__)

    def get_statements(self, symbol: str, statement_type: Optional[str] = None) -> pd.DataFrame:
        df = self._db.get_financial_data(symbol, statement_type=statement_type)
        return df

    def get_pivot(self, symbol: str, statement_type: str) -> pd.DataFrame:
        df = self.get_statements(symbol, statement_type)
        if df is None or df.empty:
            return pd.DataFrame()
        # pivot to items x period_date
        pivot = df.pivot_table(index='item_name', columns='period_date', values='value', aggfunc='first')
        return pivot

