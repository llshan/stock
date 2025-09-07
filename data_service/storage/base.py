#!/usr/bin/env python3
"""
存储层基础抽象类
定义存储操作的通用接口
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
import pandas as pd
try:
    from ..models import StockData, FinancialData, ComprehensiveData, DataQuality
except ImportError:
    # Fallback for direct execution
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from models import StockData, FinancialData, ComprehensiveData, DataQuality


class BaseStorage(ABC):
    """存储层基础抽象类"""
    
    @abstractmethod
    def connect(self):
        """建立存储连接"""
        pass
    
    @abstractmethod
    def close(self):
        """关闭存储连接"""
        pass
    
    @abstractmethod
    def store_stock_data(self, symbol: str, stock_data: Union[StockData, Dict]) -> bool:
        """存储股票价格数据"""
        pass
    
    @abstractmethod
    def store_financial_data(self, symbol: str, financial_data: Union[FinancialData, Dict]) -> bool:
        """存储财务数据"""
        pass
    
    @abstractmethod
    def store_data_quality(self, symbol: str, quality_data: Union[DataQuality, Dict]) -> bool:
        """存储数据质量评估"""
        pass
    
    @abstractmethod
    def get_stock_data(self, symbol: str, start_date: str = None, end_date: str = None) -> Optional[StockData]:
        """获取股票数据"""
        pass
    
    @abstractmethod
    def get_financial_data(self, symbol: str) -> Optional[FinancialData]:
        """获取财务数据"""
        pass
    
    @abstractmethod
    def get_existing_symbols(self) -> List[str]:
        """获取已存储的股票代码列表"""
        pass
    
    @abstractmethod
    def get_last_update_date(self, symbol: str) -> Optional[str]:
        """获取最后更新日期"""
        pass


class StorageError(Exception):
    """存储操作异常"""
    def __init__(self, message: str, operation: str = None):
        super().__init__(message)
        self.operation = operation
        self.message = message