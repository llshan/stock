#!/usr/bin/env python3
from __future__ import annotations

from typing import Dict, Any
import pandas as pd
from .base import Operator


class DropAlertOperator(Operator):
    name = "drop_alert"

    def __init__(self, days: int = 1, threshold_percent: float = 15.0):
        self.days = days
        self.threshold = threshold_percent

    def run(self, ctx: "AnalysisContext") -> Dict[str, Any]:
        data: pd.DataFrame = ctx.extras.get('rsi_data') or ctx.extras.get('ma_data') or ctx.data
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
            'message': self._message(ctx.symbol, percent, is_alert)
        }

    def _message(self, symbol: str, percent: float, is_alert: bool) -> str:
        if is_alert:
            return f"⚠️ {symbol} {self.days}D drop {abs(percent):.2f}% >= {self.threshold}%"
        return f"{symbol} {self.days}D change {percent:.2f}%"

