#!/usr/bin/env python3
"""
RSI 算子（相对强弱指数）

职责：
- 计算 RSI 与信号（overbought/oversold/neutral），将结果写入 ctx.extras['rsi_data']
"""

from __future__ import annotations

from typing import Dict, Any
import logging
import pandas as pd
from .base import Operator


logger = logging.getLogger(__name__)


class RSIOperator(Operator):
    name = "rsi"

    def __init__(self, period: int | None = None):
        self.period = period

    def run(self, ctx: "AnalysisContext") -> Dict[str, Any]:
        data: pd.DataFrame = ctx.extras.get('ma_data') or ctx.data.copy()
        period = self.period or getattr(ctx.config.technical, 'rsi_period', 14)
        if 'Close' not in data.columns or len(data) < period + 1:
            return {'error': 'insufficient_data'}
        delta = data['Close'].diff()
        gain = (delta.clip(lower=0)).rolling(window=period).mean()
        loss = (-delta.clip(upper=0)).rolling(window=period).mean()
        rs = gain / loss.replace(0, float('nan'))
        data['RSI'] = 100 - (100 / (1 + rs))
        last_rsi = float(data['RSI'].iloc[-1]) if not data['RSI'].isna().iloc[-1] else float('nan')
        overbought = ctx.config.technical.rsi_overbought
        oversold = ctx.config.technical.rsi_oversold
        if last_rsi >= overbought:
            signal = 'overbought'
        elif last_rsi <= oversold:
            signal = 'oversold'
        else:
            signal = 'neutral'
        ctx.extras['rsi_data'] = data
        return {'period': period, 'rsi': last_rsi, 'signal': signal}
