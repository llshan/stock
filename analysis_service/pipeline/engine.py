#!/usr/bin/env python3
from __future__ import annotations

from typing import List, Dict, Any
import logging
from .context import AnalysisContext
from ..operators.base import Operator


logger = logging.getLogger(__name__)


class PipelineEngine:
    """Sequentially run operators, collecting their results with isolation."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def run(self, ctx: AnalysisContext, operators: List[Operator]) -> Dict[str, Any]:
        results: Dict[str, Any] = {}
        for op in operators:
            try:
                self.logger.info(f"[{ctx.symbol}] run operator: {op.name}")
                res = op.run(ctx)
                results[op.name] = res
            except Exception as e:
                self.logger.warning(f"[{ctx.symbol}] operator {op.name} failed: {e}")
                results[op.name] = {'error': str(e)}
        return results

