#!/usr/bin/env python3
"""
交易模块配置
定义交易相关的配置选项和默认值
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional


class CostBasisMethod(Enum):
    """成本基础计算方法"""
    AVERAGE_COST = "average_cost"  # 平均成本法（当前实现）
    FIFO = "fifo"                 # 先进先出法（计划支持）
    LIFO = "lifo"                 # 后进先出法（计划支持）
    SPECIFIC_ID = "specific_id"   # 指定批次法（计划支持）


class PriceSource(Enum):
    """价格来源"""
    ADJ_CLOSE = "adj_close"       # 复权收盘价（默认）
    CLOSE = "close"               # 原始收盘价


class MissingPriceStrategy(Enum):
    """缺失价格处理策略"""
    BACKFILL = "backfill"         # 回填最近交易日价格（默认）
    STRICT_FAIL = "strict_fail"   # 严格模式：缺失则失败


@dataclass
class TradingConfig:
    """交易模块配置"""
    
    # 成本计算方法
    cost_basis_method: CostBasisMethod = CostBasisMethod.AVERAGE_COST
    
    # 价格来源配置
    price_source: PriceSource = PriceSource.ADJ_CLOSE
    missing_price_strategy: MissingPriceStrategy = MissingPriceStrategy.BACKFILL
    
    # 交易限制
    allow_short_selling: bool = False  # 是否允许做空
    allow_fractional_shares: bool = False  # 是否支持小数股
    
    # 计算配置
    only_trading_days: bool = False  # 是否只在交易日计算盈亏
    recompute_window_days: int = 7   # 重算窗口天数
    
    # 精度配置
    price_precision: int = 4         # 价格精度（小数位）
    amount_precision: int = 2        # 金额精度（小数位）
    
    # 输入校验限制配置
    max_user_id_length: int = 100    # 用户ID最大长度（放宽至100字符）
    max_symbol_length: int = 20      # 股票代码最大长度
    max_quantity_per_transaction: float = 10_000_000  # 单笔交易最大数量（1千万股）
    max_price_per_share: float = 1_000_000  # 单股最大价格（100万元/股）
    max_commission_rate: float = 0.1  # 佣金占交易金额的最大比例（10%）
    max_calculation_days: int = 10 * 365  # 最大计算时间跨度（10年）
    
    def __post_init__(self):
        """配置验证"""
        if self.recompute_window_days < 1:
            raise ValueError("重算窗口天数必须大于0")
        
        if self.price_precision < 0 or self.price_precision > 10:
            raise ValueError("价格精度必须在0-10之间")
        
        if self.amount_precision < 0 or self.amount_precision > 6:
            raise ValueError("金额精度必须在0-6之间")
    
    @classmethod
    def get_default(cls) -> 'TradingConfig':
        """获取默认配置"""
        return cls()
    
    def get_cost_basis_description(self) -> str:
        """获取成本法描述"""
        descriptions = {
            CostBasisMethod.AVERAGE_COST: (
                "平均成本法：所有买入的平均价格作为成本基础。"
                "卖出时按平均成本计算已实现盈亏。"
                "适用于长期投资，计算简单。"
            ),
            CostBasisMethod.FIFO: (
                "先进先出法：按买入时间顺序，先买入的先卖出。"
                "卖出时按最早买入批次的成本计算已实现盈亏。"
                "税务上常用，符合会计准则。"
            ),
            CostBasisMethod.LIFO: (
                "后进先出法：按买入时间倒序，后买入的先卖出。"
                "卖出时按最晚买入批次的成本计算已实现盈亏。"
                "某些税务环境下有优势。"
            ),
            CostBasisMethod.SPECIFIC_ID: (
                "指定批次法：手动指定卖出特定买入批次。"
                "最灵活的方法，可优化税务效果。"
                "需要详细记录和手动选择。"
            )
        }
        return descriptions.get(self.cost_basis_method, "未知成本法")
    
    def round_price(self, price: float) -> float:
        """根据配置的精度舍入价格"""
        return round(price, self.price_precision)
    
    def round_amount(self, amount: float) -> float:
        """根据配置的精度舍入金额"""
        return round(amount, self.amount_precision)
    
    def format_price(self, price: float) -> str:
        """格式化价格为字符串"""
        return f"{self.round_price(price):.{self.price_precision}f}"
    
    def format_amount(self, amount: float) -> str:
        """格式化金额为字符串"""
        return f"{self.round_amount(amount):.{self.amount_precision}f}"
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'cost_basis_method': self.cost_basis_method.value,
            'price_source': self.price_source.value,
            'missing_price_strategy': self.missing_price_strategy.value,
            'allow_short_selling': self.allow_short_selling,
            'allow_fractional_shares': self.allow_fractional_shares,
            'only_trading_days': self.only_trading_days,
            'recompute_window_days': self.recompute_window_days,
            'price_precision': self.price_precision,
            'amount_precision': self.amount_precision,
            'max_user_id_length': self.max_user_id_length,
            'max_symbol_length': self.max_symbol_length,
            'max_quantity_per_transaction': self.max_quantity_per_transaction,
            'max_price_per_share': self.max_price_per_share,
            'max_commission_rate': self.max_commission_rate,
            'max_calculation_days': self.max_calculation_days,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'TradingConfig':
        """从字典创建配置"""
        return cls(
            cost_basis_method=CostBasisMethod(data.get('cost_basis_method', 'average_cost')),
            price_source=PriceSource(data.get('price_source', 'adj_close')),
            missing_price_strategy=MissingPriceStrategy(data.get('missing_price_strategy', 'backfill')),
            allow_short_selling=data.get('allow_short_selling', False),
            allow_fractional_shares=data.get('allow_fractional_shares', False),
            only_trading_days=data.get('only_trading_days', False),
            recompute_window_days=data.get('recompute_window_days', 7),
            price_precision=data.get('price_precision', 4),
            amount_precision=data.get('amount_precision', 2),
            max_user_id_length=data.get('max_user_id_length', 100),
            max_symbol_length=data.get('max_symbol_length', 20),
            max_quantity_per_transaction=data.get('max_quantity_per_transaction', 10_000_000),
            max_price_per_share=data.get('max_price_per_share', 1_000_000),
            max_commission_rate=data.get('max_commission_rate', 0.1),
            max_calculation_days=data.get('max_calculation_days', 10 * 365),
        )


# 默认配置实例
DEFAULT_TRADING_CONFIG = TradingConfig.get_default()