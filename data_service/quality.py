#!/usr/bin/env python3
"""
数据质量评估工具
集中化的数据质量与评级逻辑，供下载器与服务层复用
"""

from datetime import datetime
from typing import Dict, Union

from .models import StockData, FinancialData, DataQuality


def _get_quality_grade(score: float) -> str:
    if score >= 0.9:
        return 'A - 优秀'
    elif score >= 0.7:
        return 'B - 良好'
    elif score >= 0.5:
        return 'C - 一般'
    elif score >= 0.3:
        return 'D - 较差'
    else:
        return 'F - 很差'


def assess_data_quality(stock_data: Union[StockData, Dict],
                        financial_data: Union[FinancialData, Dict],
                        start_date: str) -> DataQuality:
    """评估数据质量（供 Service 与 Downloader 共享）"""
    stock_available = False
    financial_available = False
    issues = []

    if isinstance(stock_data, StockData):
        stock_available = True
    elif isinstance(stock_data, dict):
        stock_available = 'error' not in stock_data

    if isinstance(financial_data, FinancialData):
        financial_available = True
    elif isinstance(financial_data, dict):
        financial_available = 'error' not in financial_data

    stock_data_completeness = None
    if stock_available:
        if isinstance(stock_data, StockData):
            data_points = stock_data.data_points
        else:
            data_points = stock_data.get('data_points', 0)
        expected_points = (datetime.now() - datetime.strptime(start_date, '%Y-%m-%d')).days
        stock_data_completeness = min(1.0, data_points / (expected_points * 0.7))  # 粗略考虑周末
    else:
        issues.append('股票价格数据不可用')

    financial_statements_count = 0
    if financial_available:
        if isinstance(financial_data, FinancialData):
            statements = financial_data.financial_statements
        else:
            statements = financial_data.get('financial_statements', {})
        financial_statements_count = len(statements)
        if len(statements) < 3:
            issues.append('财务报表数据不完整')
    else:
        issues.append('财务数据不可用')

    completeness_score = 0
    if stock_available:
        completeness_score += 0.6
    if financial_available:
        completeness_score += 0.4

    quality_grade = _get_quality_grade(completeness_score)

    return DataQuality(
        stock_data_available=stock_available,
        financial_data_available=financial_available,
        data_completeness=completeness_score,
        quality_grade=quality_grade,
        issues=issues,
        stock_data_completeness=stock_data_completeness,
        financial_statements_count=financial_statements_count
    )

