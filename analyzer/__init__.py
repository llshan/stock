"""
股票分析模块包
包含技术分析、财务分析、综合分析、数据获取和可视化等功能模块
"""

# 综合分析器（基于流水线）
from .comprehensive_analyzer import ComprehensiveStockAnalyzer

# 新的DB仓储 + operator 流水线
from .data.market_repository import MarketDataRepository, DatabaseMarketDataRepository, TimeRange
from .data.financial_repository import FinancialRepository
from .operators.base import Operator
from .operators.ma import MovingAverageOperator
from .operators.rsi import RSIOperator
from .operators.drop_alert import DropAlertOperator
from .operators.fin_ratios import FinancialRatioOperator
from .operators.fin_health import FinancialHealthOperator
from .pipeline.engine import PipelineEngine
from .pipeline.context import AnalysisContext
from .app.runner import run_analysis_for_symbols, build_operators

# 配置管理
from .config import (
    Config,
    TechnicalAnalysisConfig,
    FinancialAnalysisConfig, 
    ChartConfig,
    DataFetchConfig,
    ApplicationConfig,
    get_config,
    set_config,
    load_config_from_file,
    save_config_to_file,
    load_env_overrides
)

__all__ = [
    # 综合分析器
    'ComprehensiveStockAnalyzer',
    
    # 数据仓储 + 流水线
    'MarketDataRepository',
    'DatabaseMarketDataRepository',
    'FinancialRepository',
    'TimeRange',
    'Operator',
    'MovingAverageOperator',
    'RSIOperator',
    'DropAlertOperator',
    'FinancialRatioOperator',
    'FinancialHealthOperator',
    'PipelineEngine',
    'AnalysisContext',
    'run_analysis_for_symbols',
    'build_operators',
    
    # 配置管理
    'Config',
    'TechnicalAnalysisConfig',
    'FinancialAnalysisConfig',
    'ChartConfig',
    'DataFetchConfig', 
    'ApplicationConfig',
    'get_config',
    'set_config',
    'load_config_from_file',
    'save_config_to_file'
]

# 版本信息
__version__ = '2.0.0'
__author__ = 'Stock Analysis Team'
__description__ = '股票技术分析和财务分析工具包'

# 模块级文档
def get_module_info():
    """获取模块信息"""
    return {
        'name': __name__,
        'version': __version__,
        'author': __author__,
        'description': __description__,
        'modules': {
            'stock_analyzer': '技术分析模块 - RSI, 移动平均, 布林带等指标',
            'comprehensive_analyzer': '综合分析模块 - 基于数据库与可插拔Operators',
            'data': '数据仓储模块（行情/财务）',
            'operators': '可插拔分析算子（技术/财务/风险）',
            'pipeline': '流水线引擎与上下文',
            'config': '配置管理模块 - 参数配置和环境管理'
        },
        'features': [
            '技术指标分析 (RSI, MACD, 布林带等)',
            '财务指标分析 (ROE, 负债率, PE等)',
            '多数据源支持 (Yahoo Finance, Stooq等)',
            '灵活的配置管理',
            '丰富的图表生成'
        ]
    }

# 建议直接使用 run_analysis_for_symbols 或 ComprehensiveStockAnalyzer
