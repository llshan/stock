"""
股票分析模块包
包含技术分析、财务分析、综合分析、数据获取和可视化等功能模块
"""

# 核心分析器
from .stock_analyzer import StockAnalyzer, StockDataFetcher, ChartGenerator, StockAnalysisApp
from .financial_analyzer import FinancialAnalyzer, FinancialDataFetcher, FinancialChartGenerator  
from .comprehensive_analyzer import ComprehensiveStockAnalyzer

# 数据获取模块
from .data_fetcher import YFinanceDataFetcher, get_data_fetcher

# 图表生成模块
from .chart_generator import (
    UnifiedChartGenerator, 
    CandlestickChartGenerator,
    RSIChartGenerator,
    BollingerBandsChartGenerator,
    FinancialMetricsChartGenerator,
    get_chart_generator
)

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
    save_config_to_file
)

__all__ = [
    # 核心分析器
    'StockAnalyzer',
    'StockDataFetcher',
    'ChartGenerator', 
    'StockAnalysisApp',
    'FinancialAnalyzer',
    'FinancialDataFetcher',
    'FinancialChartGenerator',
    'ComprehensiveStockAnalyzer',
    
    # 数据获取
    'YFinanceDataFetcher',
    'get_data_fetcher',
    
    # 图表生成
    'UnifiedChartGenerator',
    'CandlestickChartGenerator',
    'RSIChartGenerator', 
    'BollingerBandsChartGenerator',
    'FinancialMetricsChartGenerator',
    'get_chart_generator',
    
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
            'financial_analyzer': '财务分析模块 - 财务比率, 健康度评分等',
            'comprehensive_analyzer': '综合分析模块 - 整合技术和财务分析',
            'data_fetcher': '统一数据获取模块 - 支持多数据源',
            'chart_generator': '图表生成模块 - K线图, 指标图等',
            'config': '配置管理模块 - 参数配置和环境管理'
        },
        'features': [
            '技术指标分析 (RSI, MACD, 布林带等)',
            '财务指标分析 (ROE, 负债率, PE等)',
            '多数据源支持 (Yahoo Finance, Stooq等)',
            '灵活的配置管理',
            '丰富的图表生成',
            '向后兼容性保证'
        ]
    }


# 便捷函数
def create_analyzer(config_file: str = None):
    """
    创建完整的股票分析器实例
    
    Args:
        config_file: 可选的配置文件路径
        
    Returns:
        ComprehensiveStockAnalyzer实例
    """
    if config_file:
        config = load_config_from_file(config_file)
        set_config(config)
    
    return ComprehensiveStockAnalyzer()


def quick_analyze(symbol: str, period: str = '1y', save_charts: bool = True):
    """
    快速分析单个股票
    
    Args:
        symbol: 股票代码
        period: 分析周期
        save_charts: 是否保存图表
        
    Returns:
        分析结果字典
    """
    analyzer = create_analyzer()
    config = get_config()
    
    if save_charts:
        config.app.ensure_directories()
    
    # 执行综合分析
    result = analyzer.comprehensive_analyze(symbol, period)
    
    return result