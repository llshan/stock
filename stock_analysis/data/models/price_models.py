#!/usr/bin/env python3
"""
价格相关数据模型
股票价格、交易量等市场数据的模型定义
"""

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base_models import SummaryStats, calculate_summary_stats


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

    def get_summary_stats(self) -> SummaryStats:
        """计算价格数据的统计信息"""
        return calculate_summary_stats(self.close, self.volume)

    def validate(self) -> List[str]:
        """验证数据完整性，返回问题列表"""
        issues = []

        # 检查列表长度一致性
        lengths = [
            len(self.dates),
            len(self.open),
            len(self.high),
            len(self.low),
            len(self.close),
            len(self.volume),
            len(self.adj_close),
        ]
        if len(set(lengths)) > 1:
            issues.append(
                f"数据长度不一致: {dict(zip(['dates', 'open', 'high', 'low', 'close', 'volume', 'adj_close'], lengths))}"
            )

        # 检查是否有数据
        if not self.dates:
            issues.append("没有价格数据")
            return issues

        # 检查价格逻辑性
        for i, (open_p, high_p, low_p, close_p) in enumerate(
            zip(self.open, self.high, self.low, self.close)
        ):
            if high_p < max(open_p, close_p):
                issues.append(f"第{i+1}天最高价低于开盘价或收盘价")
            if low_p > min(open_p, close_p):
                issues.append(f"第{i+1}天最低价高于开盘价或收盘价")
            if any(p <= 0 for p in [open_p, high_p, low_p, close_p]):
                issues.append(f"第{i+1}天存在非正价格")

        # 检查交易量
        if any(v < 0 for v in self.volume):
            issues.append("存在负交易量")

        return issues


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
            'no_new_data': self.no_new_data,
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
            no_new_data=data.get('no_new_data', False),
        )

    def validate(self) -> List[str]:
        """验证股票数据完整性"""
        issues = []

        # 验证基本信息
        if not self.symbol:
            issues.append("股票代码为空")

        if self.data_points < 0:
            issues.append("数据点数为负数")

        # 验证价格数据
        price_issues = self.price_data.validate()
        issues.extend(price_issues)

        # 验证数据点数一致性
        if self.price_data.dates and len(self.price_data.dates) != self.data_points:
            issues.append(
                f"数据点数不匹配: 声明{self.data_points}个，实际{len(self.price_data.dates)}个"
            )

        return issues

    def get_latest_price(self) -> Optional[float]:
        """获取最新价格"""
        if self.price_data.close:
            return self.price_data.close[-1]
        return None

    def get_price_change(self) -> Optional[float]:
        """获取最新价格变化（绝对值）"""
        if len(self.price_data.close) >= 2:
            return self.price_data.close[-1] - self.price_data.close[-2]
        return None

    def get_price_change_percent(self) -> Optional[float]:
        """获取最新价格变化百分比"""
        if len(self.price_data.close) >= 2:
            prev_price = self.price_data.close[-2]
            if prev_price != 0:
                change = self.price_data.close[-1] - prev_price
                return (change / prev_price) * 100
        return None


# 工具函数
def create_empty_price_data() -> PriceData:
    """创建空的价格数据"""
    return PriceData(dates=[], open=[], high=[], low=[], close=[], volume=[], adj_close=[])


def create_empty_stock_data(
    symbol: str, start_date: str, end_date: str, error_msg: Optional[str] = None
) -> Dict[str, Any]:
    """创建包含错误信息的空股票数据"""
    return {
        'symbol': symbol,
        'start_date': start_date,
        'end_date': end_date,
        'data_points': 0,
        'price_data': create_empty_price_data().to_dict(),
        'summary_stats': SummaryStats(0, 0, 0, 0, 0).to_dict(),
        'downloaded_at': datetime.now().isoformat(),
        'data_source': 'unknown',
        'incremental_update': False,
        'no_new_data': False,
        'error': error_msg or '数据不可用',
    }


def merge_price_data(old_data: PriceData, new_data: PriceData) -> PriceData:
    """
    合并两个价格数据（用于增量更新）

    Args:
        old_data: 原有数据
        new_data: 新数据

    Returns:
        合并后的价格数据
    """
    # 简单合并：将新数据追加到旧数据后面
    return PriceData(
        dates=old_data.dates + new_data.dates,
        open=old_data.open + new_data.open,
        high=old_data.high + new_data.high,
        low=old_data.low + new_data.low,
        close=old_data.close + new_data.close,
        volume=old_data.volume + new_data.volume,
        adj_close=old_data.adj_close + new_data.adj_close,
    )
