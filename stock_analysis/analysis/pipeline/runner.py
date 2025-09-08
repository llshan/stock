#!/usr/bin/env python3
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from ..config import Config, get_config
from ..core.contracts import (
    AnalysisResult,
    AnalysisSummary,
    Error,
    OperatorResult,
)
from ..data.price_repository import (
    DatabasePriceDataRepository,
    PriceDataRepository,
    TimeRange,
)
from ..operators.base import Operator
from ..operators.drop_alert import DropAlertOperator
from ..operators.ma import MovingAverageOperator
from ..operators.rsi import RSIOperator
from .context import AnalysisContext
from .engine import PipelineEngine

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
    db_path: str = "database/stock_data.db",
    start: Optional[str] = None,
    end: Optional[str] = None,
    enabled_operators: Optional[List[str]] = None,
    *,
    config: Optional[Config] = None,
    repo: Optional[PriceDataRepository] = None,
    engine: Optional[PipelineEngine] = None,
) -> Dict[str, Any]:
    """运行基于数据库的算子流水线，返回结构化结果（JSON 友好）。"""
    cfg = config or get_config()
    repo = repo or DatabasePriceDataRepository(db_path=db_path)
    ops = build_operators(enabled_operators)
    engine = engine or PipelineEngine()
    time_range = TimeRange(start=start or cfg.data.default_start_date, end=end)

    results: Dict[str, Any] = {}
    time.perf_counter()

    try:
        for sym in symbols:
            sym_start = time.perf_counter()
            errors: List[Error] = []
            if not repo.exists(sym):
                logger.warning(f"[{sym}] not found in database; skip")
                ar = AnalysisResult(
                    operators={},
                    summary=AnalysisSummary(
                        trend='unknown',
                        rsi_signal='n/a',
                        drop_alert=False,
                        drop_change=None,
                    ),
                    errors=[
                        Error(
                            code='symbol_not_in_database',
                            message='symbol not found',
                            severity='warn',
                        )
                    ],
                    metrics={'rows': 0, 'duration_ms': 0},
                )
                results[sym] = ar.to_dict()
                continue
            df = repo.get_ohlcv(sym, time_range)
            if df.empty:
                logger.warning(f"[{sym}] no OHLCV data in range; skip")
                ar = AnalysisResult(
                    operators={},
                    summary=AnalysisSummary(
                        trend='unknown',
                        rsi_signal='n/a',
                        drop_alert=False,
                        drop_change=None,
                    ),
                    errors=[
                        Error(
                            code='no_data',
                            message='no data in range',
                            severity='warn',
                        )
                    ],
                    metrics={'rows': 0, 'duration_ms': 0},
                )
                results[sym] = ar.to_dict()
                continue
            ctx = AnalysisContext(symbol=sym, data=df, config=cfg)
            op_results: Dict[str, OperatorResult] = engine.run(ctx, ops)
            # 迁移：保留 fin_ratios 结果以便其他算子访问（当前算子可能已在内部使用 ctx.extras）
            if 'fin_ratios' in op_results and not op_results['fin_ratios'].error:
                ctx.extras['fin_ratios'] = op_results['fin_ratios'].data
            summary = _summarize(ctx, op_results)

            # 收集算子错误
            for v in op_results.values():
                if v.error:
                    errors.append(v.error)

            duration_ms = int((time.perf_counter() - sym_start) * 1000)
            ar = AnalysisResult(
                operators=op_results,
                summary=summary,
                errors=errors,
                metrics={'rows': int(len(df)), 'duration_ms': duration_ms},
            )
            results[sym] = ar.to_dict()
            _log_summary(sym, summary)
    finally:
        # 若 repo 实现了 close/on-exit，这里可以处理
        try:
            close = getattr(repo, 'close', None)
            if callable(close):
                close()
        except Exception:
            pass

    return results


def _summarize(ctx: AnalysisContext, op_results: Dict[str, OperatorResult]) -> AnalysisSummary:
    # derive a simple trend & rsi signal & drop alert
    trend = 'unknown'
    ma_res = op_results.get('ma')
    if ma_res and not ma_res.error and 'ma_20' in (ma_res.data or {}) and 'ma_data' in ctx.extras:
        last_close = float(ctx.extras['ma_data']['Close'].iloc[-1])
        ma20_raw = ma_res.data.get('ma_20') if ma_res.data else None
        ma20 = float(ma20_raw) if ma20_raw is not None else None
        if ma20 is not None:
            trend = 'up' if last_close > ma20 else 'down'

    rsi_res = op_results.get('rsi')
    rsi_sig = 'n/a'
    if rsi_res and not rsi_res.error:
        rsi_sig = str((rsi_res.data or {}).get('signal', 'n/a'))

    drop_res = op_results.get('drop_alert')
    drop_alert = False
    drop_change = None
    if drop_res and not drop_res.error:
        d = drop_res.data or {}
        drop_alert = bool(d.get('is_alert', False))
        drop_change = d.get('percent_change')

    return AnalysisSummary(
        trend=trend,
        rsi_signal=rsi_sig,
        drop_alert=drop_alert,
        drop_change=drop_change,
    )


def _log_summary(symbol: str, summary: AnalysisSummary) -> None:
    logger.info(
        f"[{symbol}] trend={summary.trend} rsi={summary.rsi_signal} "
        f"drop_alert={summary.drop_alert} change={summary.drop_change}%"
    )
