#!/usr/bin/env python3
"""
数据服务配置管理

职责：
- 统一管理下载器、数据库、批量处理、数据质量与日志等配置项
- 从环境变量/字典加载配置，提供便捷的默认值

说明：
- 仅包含纯配置与序列化逻辑，不包含 I/O 与业务流程
"""

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DownloaderConfig:
    """下载器配置"""

    max_retries: int = 3
    base_delay: int = 30
    timeout: int = 120
    rate_limit_delay: float = 1.0
    # 财务刷新阈值（天）：距离最近财报期超过该天数则重新抓取财务
    financial_refresh_days: int = 90
    # 股票增量更新阈值（天）：距离最新股票数据超过该天数则使用批量下载而非增量
    stock_incremental_threshold_days: int = 100
    # 财务数据下载器：目前仅支持 'finnhub'
    financial_downloader: str = 'finnhub'


@dataclass
class DatabaseConfig:
    """数据库配置"""

    db_path: str = "database/stock_data.db"
    db_type: str = "sqlite"
    connection_timeout: int = 30
    max_connections: int = 10
    enable_foreign_keys: bool = True


@dataclass
class BatchConfig:
    """批量操作配置"""

    batch_size: int = 100
    delay_between_requests: int = 2
    max_concurrent_downloads: int = 5
    enable_progress_logging: bool = True


@dataclass
class DataQualityConfig:
    """数据质量配置"""

    min_data_points: int = 100
    max_missing_days: int = 30
    enable_quality_checks: bool = True
    quality_thresholds: Dict[str, float] = field(
        default_factory=lambda: {
            'completeness': 0.8,
            'freshness_days': 7,
            'consistency': 0.9,
        }
    )


@dataclass
class DataServiceConfig:
    """数据服务主配置"""

    # 基础配置
    default_start_date: str = "2000-01-01"
    default_data_source: str = "stooq"  # 统一使用 stooq 进行价格数据下载

    # 子配置
    downloader: DownloaderConfig = field(default_factory=DownloaderConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    batch: BatchConfig = field(default_factory=BatchConfig)
    quality: DataQualityConfig = field(default_factory=DataQualityConfig)

    # 日志配置
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    enable_file_logging: bool = False
    log_file_path: str = "data_service.log"

    @classmethod
    def from_env(cls, db_path: Optional[str] = None) -> 'DataServiceConfig':
        """
        从环境变量创建配置

        Args:
            db_path: 数据库路径，如果提供将覆盖环境变量

        Returns:
            配置实例
        """
        config = cls()

        # 数据库配置
        if db_path:
            config.database.db_path = db_path
        else:
            config.database.db_path = os.getenv('DATA_SERVICE_DB_PATH', config.database.db_path)

        config.database.db_type = os.getenv('DATA_SERVICE_DB_TYPE', config.database.db_type)

        # 下载器配置
        config.downloader.max_retries = int(
            os.getenv('DATA_SERVICE_MAX_RETRIES', config.downloader.max_retries)
        )
        config.downloader.base_delay = int(
            os.getenv('DATA_SERVICE_BASE_DELAY', config.downloader.base_delay)
        )
        config.downloader.timeout = int(
            os.getenv('DATA_SERVICE_TIMEOUT', config.downloader.timeout)
        )
        config.downloader.financial_downloader = os.getenv(
            'DATA_SERVICE_FINANCIAL_DOWNLOADER', config.downloader.financial_downloader
        )
        config.downloader.stock_incremental_threshold_days = int(
            os.getenv('DATA_SERVICE_STOCK_INCREMENTAL_THRESHOLD_DAYS', config.downloader.stock_incremental_threshold_days)
        )

        # 批量配置
        config.batch.batch_size = int(os.getenv('DATA_SERVICE_BATCH_SIZE', config.batch.batch_size))
        config.batch.delay_between_requests = int(
            os.getenv('DATA_SERVICE_BATCH_DELAY', config.batch.delay_between_requests)
        )

        # 日志配置
        config.log_level = os.getenv('DATA_SERVICE_LOG_LEVEL', config.log_level)
        config.enable_file_logging = (
            os.getenv('DATA_SERVICE_ENABLE_FILE_LOG', 'false').lower() == 'true'
        )
        config.log_file_path = os.getenv('DATA_SERVICE_LOG_FILE', config.log_file_path)

        # 默认开始日期
        config.default_start_date = os.getenv(
            'DATA_SERVICE_DEFAULT_START_DATE', config.default_start_date
        )
        config.default_data_source = os.getenv(
            'DATA_SERVICE_DEFAULT_SOURCE', config.default_data_source
        )

        return config

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'DataServiceConfig':
        """
        从字典创建配置

        Args:
            config_dict: 配置字典

        Returns:
            配置实例
        """
        config = cls()

        # 基础配置
        if 'default_start_date' in config_dict:
            config.default_start_date = config_dict['default_start_date']
        if 'default_data_source' in config_dict:
            config.default_data_source = config_dict['default_data_source']

        # 下载器配置
        if 'downloader' in config_dict:
            downloader_dict = config_dict['downloader']
            for key, value in downloader_dict.items():
                if hasattr(config.downloader, key):
                    setattr(config.downloader, key, value)

        # 数据库配置
        if 'database' in config_dict:
            database_dict = config_dict['database']
            for key, value in database_dict.items():
                if hasattr(config.database, key):
                    setattr(config.database, key, value)

        # 批量配置
        if 'batch' in config_dict:
            batch_dict = config_dict['batch']
            for key, value in batch_dict.items():
                if hasattr(config.batch, key):
                    setattr(config.batch, key, value)

        # 数据质量配置
        if 'quality' in config_dict:
            quality_dict = config_dict['quality']
            for key, value in quality_dict.items():
                if hasattr(config.quality, key):
                    setattr(config.quality, key, value)

        # 日志配置
        for key in [
            'log_level',
            'log_format',
            'enable_file_logging',
            'log_file_path',
        ]:
            if key in config_dict:
                setattr(config, key, config_dict[key])

        return config

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'default_start_date': self.default_start_date,
            'default_data_source': self.default_data_source,
            'downloader': {
                'max_retries': self.downloader.max_retries,
                'base_delay': self.downloader.base_delay,
                'timeout': self.downloader.timeout,
                'rate_limit_delay': self.downloader.rate_limit_delay,
            },
            'database': {
                'db_path': self.database.db_path,
                'db_type': self.database.db_type,
                'connection_timeout': self.database.connection_timeout,
                'max_connections': self.database.max_connections,
                'enable_foreign_keys': self.database.enable_foreign_keys,
            },
            'batch': {
                'batch_size': self.batch.batch_size,
                'delay_between_requests': self.batch.delay_between_requests,
                'max_concurrent_downloads': self.batch.max_concurrent_downloads,
                'enable_progress_logging': self.batch.enable_progress_logging,
            },
            'quality': {
                'min_data_points': self.quality.min_data_points,
                'max_missing_days': self.quality.max_missing_days,
                'enable_quality_checks': self.quality.enable_quality_checks,
                'quality_thresholds': self.quality.quality_thresholds.copy(),
            },
            'log_level': self.log_level,
            'log_format': self.log_format,
            'enable_file_logging': self.enable_file_logging,
            'log_file_path': self.log_file_path,
        }

    def update(self, **kwargs: Any) -> 'DataServiceConfig':
        """
        更新配置参数

        Args:
            **kwargs: 要更新的配置参数

        Returns:
            更新后的配置实例
        """
        # 支持直接更新下载器参数
        downloader_keys = [
            'max_retries',
            'base_delay',
            'timeout',
            'rate_limit_delay',
        ]
        for key in downloader_keys:
            if key in kwargs:
                setattr(self.downloader, key, kwargs.pop(key))

        # 支持直接更新数据库参数
        database_keys = [
            'db_path',
            'db_type',
            'connection_timeout',
            'max_connections',
            'enable_foreign_keys',
        ]
        for key in database_keys:
            if key in kwargs:
                setattr(self.database, key, kwargs.pop(key))

        # 支持直接更新批量参数
        batch_keys = [
            'batch_size',
            'delay_between_requests',
            'max_concurrent_downloads',
            'enable_progress_logging',
        ]
        for key in batch_keys:
            if key in kwargs:
                setattr(self.batch, key, kwargs.pop(key))

        # 更新剩余的顶级参数
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

        return self


# 预定义配置模板
DEFAULT_CONFIG = DataServiceConfig()

DEVELOPMENT_CONFIG = DataServiceConfig(
    log_level="DEBUG",
    enable_file_logging=True,
    downloader=DownloaderConfig(max_retries=2, base_delay=10),
    batch=BatchConfig(delay_between_requests=1, enable_progress_logging=True),
)

PRODUCTION_CONFIG = DataServiceConfig(
    log_level="WARNING",
    enable_file_logging=True,
    downloader=DownloaderConfig(max_retries=5, base_delay=60),
    batch=BatchConfig(delay_between_requests=5, enable_progress_logging=False),
    quality=DataQualityConfig(enable_quality_checks=True),
)

TESTING_CONFIG = DataServiceConfig(
    database=DatabaseConfig(db_path=":memory:", db_type="sqlite"),
    downloader=DownloaderConfig(max_retries=1, base_delay=0),
    batch=BatchConfig(delay_between_requests=0, enable_progress_logging=False),
    quality=DataQualityConfig(enable_quality_checks=False),
)


def get_config(config_name: str = "default") -> DataServiceConfig:
    """
    获取预定义配置

    Args:
        config_name: 配置名称 ('default', 'development', 'production', 'testing')

    Returns:
        配置实例
    """
    configs = {
        'default': DEFAULT_CONFIG,
        'development': DEVELOPMENT_CONFIG,
        'production': PRODUCTION_CONFIG,
        'testing': TESTING_CONFIG,
    }

    return configs.get(config_name, DEFAULT_CONFIG)


def create_config(db_path: str = "database/stock_data.db", **kwargs: Any) -> DataServiceConfig:
    """
    创建自定义配置的便捷函数

    Args:
        db_path: 数据库路径
        **kwargs: 其他配置参数

    Returns:
        配置实例

    Example:
        >>> config = create_config("my_stocks.db", max_retries=5, log_level="DEBUG")
    """
    config = DataServiceConfig.from_env(db_path)
    config.update(**kwargs)
    return config


# 默认关注列表（用于示例/演示）
def get_default_watchlist() -> List[str]:
    """获取默认关注股票列表（可通过环境变量 WATCHLIST 覆盖，逗号分隔）"""
    env = os.getenv('WATCHLIST')
    if env:
        syms = [s.strip().upper() for s in env.split(',') if s.strip()]
        if syms:
            return syms
    return [
        'AAPL',  # Apple
        'GOOG',  # Google
        'LULU',  # Lululemon
    ]
