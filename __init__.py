"""
Stock Analysis Toolkit
股票数据分析工具包

提供股票数据下载、存储、分析和可视化功能。
"""

from . import data_service
from . import analysis_service

# 导入核心类
from .data_service import (
    YFinanceDataDownloader,
    StooqDataDownloader,
    StockDatabase,
    DataService
)

from .analysis_service import (
    StockAnalyzer,
    FinancialAnalyzer,
    AnalysisService
)

__version__ = "1.0.0"
__author__ = "Stock Analysis Team"
__description__ = "Stock data download and analysis toolkit"

__all__ = [
    # 数据服务
    'YFinanceDataDownloader',
    'StooqDataDownloader',
    'StockDatabase',
    'DataService',
    
    # 分析器
    'StockAnalyzer',
    'FinancialAnalyzer', 
    'AnalysisService',
    
    # 模块
    'data_service',
    'analysis_service'
]

def get_version():
    """获取版本信息"""
    return __version__

def get_info():
    """获取包信息"""
    return {
        'name': 'Stock Analysis Toolkit',
        'version': __version__,
        'author': __author__,
        'description': __description__,
        'modules': {
            'data_service': '数据下载和存储服务',
            'analysis_service': '股票分析模块（流水线 + 算子）'
        }
    }
