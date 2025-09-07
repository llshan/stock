#!/usr/bin/env python3
from __future__ import annotations

from typing import List, Dict, Any, Optional
import logging
from ..config import get_config
from ..data.market_repository import DatabaseMarketDataRepository, MarketDataRepository, TimeRange
from ..pipeline.context import AnalysisContext
from ..pipeline.engine import PipelineEngine
from ..operators.base import Operator
from ..operators.ma import MovingAverageOperator
from ..operators.rsi import RSIOperator
from ..operators.drop_alert import DropAlertOperator


logger = logging.getLogger(__name__)


def build_operators(enabled: Optional[List[str]] = None) -> List[Operator]:
    """Create operator instances based on names. Default set: ma, rsi, drop_alert."""
    if enabled is None:
        cfg = get_config()
        names = list(getattr(cfg.pipeline, 'enabled_operators', ["ma", "rsi", "drop_alert"]))
    else:
        names = enabled
    ops: List[Operator] = []
    for name in names:
        if name == "ma":
            ops.append(MovingAverageOperator())
        elif name == "rsi":
            ops.append(RSIOperator())
        elif name == "drop_alert":
            # read from config if available
            cfg = get_config()
            days = getattr(cfg.pipeline, 'drop_alert_days', 1)
            th = getattr(cfg.pipeline, 'drop_alert_threshold', 15.0)
            ops.append(DropAlertOperator(days=days, threshold_percent=th))
        elif name == "fin_ratios":
            try:
                from ..operators.fin_ratios import FinancialRatioOperator
                ops.append(FinancialRatioOperator())
            except Exception as e:
                logger.warning(f"load fin_ratios failed: {e}")
        elif name == "fin_health":
            try:
                from ..operators.fin_health import FinancialHealthOperator
                ops.append(FinancialHealthOperator())
            except Exception as e:
                logger.warning(f"load fin_health failed: {e}")
        elif name == "drop_alert_7d":
            try:
                from ..operators.drop_alert_7d import DropAlert7dOperator
                cfg = get_config()
                th7 = getattr(cfg.pipeline, 'drop_alert_7d_threshold', 20.0)
                ops.append(DropAlert7dOperator(threshold_percent=th7))
            except Exception as e:
                logger.warning(f"load drop_alert_7d failed: {e}")
        else:
            logger.warning(f"Unknown operator '{name}', skipping")
    return ops


def run_analysis_for_symbols(
    symbols: List[str],
    db_path: str = "stock_data.db",
    start: Optional[str] = None,
    end: Optional[str] = None,
    enabled_operators: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Run operator pipeline for symbols using DB-backed repository only."""
    cfg = get_config()
    repo: MarketDataRepository = DatabaseMarketDataRepository(db_path=db_path)
    ops = build_operators(enabled_operators)
    engine = PipelineEngine()
    time_range = TimeRange(start=start or cfg.data.default_start_date, end=end)

    results: Dict[str, Any] = {}
    for sym in symbols:
        if not repo.exists(sym):
            logger.warning(f"[{sym}] not found in database; skip")
            results[sym] = {'error': 'symbol_not_in_database'}
            continue
        df = repo.get_ohlcv(sym, time_range)
        if df.empty:
            logger.warning(f"[{sym}] no OHLCV data in range; skip")
            results[sym] = {'error': 'no_data'}
            continue
        ctx = AnalysisContext(symbol=sym, data=df, config=cfg)
        op_results = engine.run(ctx, ops)
        # 将关键信息放入 extras，供后续 operator 访问（例如 fin_health 可读取 fin_ratios）
        if 'fin_ratios' in op_results and 'error' not in op_results['fin_ratios']:
            ctx.extras['fin_ratios'] = op_results['fin_ratios']
        summary = _summarize(ctx, op_results)
        results[sym] = {'operators': op_results, 'summary': summary}
        _log_summary(sym, summary)
    return results


def _summarize(ctx: AnalysisContext, op_results: Dict[str, Any]) -> Dict[str, Any]:
    # derive a simple trend & rsi signal & drop alert
    trend = 'unknown'
    if 'ma' in op_results and 'ma_20' in op_results['ma'] and 'ma_data' in ctx.extras:
        last_close = float(ctx.extras['ma_data']['Close'].iloc[-1])
        ma20 = float(op_results['ma']['ma_20']) if op_results['ma'].get('ma_20') is not None else None
        if ma20 is not None:
            trend = 'up' if last_close > ma20 else 'down'

    rsi_sig = op_results.get('rsi', {}).get('signal', 'n/a')
    drop = op_results.get('drop_alert', {})
    return {
        'trend': trend,
        'rsi_signal': rsi_sig,
        'drop_alert': bool(drop.get('is_alert', False)),
        'drop_change': drop.get('percent_change'),
    }


def _log_summary(symbol: str, summary: Dict[str, Any]):
    logger.info(
        f"[{symbol}] trend={summary.get('trend')} rsi={summary.get('rsi_signal')} "
        f"drop_alert={summary.get('drop_alert')} change={summary.get('drop_change')}%"
    )
