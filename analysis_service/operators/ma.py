#!/usr/bin/env python3
"""
移动平均算子（MA）

职责：
- 基于收盘价计算多窗口移动平均，并将结果写入 ctx.extras['ma_data']
"""

from __future__ import annotations

from typing import Dict, Any, List
import logging
import pandas as pd
from .base import Operator


logger = logging.getLogger(__name__)


class MovingAverageOperator(Operator):
    name = "ma"

    def __init__(self, windows: List[int] | None = None):
        self.windows = windows

    def run(self, ctx: "AnalysisContext") -> Dict[str, Any]:
        data: pd.DataFrame = ctx.data.copy()
        windows = self.windows or getattr(ctx.config.technical, 'ma_windows', [5, 10, 20, 50])
        for w in windows:
            data[f"MA_{w}"] = data['Close'].rolling(window=w).mean()
        # expose only last values for summary, and the computed frame in extras
        last = data.iloc[-1] if len(data) else None
        result: Dict[str, Any] = {
            'windows': windows,
        }
        if last is not None:
            for w in windows:
                result[f"ma_{w}"] = float(last.get(f"MA_{w}", float('nan')))
        ctx.extras['ma_data'] = data
        return result
