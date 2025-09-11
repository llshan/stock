#!/usr/bin/env python3
"""
财务比率算子

职责：
- 读取财务报表，计算净利润率、ROE、负债率、尝试 PE（基于最新期间与现价/股本）
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, Optional

import pandas as pd

if TYPE_CHECKING:
    from ..pipeline.context import AnalysisContext

from ..data.financial_repository import DatabaseFinancialRepository
from .base import Operator

logger = logging.getLogger(__name__)


class FinancialRatioOperator(Operator):
    name = 'fin_ratios'

    def __init__(self, db_path: str = 'database/stock_data.db'):
        self.db_path = db_path
        self.repo = DatabaseFinancialRepository(db_path=db_path)

    def run(self, ctx: "AnalysisContext") -> Dict[str, Any]:
        symbol = ctx.symbol
        inc = self.repo.get_pivot(symbol, 'income_statement')
        bal = self.repo.get_pivot(symbol, 'balance_sheet')
        if inc.empty or bal.empty:
            return {'error': 'financial_data_unavailable'}
        # choose latest common period
        periods = sorted(set(inc.columns) & set(bal.columns))
        if not periods:
            latest = inc.columns[-1] if len(inc.columns) else None
        else:
            latest = periods[-1]
        if latest is None:
            return {'error': 'no_period'}

        def get(df: pd.DataFrame, key_options: list[str]) -> Optional[float]:
            for k in key_options:
                if k in df.index:
                    try:
                        v = df.loc[k, latest]
                        if pd.notna(v):
                            return float(v)
                    except Exception:
                        continue
            return None

        revenue = get(inc, ['Revenue', 'Revenue, Net', 'Net sales', 'Total Revenue']) or 0.0
        net_income = get(inc, ['Net income', 'Net Income', 'Net Income (Loss) Attributable to Parent', 'Net Income Loss']) or 0.0
        total_equity = (
            get(
                bal,
                [
                    "Total shareholders' equity",  # normalized to straight quote
                    "Stockholders' Equity Attributable to Parent", 
                    "Stockholders Equity",
                    "Total Stockholder Equity", 
                    "Total Equity",
                ],
            )
            or 0.0
        )
        total_assets = get(bal, ['Total assets', 'Assets', 'Total Assets']) or 0.0
        total_liab = get(bal, ['Total liabilities', 'Liabilities', 'Total Liab', 'Total Liabilities']) or 0.0

        ratios: Dict[str, Any] = {}
        if revenue > 0:
            ratios['net_profit_margin'] = (net_income / revenue) * 100.0
        if total_equity > 0:
            ratios['roe'] = (net_income / total_equity) * 100.0
        if total_assets > 0 and total_liab is not None:
            ratios['debt_ratio'] = (total_liab / total_assets) * 100.0

        # PE requires price and EPS; fallback to price/ (net_income/shares)
        price = (
            float(ctx.data['Close'].iloc[-1])
            if 'Close' in ctx.data.columns and len(ctx.data)
            else None
        )
        shares = get(bal, ['Common stock, shares outstanding (in shares)', 'Common stock, shares issued (in shares)', 'Weighted-average shares outstanding (in shares)', 'Common Shares Outstanding', 'Shares Outstanding'])
        if price is not None and shares and shares > 0 and net_income:
            eps = net_income / shares
            if eps != 0:
                ratios['pe_ratio'] = price / eps

        return ratios if ratios else {'error': 'insufficient_financials'}
