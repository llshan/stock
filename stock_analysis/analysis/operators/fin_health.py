#!/usr/bin/env python3
"""
财务健康度算子

职责：
- 基于财务比率（来自 fin_ratios）进行简单打分并给出等级（A-F）
"""

from __future__ import annotations

from typing import Dict, Any
import logging
from .base import Operator


logger = logging.getLogger(__name__)


class FinancialHealthOperator(Operator):
    name = 'fin_health'

    def run(self, ctx: "AnalysisContext") -> Dict[str, Any]:
        ratios = ctx.extras.get('fin_ratios') or {}
        score = 0
        # 简单打分模型
        roe = ratios.get('roe') or 0
        if roe > 15:
            score += 20
        elif roe > 10:
            score += 15
        elif roe > 5:
            score += 10

        debt = ratios.get('debt_ratio')
        if debt is not None:
            if debt < 30:
                score += 20
            elif debt < 50:
                score += 15
            elif debt < 70:
                score += 10

        npm = ratios.get('net_profit_margin') or 0
        if npm > 20:
            score += 20
        elif npm > 10:
            score += 15
        elif npm > 5:
            score += 10

        pe = ratios.get('pe_ratio')
        if pe and pe > 0:
            if pe < 15:
                score += 15
            elif pe < 25:
                score += 10
            elif pe < 35:
                score += 5

        grade = (
            'A' if score >= 80 else
            'B' if score >= 60 else
            'C' if score >= 40 else
            'D' if score >= 20 else 'F'
        )
        return {'health_score': score, 'grade': grade}
