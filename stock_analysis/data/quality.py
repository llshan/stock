#!/usr/bin/env python3
"""
数据质量评估工具 - 向后兼容性包装器
集中化的数据质量与评级逻辑，供下载器与服务层复用

注意: assess_data_quality 函数已迁移到 models.quality_models.DataQuality.assess_data_quality
本模块提供向后兼容性支持
"""

from typing import Dict, Union

from .models import DataQuality, FinancialData, StockData


def assess_data_quality(
    stock_data: Union[StockData, Dict],
    financial_data: Union[FinancialData, Dict],
    start_date: str,
) -> DataQuality:
    """
    评估数据质量（向后兼容性包装器）
    
    注意: 此函数已迁移到 DataQuality.assess_data_quality 类方法
    建议使用新的类方法: DataQuality.assess_data_quality(stock_data, financial_data, start_date)
    """
    return DataQuality.assess_data_quality(stock_data, financial_data, start_date)
