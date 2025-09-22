"""
持仓批次模型
每次买入都创建一个独立的批次，支持精确的成本基础追踪
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from decimal import Decimal


@dataclass
class PositionLot:
    """
    持仓批次模型 - 每次买入创建一个独立批次
    
    核心概念：
    - 每次买入都是独立批次，保持完整的成本基础追踪
    - original_quantity: 原始买入数量（不变）
    - remaining_quantity: 剩余数量（随卖出减少）
    - cost_basis: 每股成本基础
    """
    
    id: Optional[int] = None
    user_id: str                       # 用户ID
    symbol: str                        # 股票代码
    transaction_id: int                # 关联的买入交易ID
    original_quantity: Decimal         # 原始买入数量
    remaining_quantity: Decimal        # 剩余数量（卖出后减少）
    cost_basis: Decimal               # 每股成本基础
    purchase_date: str                # 买入日期（YYYY-MM-DD）
    is_closed: bool = False           # 是否已完全卖出
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @property
    def total_cost(self) -> Decimal:
        """剩余持仓的总成本"""
        return self.remaining_quantity * self.cost_basis
    
    @property
    def is_fully_sold(self) -> bool:
        """是否已完全卖出"""
        return self.remaining_quantity <= Decimal('0.0001')  # 考虑精度
    
    @property
    def sold_quantity(self) -> Decimal:
        """已卖出数量"""
        return self.original_quantity - self.remaining_quantity
    
    def can_sell(self, quantity: Decimal) -> bool:
        """检查是否可以从此批次卖出指定数量"""
        return self.remaining_quantity >= quantity - Decimal('0.0001')  # 考虑精度
    
    def sell_from_lot(self, quantity: Decimal) -> None:
        """从此批次卖出指定数量"""
        if not self.can_sell(quantity):
            raise ValueError(f"批次 {self.id} 剩余数量 {self.remaining_quantity} 不足以卖出 {quantity}")
        
        self.remaining_quantity -= quantity
        if self.is_fully_sold:
            self.is_closed = True
        self.updated_at = datetime.now()
    
    def __str__(self) -> str:
        status = "已关闭" if self.is_closed else "活跃"
        return (f"批次{self.id}: {self.symbol} "
                f"{self.remaining_quantity:.4f}/{self.original_quantity:.4f}股 "
                f"@{self.cost_basis:.4f} ({status})")