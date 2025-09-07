#!/usr/bin/env python3
"""
股票数据模型
使用dataclass定义数据结构，提供类型安全和结构化的数据处理
"""

from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Any
from datetime import datetime


@dataclass
class PriceData:
    """股票价格数据模型"""
    dates: List[str]
    open: List[float]
    high: List[float]
    low: List[float]
    close: List[float]
    volume: List[int]
    adj_close: List[float]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PriceData':
        """从字典创建实例"""
        return cls(**data)


@dataclass
class SummaryStats:
    """价格数据统计信息模型"""
    min_price: float
    max_price: float
    avg_price: float
    total_volume: int
    avg_volume: int
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SummaryStats':
        """从字典创建实例"""
        return cls(**data)


@dataclass
class BasicInfo:
    """股票基本信息模型"""
    company_name: str = ""
    sector: str = ""
    industry: str = ""
    market_cap: int = 0
    employees: int = 0
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BasicInfo':
        """从字典创建实例"""
        return cls(**data)


@dataclass
class FinancialStatement:
    """财务报表数据模型"""
    statement_type: str
    periods: List[str]
    items: Dict[str, List[Optional[float]]]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FinancialStatement':
        """从字典创建实例"""
        return cls(**data)


@dataclass
class FinancialData:
    """完整财务数据模型"""
    symbol: str
    basic_info: BasicInfo
    financial_statements: Dict[str, FinancialStatement]
    downloaded_at: str
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            'symbol': self.symbol,
            'basic_info': self.basic_info.to_dict(),
            'financial_statements': {},
            'downloaded_at': self.downloaded_at
        }
        
        for key, statement in self.financial_statements.items():
            result['financial_statements'][key] = statement.to_dict()
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FinancialData':
        """从字典创建实例"""
        basic_info = BasicInfo.from_dict(data.get('basic_info', {}))
        statements = {}
        
        for key, stmt_data in data.get('financial_statements', {}).items():
            if 'error' not in stmt_data:
                statements[key] = FinancialStatement.from_dict(stmt_data)
        
        return cls(
            symbol=data['symbol'],
            basic_info=basic_info,
            financial_statements=statements,
            downloaded_at=data['downloaded_at']
        )


@dataclass
class DataQuality:
    """数据质量评估模型"""
    stock_data_available: bool
    financial_data_available: bool
    data_completeness: float
    quality_grade: str
    issues: List[str] = field(default_factory=list)
    stock_data_completeness: Optional[float] = None
    financial_statements_count: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DataQuality':
        """从字典创建实例"""
        return cls(**data)


@dataclass
class StockData:
    """股票数据模型"""
    symbol: str
    start_date: str
    end_date: str
    data_points: int
    price_data: PriceData
    summary_stats: SummaryStats
    downloaded_at: str
    data_source: str = "yfinance"
    incremental_update: bool = False
    no_new_data: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'symbol': self.symbol,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'data_points': self.data_points,
            'price_data': self.price_data.to_dict(),
            'summary_stats': self.summary_stats.to_dict(),
            'downloaded_at': self.downloaded_at,
            'data_source': self.data_source,
            'incremental_update': self.incremental_update,
            'no_new_data': self.no_new_data
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StockData':
        """从字典创建实例"""
        return cls(
            symbol=data['symbol'],
            start_date=data['start_date'],
            end_date=data['end_date'],
            data_points=data['data_points'],
            price_data=PriceData.from_dict(data['price_data']),
            summary_stats=SummaryStats.from_dict(data['summary_stats']),
            downloaded_at=data['downloaded_at'],
            data_source=data.get('data_source', 'yfinance'),
            incremental_update=data.get('incremental_update', False),
            no_new_data=data.get('no_new_data', False)
        )


@dataclass
class ComprehensiveData:
    """综合股票数据模型（价格 + 财务）"""
    symbol: str
    download_timestamp: str
    stock_data: Optional[StockData]
    financial_data: Optional[FinancialData]
    data_quality: DataQuality
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            'symbol': self.symbol,
            'download_timestamp': self.download_timestamp,
            'data_quality': self.data_quality.to_dict()
        }
        
        if self.stock_data:
            result['stock_data'] = self.stock_data.to_dict()
        else:
            result['stock_data'] = {'error': 'Stock data not available'}
        
        if self.financial_data:
            result['financial_data'] = self.financial_data.to_dict()
        else:
            result['financial_data'] = {'error': 'Financial data not available'}
        
        if self.error:
            result['error'] = self.error
            
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ComprehensiveData':
        """从字典创建实例"""
        stock_data = None
        financial_data = None
        
        if 'stock_data' in data and 'error' not in data['stock_data']:
            stock_data = StockData.from_dict(data['stock_data'])
        
        if 'financial_data' in data and 'error' not in data['financial_data']:
            financial_data = FinancialData.from_dict(data['financial_data'])
        
        return cls(
            symbol=data['symbol'],
            download_timestamp=data['download_timestamp'],
            stock_data=stock_data,
            financial_data=financial_data,
            data_quality=DataQuality.from_dict(data['data_quality']),
            error=data.get('error')
        )


@dataclass
class DownloadError:
    """下载错误模型"""
    symbol: str
    error_message: str
    error_type: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DownloadError':
        """从字典创建实例"""
        return cls(**data)


# 工具函数
def create_empty_stock_data(symbol: str, start_date: str, end_date: str, error_msg: str) -> Dict[str, Any]:
    """创建包含错误信息的空股票数据"""
    return {
        'symbol': symbol,
        'start_date': start_date,
        'end_date': end_date,
        'data_points': 0,
        'price_data': {
            'dates': [], 'open': [], 'high': [], 'low': [], 
            'close': [], 'volume': [], 'adj_close': []
        },
        'summary_stats': {
            'min_price': 0.0, 'max_price': 0.0, 'avg_price': 0.0,
            'total_volume': 0, 'avg_volume': 0
        },
        'downloaded_at': datetime.now().isoformat(),
        'error': error_msg
    }


def create_empty_financial_data(symbol: str, error_msg: str) -> Dict[str, Any]:
    """创建包含错误信息的空财务数据"""
    return {
        'symbol': symbol,
        'basic_info': {
            'company_name': '', 'sector': '', 'industry': '',
            'market_cap': 0, 'employees': 0, 'description': ''
        },
        'financial_statements': {},
        'downloaded_at': datetime.now().isoformat(),
        'error': error_msg
    }