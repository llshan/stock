#!/usr/bin/env python3
"""
数据模型模块
重构后的模型组织
"""

# 基础模型
from .base_models import (
    BaseDataModel,
    BasicInfo,
    DownloadError,
    SummaryStats,
    calculate_summary_stats,
    create_timestamp,
    validate_date_string,
    validate_symbol,
)

# 财务相关模型
from .financial_models import (
    FinancialData,
    FinancialStatement,
    create_empty_basic_info,
    create_empty_financial_data,
    create_empty_financial_statement,
    merge_financial_statements,
)

# 价格相关模型
from .price_models import (
    PriceData,
    StockData,
    create_empty_price_data,
    create_empty_stock_data,
    merge_price_data,
)

# 数据质量相关模型
from .quality_models import (
    BatchDownloadResult,
    ComprehensiveData,
    DataQuality,
    DownloadResult,
    assess_overall_quality,
    create_download_result,
    create_empty_data_quality,
)

__all__ = [
    # 基础模型
    'BaseDataModel',
    'SummaryStats',
    'BasicInfo',
    'DownloadError',
    # 价格模型
    'PriceData',
    'StockData',
    # 财务模型
    'FinancialStatement',
    'FinancialData',
    # 质量模型
    'DataQuality',
    'ComprehensiveData',
    'DownloadResult',
    'BatchDownloadResult',
    # 工具函数
    'create_timestamp',
    'validate_symbol',
    'validate_date_string',
    'calculate_summary_stats',
    'create_empty_price_data',
    'create_empty_stock_data',
    'create_empty_basic_info',
    'create_empty_financial_statement',
    'create_empty_financial_data',
    'create_empty_data_quality',
    'merge_price_data',
    'merge_financial_statements',
    'assess_overall_quality',
    'create_download_result',
]
