"""
卖出分配模型
记录每笔卖出交易与买入批次的精确匹配关系
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from decimal import Decimal


@dataclass
class SaleAllocation:
    """
    卖出分配模型 - 记录卖出与批次的匹配关系
    
    核心概念：
    - 每笔卖出交易可能匹配多个买入批次
    - 每个匹配记录一条SaleAllocation
    - 记录精确的数量、成本和收益
    """
    
    sale_transaction_id: int           # 卖出交易ID
    lot_id: int                       # 匹配的买入批次ID
    quantity_sold: Decimal            # 从该批次卖出的数量
    cost_basis: Decimal               # 该批次的成本基础（每股）
    sale_price: Decimal               # 卖出价格（每股）
    realized_pnl: Decimal             # 该笔匹配的已实现盈亏
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    
    @property
    def proceeds(self) -> Decimal:
        """销售收入"""
        return self.quantity_sold * self.sale_price
    
    @property
    def cost_amount(self) -> Decimal:
        """该笔匹配的成本金额"""
        return self.quantity_sold * self.cost_basis
    
    @classmethod
    def create_allocation(cls, sale_transaction_id: int, lot_id: int, 
                         quantity_sold: Decimal, cost_basis: Decimal, 
                         sale_price: Decimal) -> 'SaleAllocation':
        """创建卖出分配记录"""
        realized_pnl = (sale_price - cost_basis) * quantity_sold
        
        return cls(
            sale_transaction_id=sale_transaction_id,
            lot_id=lot_id,
            quantity_sold=quantity_sold,
            cost_basis=cost_basis,
            sale_price=sale_price,
            realized_pnl=realized_pnl,
            created_at=datetime.now()
        )
    
    def __str__(self) -> str:
        return (f"分配{self.id}: 批次{self.lot_id} "
                f"{self.quantity_sold:.4f}股 "
                f"@{self.sale_price:.4f} "
                f"(成本{self.cost_basis:.4f}, "
                f"盈亏{self.realized_pnl:.2f})")