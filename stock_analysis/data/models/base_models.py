#!/usr/bin/env python3
"""
基础模型模块
定义所有数据模型的基础类和公共工具函数
"""

import re
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


class BaseDataModel(ABC):
    """所有数据模型的基础抽象类"""

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""

    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseDataModel':
        """从字典创建实例"""


@dataclass
class SummaryStats:
    """统计数据模型"""

    mean_price: float
    std_price: float
    min_price: float
    max_price: float
    total_volume: int

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

    company_name: str
    sector: str
    industry: str
    market_cap: int
    employees: int
    description: str

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BasicInfo':
        """从字典创建实例"""
        return cls(**data)

    def validate(self) -> List[str]:
        """验证基本信息完整性"""
        issues = []

        if not self.company_name:
            issues.append("公司名称为空")

        if self.market_cap < 0:
            issues.append("市值不能为负数")

        if self.employees < 0:
            issues.append("员工数不能为负数")

        return issues


@dataclass
class DownloadError:
    """下载错误信息模型"""

    symbol: str
    error_type: str
    error_message: str
    timestamp: str
    source: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DownloadError':
        """从字典创建实例"""
        return cls(**data)


# 工具函数
def create_timestamp() -> str:
    """创建当前时间戳"""
    return datetime.now().isoformat()


def validate_symbol(symbol: str) -> bool:
    """
    验证股票代码格式

    Args:
        symbol: 股票代码

    Returns:
        是否有效
    """
    if not symbol:
        return False

    # 基本格式检查：1-10个大写字母或数字
    pattern = r'^[A-Z0-9]{1,10}$'
    return bool(re.match(pattern, symbol.upper()))


def validate_date_string(date_string: str) -> bool:
    """
    验证日期字符串格式 (YYYY-MM-DD)

    Args:
        date_string: 日期字符串

    Returns:
        是否有效
    """
    if not date_string:
        return False

    try:
        datetime.strptime(date_string, '%Y-%m-%d')
        return True
    except ValueError:
        return False


def calculate_summary_stats(prices: List[float], volumes: List[int]) -> SummaryStats:
    """
    计算价格和交易量的统计数据

    Args:
        prices: 价格列表
        volumes: 交易量列表

    Returns:
        统计数据对象
    """
    if not prices:
        return SummaryStats(0.0, 0.0, 0.0, 0.0, 0)

    mean_price = sum(prices) / len(prices)

    # 计算标准差
    if len(prices) > 1:
        variance = sum((p - mean_price) ** 2 for p in prices) / (len(prices) - 1)
        std_price = variance**0.5
    else:
        std_price = 0.0

    min_price = min(prices)
    max_price = max(prices)
    total_volume = sum(volumes) if volumes else 0

    return SummaryStats(
        mean_price=mean_price,
        std_price=std_price,
        min_price=min_price,
        max_price=max_price,
        total_volume=total_volume,
    )
