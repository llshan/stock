#!/usr/bin/env python3
"""
配置管理模块
统一管理所有硬编码的参数和设置
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Any
import os
import logging


@dataclass
class TechnicalAnalysisConfig:
    """技术分析配置"""
    # RSI指标配置
    rsi_period: int = 14
    rsi_overbought: float = 70.0
    rsi_oversold: float = 30.0
    
    # 移动平均线配置
    ma_windows: List[int] = field(default_factory=lambda: [5, 10, 20, 50])
    
    # 布林带配置
    bb_period: int = 20
    bb_std: float = 2.0
    
    # MACD配置
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9


@dataclass
class FinancialAnalysisConfig:
    """财务分析配置"""
    # 财务健康度评分权重
    profitability_weight: int = 30
    liquidity_weight: int = 20
    leverage_weight: int = 25
    efficiency_weight: int = 25
    
    # 财务比率阈值
    debt_ratio_good: float = 30.0    # 负债率良好阈值
    debt_ratio_warning: float = 70.0  # 负债率警告阈值
    pe_ratio_high: float = 30.0      # PE比率过高阈值
    
    # 评分阈值
    excellent_score: int = 80
    good_score: int = 60


@dataclass  
class ChartConfig:
    """图表配置"""
    # matplotlib样式
    plt_style: str = 'seaborn-v0_8'
    plt_fallback_style: str = 'seaborn'
    
    # 图表尺寸
    default_figsize: Tuple[int, int] = (12, 8)
    financial_figsize: Tuple[int, int] = (15, 10)
    rsi_figsize: Tuple[int, int] = (12, 8)
    
    # DPI设置
    save_dpi: int = 300
    
    # 颜色配置
    colors: Dict[str, str] = field(default_factory=lambda: {
        'primary': '#1f77b4',
        'secondary': '#ff7f0e', 
        'success': '#2ca02c',
        'danger': '#d62728',
        'warning': '#ff7f0e',
        'info': '#17a2b8',
        'up_color': 'green',
        'down_color': 'red',
        'neutral_color': 'gray'
    })
    
    # RSI图表特定配置
    rsi_overbought_color: str = 'red'
    rsi_oversold_color: str = 'green'
    rsi_neutral_alpha: float = 0.1
    rsi_line_alpha: float = 0.7
    
    # 子图高度比例
    candlestick_height_ratios: List[int] = field(default_factory=lambda: [3, 1])


@dataclass
class PipelineConfig:
    """分析流水线配置"""
    enabled_operators: List[str] = field(default_factory=lambda: [
        'ma', 'rsi', 'drop_alert'
    ])
    # 跌幅预警参数
    drop_alert_days: int = 1
    drop_alert_threshold: float = 15.0
    drop_alert_7d_threshold: float = 20.0


@dataclass
class DataFetchConfig:
    """数据获取配置"""
    # API请求限制
    rate_limit_delay: float = 1.0
    max_retries: int = 3
    retry_delay_base: int = 2
    
    # 默认时间周期
    default_period: str = "1y"
    default_interval: str = "1d"
    realtime_period: str = "1d"
    realtime_interval: str = "5m"
    
    # 数据范围
    default_start_date: str = "2020-01-01"


@dataclass
class ApplicationConfig:
    """应用程序配置"""
    # 输出目录
    results_dir: str = "result"
    charts_dir: str = "result"
    
    # 日志配置
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # 并发配置
    max_concurrent_downloads: int = 5
    
    # 缓存配置
    enable_cache: bool = True
    cache_expire_hours: int = 24


@dataclass
class Config:
    """主配置类，包含所有子配置"""
    technical: TechnicalAnalysisConfig = field(default_factory=TechnicalAnalysisConfig)
    financial: FinancialAnalysisConfig = field(default_factory=FinancialAnalysisConfig) 
    chart: ChartConfig = field(default_factory=ChartConfig)
    data: DataFetchConfig = field(default_factory=DataFetchConfig)
    app: ApplicationConfig = field(default_factory=ApplicationConfig)
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'Config':
        """从字典创建配置对象"""
        return cls(
            technical=TechnicalAnalysisConfig(**config_dict.get('technical', {})),
            financial=FinancialAnalysisConfig(**config_dict.get('financial', {})),
            chart=ChartConfig(**config_dict.get('chart', {})),
            data=DataFetchConfig(**config_dict.get('data', {})),
            app=ApplicationConfig(**config_dict.get('app', {})),
            pipeline=PipelineConfig(**config_dict.get('pipeline', {}))
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'technical': self.technical.__dict__,
            'financial': self.financial.__dict__,
            'chart': self.chart.__dict__,
            'data': self.data.__dict__,
            'app': self.app.__dict__,
            'pipeline': self.pipeline.__dict__
        }
    
    def ensure_directories(self):
        """确保必需的目录存在"""
        os.makedirs(self.app.results_dir, exist_ok=True)
        os.makedirs(self.app.charts_dir, exist_ok=True)


# 创建全局默认配置实例
default_config = Config()


def get_config() -> Config:
    """获取全局配置实例"""
    return default_config


def set_config(new_config: Config):
    """设置新的全局配置"""
    global default_config
    default_config = new_config


def load_config_from_file(filepath: str) -> Config:
    """从文件加载配置"""
    try:
        import json
        with open(filepath, 'r', encoding='utf-8') as f:
            config_dict = json.load(f)
        return Config.from_dict(config_dict)
    except Exception as e:
        logging.getLogger(__name__).warning(f"加载配置文件失败: {e}, 使用默认配置")
        return Config()


def save_config_to_file(config: Config, filepath: str):
    """保存配置到文件"""
    try:
        import json
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)
        logging.getLogger(__name__).info(f"配置已保存到: {filepath}")
    except Exception as e:
        logging.getLogger(__name__).error(f"保存配置文件失败: {e}")


# 环境变量配置覆盖
def load_env_overrides():
    """从环境变量加载配置覆盖"""
    config = get_config()
    
    # 技术分析配置
    if rsi_overbought := os.getenv('RSI_OVERBOUGHT'):
        config.technical.rsi_overbought = float(rsi_overbought)
    if rsi_oversold := os.getenv('RSI_OVERSOLD'):
        config.technical.rsi_oversold = float(rsi_oversold)
    
    # 数据获取配置  
    if rate_limit := os.getenv('RATE_LIMIT_DELAY'):
        config.data.rate_limit_delay = float(rate_limit)
    if max_retries := os.getenv('MAX_RETRIES'):
        config.data.max_retries = int(max_retries)
    
    # 应用配置
    if results_dir := os.getenv('RESULTS_DIR'):
        config.app.results_dir = results_dir
    if log_level := os.getenv('LOG_LEVEL'):
        config.app.log_level = log_level
    
    set_config(config)


# 注意：不在导入时自动加载环境变量覆盖，
# 由应用入口或显式初始化流程调用。
