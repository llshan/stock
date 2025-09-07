#!/usr/bin/env python3
"""
股票数据库模块（向后兼容层）
现在使用新的存储层架构，保持向后兼容性
"""

import warnings
import pandas as pd
from typing import Dict, List, Optional, Any, Union
try:
    from .storage import SQLiteStorage, create_storage
    from .models import StockData, FinancialData, ComprehensiveData, DataQuality
except ImportError:
    # Fallback for direct execution
    from storage import SQLiteStorage, create_storage
    from models import StockData, FinancialData, ComprehensiveData, DataQuality


class StockDatabase:
    """
    向后兼容的数据库接口
    现在作为新存储层的包装器
    """
    
    def __init__(self, db_path: str = "stock_data.db", db_type: str = "sqlite"):
        """
        初始化股票数据库
        
        Args:
            db_path: 数据库路径或连接字符串
            db_type: 数据库类型 ('sqlite' 或 'postgresql')
        """
        # 发出弃用警告
        warnings.warn(
            "StockDatabase 已弃用，请使用 storage.create_storage() 或直接使用存储层",
            DeprecationWarning,
            stacklevel=2
        )
        
        self.db_path = db_path
        self.db_type = db_type
        
        # 使用新的存储层
        if db_type == "sqlite":
            self._storage = SQLiteStorage(db_path)
        else:
            self._storage = create_storage(db_type, db_path=db_path)
    
    def store_stock_basic_info(self, symbol: str, basic_info: Union['BasicInfo', Dict]):
        """存储股票基本信息"""
        # 通过存储股票数据来间接存储基本信息
        from .models import StockData, PriceData, SummaryStats
        from datetime import datetime
        
        # 创建一个空的股票数据对象来携带基本信息
        empty_price_data = PriceData(
            dates=[], open=[], high=[], low=[], close=[], volume=[], adj_close=[]
        )
        empty_stats = SummaryStats(0, 0, 0, 0, 0)
        
        stock_data = StockData(
            symbol=symbol,
            start_date="",
            end_date="",
            data_points=0,
            price_data=empty_price_data,
            summary_stats=empty_stats,
            downloaded_at=datetime.now().isoformat()
        )
        stock_data.basic_info = basic_info  # 添加基本信息
        
        return self._storage.store_stock_data(symbol, stock_data)
    
    def store_stock_prices(self, symbol: str, price_data: Union['PriceData', Dict], incremental: bool = True):
        """存储股票价格数据"""
        from .models import StockData, SummaryStats, calculate_summary_stats
        from datetime import datetime
        
        if isinstance(price_data, dict):
            from .models import PriceData
            price_data = PriceData.from_dict(price_data)
        
        # 计算统计数据
        summary_stats = calculate_summary_stats(price_data.close, price_data.volume)
        
        stock_data = StockData(
            symbol=symbol,
            start_date=price_data.dates[0] if price_data.dates else "",
            end_date=price_data.dates[-1] if price_data.dates else "",
            data_points=len(price_data.dates),
            price_data=price_data,
            summary_stats=summary_stats,
            downloaded_at=datetime.now().isoformat(),
            incremental_update=incremental
        )
        
        return self._storage.store_stock_data(symbol, stock_data)
    
    def store_financial_statements(self, symbol: str, financial_data: Union['FinancialData', Dict]):
        """存储财务报表数据"""
        return self._storage.store_financial_data(symbol, financial_data)
    
    def store_download_log(self, symbol: str, download_type: str, status: str, 
                          data_points: int = 0, error_message: str = None):
        """存储下载日志 (已弃用，存储层会自动记录)"""
        warnings.warn(
            "store_download_log 已弃用，存储层会自动记录下载日志",
            DeprecationWarning,
            stacklevel=2
        )
        # 这个功能现在由存储层自动处理，所以这里只是一个空操作
        pass
    
    def store_data_quality(self, symbol: str, quality_data: Union['DataQuality', Dict]):
        """存储数据质量评估"""
        return self._storage.store_data_quality(symbol, quality_data)
    
    def store_comprehensive_data(self, symbol: str, data: Union['ComprehensiveData', Dict]):
        """存储综合数据"""
        if isinstance(data, ComprehensiveData):
            success = True
            if data.stock_data:
                success &= self._storage.store_stock_data(symbol, data.stock_data)
            if data.financial_data:
                success &= self._storage.store_financial_data(symbol, data.financial_data)
            success &= self._storage.store_data_quality(symbol, data.data_quality)
            return success
        else:
            # 处理字典格式
            success = True
            if 'stock_data' in data and 'error' not in data['stock_data']:
                success &= self._storage.store_stock_data(symbol, data['stock_data'])
            if 'financial_data' in data and 'error' not in data['financial_data']:
                success &= self._storage.store_financial_data(symbol, data['financial_data'])
            if 'data_quality' in data:
                success &= self._storage.store_data_quality(symbol, data['data_quality'])
            return success
    
    def get_stock_prices(self, symbol: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """获取股票价格数据"""
        stock_data = self._storage.get_stock_data(symbol, start_date, end_date)
        if not stock_data:
            return pd.DataFrame()
        
        # 转换为 DataFrame 格式
        return pd.DataFrame({
            'date': stock_data.price_data.dates,
            'open': stock_data.price_data.open,
            'high': stock_data.price_data.high,
            'low': stock_data.price_data.low,
            'close': stock_data.price_data.close,
            'volume': stock_data.price_data.volume,
            'adj_close': stock_data.price_data.adj_close
        })
    
    def get_financial_data(self, symbol: str, statement_type: str = None) -> pd.DataFrame:
        """获取财务数据"""
        financial_data = self._storage.get_financial_data(symbol)
        if not financial_data:
            return pd.DataFrame()
        
        # 如果指定了报表类型
        if statement_type:
            statement = financial_data.financial_statements.get(statement_type)
            if not statement:
                return pd.DataFrame()
            
            # 转换为 DataFrame
            df_data = {'period': statement.periods}
            for item_name, values in statement.items.items():
                df_data[item_name] = values
            
            return pd.DataFrame(df_data)
        
        # 返回所有报表的汇总信息
        data_rows = []
        for stmt_type, statement in financial_data.financial_statements.items():
            for i, period in enumerate(statement.periods):
                row = {'statement_type': stmt_type, 'period': period}
                for item_name, values in statement.items.items():
                    if i < len(values):
                        row[item_name] = values[i]
                data_rows.append(row)
        
        return pd.DataFrame(data_rows)
    
    def get_data_quality_report(self) -> pd.DataFrame:
        """获取数据质量报告 (简化版本)"""
        warnings.warn(
            "get_data_quality_report 功能有限，建议直接使用存储层",
            DeprecationWarning,
            stacklevel=2
        )
        return pd.DataFrame()  # 返回空 DataFrame
    
    def get_download_summary(self) -> pd.DataFrame:
        """获取下载摘要 (简化版本)"""
        warnings.warn(
            "get_download_summary 功能有限，建议直接使用存储层",
            DeprecationWarning,
            stacklevel=2
        )
        return pd.DataFrame()  # 返回空 DataFrame
    
    def get_existing_symbols(self) -> List[str]:
        """获取已存储的股票代码列表"""
        return self._storage.get_existing_symbols()
    
    def get_last_update_date(self, symbol: str) -> Optional[str]:
        """获取最后更新日期"""
        return self._storage.get_last_update_date(symbol)
    
    def backup_database(self, backup_path: str):
        """备份数据库 (简化版本)"""
        warnings.warn(
            "backup_database 功能有限，请手动备份数据库文件",
            DeprecationWarning,
            stacklevel=2
        )
        if hasattr(self._storage, 'db_path'):
            import shutil
            shutil.copy(self._storage.db_path, backup_path)
    
    def close(self):
        """关闭数据库连接"""
        self._storage.close()
    
    # 为了兼容性，添加一些属性
    @property
    def connection(self):
        """数据库连接（仅用于兼容性）"""
        if hasattr(self._storage, 'connection'):
            return self._storage.connection
        return None
    
    @property
    def cursor(self):
        """数据库游标（仅用于兼容性）"""
        if hasattr(self._storage, 'cursor'):
            return self._storage.cursor
        return None