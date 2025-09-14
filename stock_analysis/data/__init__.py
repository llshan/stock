"""
数据服务模块包
包含数据下载、存储和管理功能
"""

from .data_service import DataService
from .models import (
    FinancialData,
    StockData,
)
from .models.quality_models import DownloadResult, BatchDownloadResult
from .storage import SQLiteStorage, create_storage

__all__ = [
    'DataService',
    'create_storage',
    'SQLiteStorage',
    'StockData',
    'FinancialData',
    'DownloadResult',
    'BatchDownloadResult',
]
