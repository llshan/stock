"""
数据服务模块包
包含数据下载、存储和管理功能
"""

# 核心数据库和服务
from .database import StockDatabase
from .data_service import DataService

# 数据下载器 - 推荐使用 DataManager
from .downloaders import (
    BaseDownloader,
    YFinanceDataDownloader,
    StooqDataDownloader, 
    DataManager
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
    DownloadErrorInfo,
    create_empty_stock_data,
    create_empty_financial_data
)

# 便捷函数 - 推荐的使用方式
from .config import DataServiceConfig


def create_data_manager(database_path: str = "stocks.db", **config) -> DataManager:
    """
    创建数据管理器的推荐方式
    
    Args:
        database_path: 数据库文件路径
        **config: 额外配置参数（如max_retries, base_delay等）
        
    Returns:
        配置好的 DataManager 实例
    
    Example:
        >>> manager = create_data_manager("my_stocks.db")
        >>> result = manager.download_stock_data("AAPL")
    """
    # 统一由配置管理重试与数据库参数
    cfg = DataServiceConfig.from_env(database_path)
    if config:
        cfg.update(**config)
    database = StockDatabase(cfg.database.db_path, cfg.database.db_type)
    return DataManager(
        database,
        max_retries=cfg.downloader.max_retries,
        base_delay=cfg.downloader.base_delay
    )


__all__ = [
    # 🎯 推荐使用 - 主要入口点
    'create_data_manager',
    'DataManager',
    
    # 核心组件
    'StockDatabase',
    'DataService',
    
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
    'DownloadErrorInfo',
    
    # 工具函数
    'create_empty_stock_data',
    'create_empty_financial_data'
]
