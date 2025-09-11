"""
数据服务模块包
包含数据下载、存储和管理功能
"""

# 核心服务和存储
from .data_service import DataService

# 数据下载器（底层）
from .downloaders import (
    BaseDownloader,
    StooqDataDownloader,
    FinnhubDownloader,
)

# 数据模型
from .models import (
    BasicInfo,
    ComprehensiveData,
    DataQuality,
    DownloadError,
    FinancialData,
    FinancialStatement,
    PriceData,
    StockData,
    SummaryStats,
    create_empty_financial_data,
    create_empty_stock_data,
)
from .storage import SQLiteStorage, create_storage

__all__ = [
    # 核心组件
    'DataService',
    'create_storage',
    'SQLiteStorage',
    # 下载器（底层）
    'StooqDataDownloader',
    'FinnhubDownloader',
    'BaseDownloader',
    # 数据模型
    'StockData',
    'FinancialData',
    'ComprehensiveData',
    'PriceData',
    'SummaryStats',
    'BasicInfo',
    'FinancialStatement',
    'DataQuality',
    'DownloadError',
    # 工具函数
    'create_empty_stock_data',
    'create_empty_financial_data',
]
