#!/usr/bin/env python3
from __future__ import annotations

from typing import List, Dict, Any
import logging
from .context import AnalysisContext
from ..operators.base import Operator
from ..core.contracts import OperatorResult, Error
import time


logger = logging.getLogger(__name__)


class PipelineEngine:
    """Sequentially run operators, collecting their results with isolation."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def run(self, ctx: AnalysisContext, operators: List[Operator]) -> Dict[str, OperatorResult]:
        results: Dict[str, OperatorResult] = {}
        for op in operators:
            start = time.perf_counter()
            try:
                self.logger.info(f"[{ctx.symbol}] run operator: {op.name}")
                data = op.run(ctx)
                duration_ms = int((time.perf_counter() - start) * 1000)
                if isinstance(data, dict) and 'error' in data and len(data) == 1:
                    # 约定：仅包含 error 字段时视为错误
                    results[op.name] = OperatorResult(
                        data=None,
                        error=Error(code='op_failed', message=str(data['error'])),
                        duration_ms=duration_ms,
                    )
                else:
                    results[op.name] = OperatorResult(
                        data=data if isinstance(data, dict) else {'value': data},
                        error=None,
                        duration_ms=duration_ms,
                    )
            except Exception as e:
                duration_ms = int((time.perf_counter() - start) * 1000)
                self.logger.warning(f"[{ctx.symbol}] operator {op.name} failed: {e}")
                results[op.name] = OperatorResult(
                    data=None,
                    error=Error(code='exception', message=str(e)),
                    duration_ms=duration_ms,
                )
        return results
