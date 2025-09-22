#!/usr/bin/env python3
"""
投资组合和持仓相关数据模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Position:
    """股票持仓记录模型"""
    user_id: str                    # 用户ID
    symbol: str                     # 股票代码
    quantity: float                 # 持仓数量
    avg_cost: float                 # 平均成本
    total_cost: float               # 总成本（含佣金）
    first_buy_date: str             # 首次买入日期（YYYY-MM-DD格式）
    last_transaction_date: str      # 最后交易日期（YYYY-MM-DD格式）
    is_active: bool = True          # 是否为活跃持仓
    id: Optional[int] = None        # 数据库ID
    created_at: Optional[datetime] = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = field(default_factory=datetime.now)

    def __post_init__(self):
        """数据验证"""
        if self.avg_cost < 0:
            raise ValueError(f"平均成本不能为负数: {self.avg_cost}")
            
        if self.total_cost < 0:
            raise ValueError(f"总成本不能为负数: {self.total_cost}")

    @property
    def market_value(self) -> float:
        """当前市值（需要传入当前价格）"""
        # 这里返回None，实际计算需要当前市场价格
        return None

    def calculate_unrealized_pnl(self, current_price: float) -> float:
        """计算未实现盈亏"""
        if current_price <= 0:
            raise ValueError(f"当前价格必须大于0: {current_price}")
        
        current_value = self.quantity * current_price
        return current_value - self.total_cost

    def calculate_unrealized_pnl_pct(self, current_price: float) -> float:
        """计算未实现盈亏百分比"""
        if self.total_cost == 0:
            return 0.0
        
        unrealized_pnl = self.calculate_unrealized_pnl(current_price)
        return (unrealized_pnl / self.total_cost) * 100

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'symbol': self.symbol,
            'quantity': self.quantity,
            'avg_cost': self.avg_cost,
            'total_cost': self.total_cost,
            'first_buy_date': self.first_buy_date,
            'last_transaction_date': self.last_transaction_date,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Position':
        """从字典创建实例"""
        # 处理datetime字段
        created_at = None
        updated_at = None
        
        if data.get('created_at'):
            if isinstance(data['created_at'], str):
                created_at = datetime.fromisoformat(data['created_at'])
            else:
                created_at = data['created_at']
                
        if data.get('updated_at'):
            if isinstance(data['updated_at'], str):
                updated_at = datetime.fromisoformat(data['updated_at'])
            else:
                updated_at = data['updated_at']
        
        return cls(
            id=data.get('id'),
            user_id=data['user_id'],
            symbol=data['symbol'],
            quantity=data['quantity'],
            avg_cost=data['avg_cost'],
            total_cost=data['total_cost'],
            first_buy_date=data['first_buy_date'],
            last_transaction_date=data['last_transaction_date'],
            is_active=data.get('is_active', True),
            created_at=created_at,
            updated_at=updated_at,
        )


@dataclass
class DailyPnL:
    """每日盈亏记录模型"""
    user_id: str                    # 用户ID
    symbol: str                     # 股票代码
    valuation_date: str             # 估值日期（YYYY-MM-DD格式）
    quantity: float                 # 持仓数量
    avg_cost: float                 # 平均成本
    market_price: float             # 市场价格（收盘价）
    market_value: float             # 市场价值
    unrealized_pnl: float           # 未实现盈亏
    unrealized_pnl_pct: float       # 未实现盈亏百分比
    total_cost: float               # 总成本
    realized_pnl: float = 0.0       # 已实现盈亏
    realized_pnl_pct: float = 0.0   # 已实现盈亏百分比
    price_date: Optional[str] = None  # 价格对应的实际日期
    is_stale_price: bool = False    # 是否为回填价格
    id: Optional[int] = None        # 数据库ID
    created_at: Optional[datetime] = field(default_factory=datetime.now)

    def __post_init__(self):
        """数据验证和计算"""
        if self.quantity < 0:
            raise ValueError(f"持仓数量不能为负数: {self.quantity}")
            
        if self.market_price < 0:
            raise ValueError(f"市场价格不能为负数: {self.market_price}")
            
        if self.avg_cost < 0:
            raise ValueError(f"平均成本不能为负数: {self.avg_cost}")

        # 验证计算的一致性
        expected_market_value = self.quantity * self.market_price
        if abs(self.market_value - expected_market_value) > 0.01:
            raise ValueError(f"市场价值计算不一致: {self.market_value} vs {expected_market_value}")

        expected_unrealized_pnl = self.market_value - self.total_cost
        if abs(self.unrealized_pnl - expected_unrealized_pnl) > 0.01:
            raise ValueError(f"未实现盈亏计算不一致: {self.unrealized_pnl} vs {expected_unrealized_pnl}")

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'symbol': self.symbol,
            'valuation_date': self.valuation_date,
            'quantity': self.quantity,
            'avg_cost': self.avg_cost,
            'market_price': self.market_price,
            'market_value': self.market_value,
            'unrealized_pnl': self.unrealized_pnl,
            'unrealized_pnl_pct': self.unrealized_pnl_pct,
            'realized_pnl': self.realized_pnl,
            'realized_pnl_pct': self.realized_pnl_pct,
            'total_cost': self.total_cost,
            'price_date': self.price_date,
            'is_stale_price': self.is_stale_price,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'DailyPnL':
        """从字典创建实例"""
        # 处理datetime字段
        created_at = None
        if data.get('created_at'):
            if isinstance(data['created_at'], str):
                created_at = datetime.fromisoformat(data['created_at'])
            else:
                created_at = data['created_at']
        
        return cls(
            id=data.get('id'),
            user_id=data['user_id'],
            symbol=data['symbol'],
            valuation_date=data['valuation_date'],
            quantity=data['quantity'],
            avg_cost=data['avg_cost'],
            market_price=data['market_price'],
            market_value=data['market_value'],
            unrealized_pnl=data['unrealized_pnl'],
            unrealized_pnl_pct=data['unrealized_pnl_pct'],
            realized_pnl=data.get('realized_pnl', 0.0),
            realized_pnl_pct=data.get('realized_pnl_pct', 0.0),
            total_cost=data['total_cost'],
            price_date=data.get('price_date'),
            is_stale_price=bool(data.get('is_stale_price', False)),
            created_at=created_at,
        )

    @classmethod
    def calculate(cls, user_id: str, symbol: str, valuation_date: str,
                  position: Position, market_price: float) -> 'DailyPnL':
        """基于持仓和市场价格计算每日盈亏"""
        if position.quantity == 0:
            raise ValueError("持仓数量为0，无法计算盈亏")
        
        market_value = position.quantity * market_price
        unrealized_pnl = market_value - position.total_cost
        unrealized_pnl_pct = (unrealized_pnl / position.total_cost) * 100 if position.total_cost > 0 else 0.0
        
        return cls(
            user_id=user_id,
            symbol=symbol,
            valuation_date=valuation_date,
            quantity=position.quantity,
            avg_cost=position.avg_cost,
            market_price=market_price,
            market_value=market_value,
            unrealized_pnl=unrealized_pnl,
            unrealized_pnl_pct=unrealized_pnl_pct,
            total_cost=position.total_cost,
        )