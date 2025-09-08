"""
数据服务模块包
包含数据下载、存储和管理功能
"""

# 核心服务和存储
from .data_service import DataService
from .storage import create_storage, SQLiteStorage

# 数据下载器 - 推荐使用 HybridDataDownloader
from .downloaders import (
    BaseDownloader,
    YFinanceDataDownloader,
    StooqDataDownloader, 
    HybridDataDownloader
)

# 数据模型
from .models import (
    StockData,
    FinancialData, 
    ComprehensiveData,
    PriceData,
    SummaryStats,
    BasicInfo,
    FinancialStatement,
    DataQuality,
    DownloadError,
    create_empty_stock_data,
    create_empty_financial_data
)

__all__ = [
    # 🎯 推荐使用 - 主要入口点
    'HybridDataDownloader',
    
    # 核心组件
    'DataService',
    'create_storage',
    'SQLiteStorage',
    
    # 其他下载器
    'YFinanceDataDownloader',
    'StooqDataDownloader',
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
    'create_empty_financial_data'
]
