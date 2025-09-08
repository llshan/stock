#!/usr/bin/env python3
"""
综合分析器：基于数据库与可插拔 Operator 的流水线实现。
目标：
  1) 针对数据库中已有数据进行分析；
  2) 支持可插拔 Operator；
  3) 不生成图表，仅文本日志。
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .config import get_config
from .app.runner import run_analysis_for_symbols


logger = logging.getLogger(__name__)


def _period_to_start(period: str) -> Optional[str]:
    try:
        now = datetime.now()
        p = (period or '').lower()
        if p.endswith('mo'):
            months = int(p[:-2])
            days = max(months * 30, 1)
            return (now - timedelta(days=days)).strftime('%Y-%m-%d')
        if p.endswith('y'):
            years = int(p[:-1])
            return (now - timedelta(days=years * 365)).strftime('%Y-%m-%d')
        if p in ('max', 'all'):
            return get_config().data.default_start_date
    except Exception:
        pass
    return get_config().data.default_start_date


class ComprehensiveStockAnalyzer:
    """综合分析器，使用统一流水线实现。"""

    def __init__(self, db_path: str = 'database/stock_data.db', enabled_operators: Optional[List[str]] = None):
        self.db_path = db_path
        self.enabled_operators = enabled_operators or ["ma", "rsi", "drop_alert"]
        self.logger = logging.getLogger(__name__)

    def run_comprehensive_analysis(self, symbols: List[str], period: str = "1y") -> Dict[str, Dict]:
        start = _period_to_start(period)
        self.logger.info(f"综合分析（DB only）: symbols={len(symbols)}, start={start}")
        pipe_results = run_analysis_for_symbols(
            symbols=symbols,
            db_path=self.db_path,
            start=start,
            end=None,
            enabled_operators=self.enabled_operators,
        )
        # 返回新的流水线原生结构，不做额外包装
        return pipe_results

    def comprehensive_analyze(self, symbol: str, period: str = "1y") -> Dict:
        return self.run_comprehensive_analysis([symbol], period).get(symbol, {})


if __name__ == "__main__":
    from utils.logging_utils import setup_logging
    setup_logging()
    syms = ["AAPL", "GOOGL", "LULU"]
    analyzer = ComprehensiveStockAnalyzer()
    out = analyzer.run_comprehensive_analysis(syms, period="6mo")
    for s, res in out.items():
        logger.info(f"{s}: {res.get('summary')}")
