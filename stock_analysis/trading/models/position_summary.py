"""
持仓汇总模型
从批次数据计算得出的汇总持仓信息
"""

from dataclasses import dataclass
from typing import List
from .position_lot import PositionLot


@dataclass
class PositionSummary:
    """
    持仓汇总模型 - 从批次数据计算得出的汇总信息
    
    核心概念：
    - 不直接存储在数据库中，而是从PositionLot动态计算
    - 提供传统的持仓视图（总数量、平均成本等）
    - 同时保留批次级别的详细信息
    """
    
    user_id: str
    symbol: str
    total_quantity: float           # 总持仓数量（所有批次剩余数量之和）
    total_cost: float              # 总成本（所有批次成本之和）
    avg_cost: float                # 加权平均成本
    first_buy_date: str            # 最早买入日期
    last_transaction_date: str     # 最后交易日期
    lot_count: int                 # 持仓批次数量
    closed_lot_count: int          # 已关闭批次数量
    
    @classmethod
    def from_lots(cls, user_id: str, symbol: str, lots: List[PositionLot]) -> 'PositionSummary':
        """从批次列表计算汇总信息"""
        if not lots:
            return cls(
                user_id=user_id,
                symbol=symbol,
                total_quantity=0.0,
                total_cost=0.0,
                avg_cost=0.0,
                first_buy_date="",
                last_transaction_date="",
                lot_count=0,
                closed_lot_count=0
            )
        
        # 计算汇总数据
        active_lots = [lot for lot in lots if not lot.is_closed]
        total_quantity = sum(lot.remaining_quantity for lot in active_lots)
        total_cost = sum(lot.total_cost for lot in active_lots)
        avg_cost = total_cost / total_quantity if total_quantity > 0 else 0.0
        
        # 日期信息
        first_buy_date = min(lot.purchase_date for lot in lots)
        last_transaction_date = max(lot.purchase_date for lot in lots)
        
        # 批次统计
        lot_count = len(active_lots)
        closed_lot_count = len([lot for lot in lots if lot.is_closed])
        
        return cls(
            user_id=user_id,
            symbol=symbol,
            total_quantity=total_quantity,
            total_cost=total_cost,
            avg_cost=avg_cost,
            first_buy_date=first_buy_date,
            last_transaction_date=last_transaction_date,
            lot_count=lot_count,
            closed_lot_count=closed_lot_count
        )
    
    @property
    def is_active(self) -> bool:
        """是否有活跃持仓"""
        return self.total_quantity > 0.0001
    
    def calculate_unrealized_pnl(self, market_price: float) -> float:
        """计算未实现盈亏"""
        if not self.is_active:
            return 0.0
        return (market_price - self.avg_cost) * self.total_quantity
    
    def calculate_unrealized_pnl_pct(self, market_price: float) -> float:
        """计算未实现盈亏百分比"""
        if self.avg_cost <= 0:
            return 0.0
        return (market_price - self.avg_cost) / self.avg_cost
    
    def __str__(self) -> str:
        if not self.is_active:
            return f"{self.symbol}: 无持仓 ({self.closed_lot_count}个已关闭批次)"
        
        return (f"{self.symbol}: {self.total_quantity:.4f}股 "
                f"@{self.avg_cost:.4f} "
                f"({self.lot_count}个批次, 成本{self.total_cost:.2f})")