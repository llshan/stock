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

from .config import get_config, Config
from .pipeline.runner import run_analysis_for_symbols


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


class AnalysisService:
    """综合分析服务，使用统一流水线实现。"""

    def __init__(self, db_path: str = 'database/stock_data.db', enabled_operators: Optional[List[str]] = None, config: Optional[Config] = None):
        self.db_path = db_path
        self.enabled_operators = enabled_operators or ["ma", "rsi", "drop_alert"]
        self.config = config or get_config()
        self.logger = logging.getLogger(__name__)

    def run_analysis(self, symbols: List[str], period: str = "1y", start: Optional[str] = None, end: Optional[str] = None) -> Dict[str, Dict]:
        start_final = start or _period_to_start(period) or self.config.data.default_start_date
        self.logger.info(f"综合分析（DB only）: symbols={len(symbols)}, start={start_final}, end={end or 'latest'}")
        pipe_results = run_analysis_for_symbols(
            symbols=symbols,
            db_path=self.db_path,
            start=start_final,
            end=end,
            enabled_operators=self.enabled_operators,
            config=self.config,
        )
        # 返回新的流水线原生结构，不做额外包装
        return pipe_results


if __name__ == "__main__":
    from utils.logging_utils import setup_logging
    setup_logging()
    syms = ["AAPL", "GOOGL", "LULU"]
    analyzer = AnalysisService()
    out = analyzer.run_analysis(syms, period="6mo")
    for s, res in out.items():
        logger.info(f"{s}: {res.get('summary')}")
