#!/usr/bin/env python3
"""
数据模型模块
重构后的模型组织，保持向后兼容性
"""

# 基础模型
from .base_models import (
    BaseDataModel,
    SummaryStats,
    BasicInfo,
    DownloadError,
    create_timestamp,
    validate_symbol,
    validate_date_string,
    calculate_summary_stats
)

# 价格相关模型
from .price_models import (
    PriceData,
    StockData,
    create_empty_price_data,
    create_empty_stock_data,
    merge_price_data
)

# 财务相关模型  
from .financial_models import (
    FinancialStatement,
    FinancialData,
    create_empty_basic_info,
    create_empty_financial_statement,
    create_empty_financial_data,
    merge_financial_statements
)

# 数据质量相关模型
from .quality_models import (
    DataQuality,
    ComprehensiveData,
    DownloadResult,
    BatchDownloadResult,
    create_empty_data_quality,
    assess_overall_quality,
    create_download_result
)

# 为了向后兼容，保持原有的导入别名
DownloadErrorInfo = DownloadError  # 别名兼容

# 向后兼容的工具函数，保持原有的函数签名
def create_empty_stock_data(symbol: str, start_date: str, end_date: str, error_msg: str) -> dict:
    """向后兼容的空股票数据创建函数"""
    from .price_models import create_empty_stock_data as _create_empty_stock_data
    return _create_empty_stock_data(symbol, start_date, end_date, error_msg)


def create_empty_financial_data(symbol: str, error_msg: str) -> dict:
    """向后兼容的空财务数据创建函数"""
    from .financial_models import create_empty_financial_data as _create_empty_financial_data
    return _create_empty_financial_data(symbol, error_msg)


__all__ = [
    # 基础模型
    'BaseDataModel',
    'SummaryStats', 
    'BasicInfo',
    'DownloadError',
    'DownloadErrorInfo',  # 向后兼容别名
    
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
    'create_download_result'
]