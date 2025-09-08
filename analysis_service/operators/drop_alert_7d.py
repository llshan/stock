#!/usr/bin/env python3
"""
7 日跌幅预警算子

职责：
- 检测最近 7 日跌幅是否超过阈值（默认 20%）
"""

from __future__ import annotations

from typing import Dict, Any
import logging
import pandas as pd
from .base import Operator


logger = logging.getLogger(__name__)


class DropAlert7dOperator(Operator):
    name = "drop_alert_7d"

    def __init__(self, threshold_percent: float = 20.0):
        self.days = 7
        self.threshold = threshold_percent

    def run(self, ctx: "AnalysisContext") -> Dict[str, Any]:
        data: pd.DataFrame = ctx.data
        if len(data) < self.days + 1 or 'Close' not in data.columns:
            return {'error': 'insufficient_data'}
        current_price = float(data['Close'].iloc[-1])
        past_price = float(data['Close'].iloc[-(self.days + 1)])
        change = current_price - past_price
        percent = (change / past_price) * 100 if past_price else 0.0
        is_alert = percent <= -self.threshold
        return {
            'days': self.days,
            'threshold': self.threshold,
            'current_price': current_price,
            'past_price': past_price,
            'percent_change': percent,
            'is_alert': is_alert,
        }
