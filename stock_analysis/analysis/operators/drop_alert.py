#!/usr/bin/env python3
"""
跌幅预警算子（N 日）

职责：
- 检测最近 N 日相对过去价格的跌幅是否超过阈值
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict

import pandas as pd

if TYPE_CHECKING:
    from ..pipeline.context import AnalysisContext

from .base import Operator

logger = logging.getLogger(__name__)


class DropAlertOperator(Operator):
    name = "drop_alert"

    def __init__(self, days: int = 1, threshold_percent: float = 15.0):
        self.days = days
        self.threshold = threshold_percent

    def run(self, ctx: "AnalysisContext") -> Dict[str, Any]:
        data: pd.DataFrame = ctx.extras.get('rsi_data')
        if data is None:
            data = ctx.extras.get('ma_data')
        if data is None:
            data = ctx.data
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
            'message': self._message(ctx.symbol, percent, is_alert),
        }

    def _message(self, symbol: str, percent: float, is_alert: bool) -> str:
        if is_alert:
            return (
                f"⚠️ {symbol} 近{self.days}日下跌 {abs(percent):.2f}%（超过阈值 {self.threshold}%）"
            )
        direction = "上涨" if percent > 0 else ("下跌" if percent < 0 else "持平")
        return f"{symbol} 近{self.days}日{direction} {abs(percent):.2f}%"
