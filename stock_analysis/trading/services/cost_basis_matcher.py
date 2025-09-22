#!/usr/bin/env python3
"""
成本基础匹配器
实现FIFO、LIFO、SpecificLot等不同的成本基础计算方法
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Tuple
import logging

from ..models.position_lot import PositionLot


class CostBasisMatcher(ABC):
    """成本基础匹配器抽象基类"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    @abstractmethod
    def match_lots_for_sale(self, available_lots: List[PositionLot], 
                           sell_quantity: float) -> List[Tuple[PositionLot, float]]:
        """
        为卖出交易匹配批次
        
        Args:
            available_lots: 可用的持仓批次列表
            sell_quantity: 要卖出的数量
            
        Returns:
            List[Tuple[PositionLot, float]]: 匹配结果，每个元组包含(批次, 从该批次卖出的数量)
        """
        pass
    
    def _validate_sufficient_quantity(self, available_lots: List[PositionLot], 
                                    sell_quantity: float) -> bool:
        """验证是否有足够的持仓数量"""
        total_available = sum(lot.remaining_quantity for lot in available_lots)
        return total_available >= sell_quantity - 0.0001  # 考虑浮点精度


class FIFOMatcher(CostBasisMatcher):
    """先进先出匹配器"""
    
    def match_lots_for_sale(self, available_lots: List[PositionLot], 
                           sell_quantity: float) -> List[Tuple[PositionLot, float]]:
        """按购买日期从早到晚匹配批次"""
        if not self._validate_sufficient_quantity(available_lots, sell_quantity):
            raise ValueError(f"可用持仓数量不足: 需要{sell_quantity}, 可用{sum(lot.remaining_quantity for lot in available_lots)}")
        
        # 按购买日期和ID排序（先进先出）
        sorted_lots = sorted(
            available_lots,
            key=lambda lot: (lot.purchase_date, lot.id or 0)
        )
        
        matches = []
        remaining_to_sell = sell_quantity
        
        for lot in sorted_lots:
            if remaining_to_sell <= 0.0001:  # 考虑浮点精度
                break
            
            if lot.remaining_quantity <= 0.0001:
                continue
            
            # 计算从此批次卖出的数量
            quantity_from_lot = min(remaining_to_sell, lot.remaining_quantity)
            matches.append((lot, quantity_from_lot))
            remaining_to_sell -= quantity_from_lot
            
            self.logger.debug(f"FIFO匹配: 批次{lot.id} {quantity_from_lot:.4f}@{lot.cost_basis:.4f}")
        
        if remaining_to_sell > 0.0001:
            raise ValueError(f"FIFO匹配失败: 还有{remaining_to_sell:.4f}未匹配")
        
        return matches


class LIFOMatcher(CostBasisMatcher):
    """后进先出匹配器"""
    
    def match_lots_for_sale(self, available_lots: List[PositionLot], 
                           sell_quantity: float) -> List[Tuple[PositionLot, float]]:
        """按购买日期从晚到早匹配批次"""
        if not self._validate_sufficient_quantity(available_lots, sell_quantity):
            raise ValueError(f"可用持仓数量不足: 需要{sell_quantity}, 可用{sum(lot.remaining_quantity for lot in available_lots)}")
        
        # 按购买日期和ID倒序排序（后进先出）
        sorted_lots = sorted(
            available_lots,
            key=lambda lot: (lot.purchase_date, lot.id or 0),
            reverse=True
        )
        
        matches = []
        remaining_to_sell = sell_quantity
        
        for lot in sorted_lots:
            if remaining_to_sell <= 0.0001:  # 考虑浮点精度
                break
            
            if lot.remaining_quantity <= 0.0001:
                continue
            
            # 计算从此批次卖出的数量
            quantity_from_lot = min(remaining_to_sell, lot.remaining_quantity)
            matches.append((lot, quantity_from_lot))
            remaining_to_sell -= quantity_from_lot
            
            self.logger.debug(f"LIFO匹配: 批次{lot.id} {quantity_from_lot:.4f}@{lot.cost_basis:.4f}")
        
        if remaining_to_sell > 0.0001:
            raise ValueError(f"LIFO匹配失败: 还有{remaining_to_sell:.4f}未匹配")
        
        return matches


class SpecificLotMatcher(CostBasisMatcher):
    """指定批次匹配器"""
    
    def __init__(self, specific_lots: List[Dict[str, float]]):
        """
        初始化指定批次匹配器
        
        Args:
            specific_lots: 指定的批次列表，格式: [{"lot_id": 123, "quantity": 50}, ...]
        """
        super().__init__()
        self.specific_lots = specific_lots
        
        # 验证指定批次格式
        for spec in specific_lots:
            if 'lot_id' not in spec or 'quantity' not in spec:
                raise ValueError("指定批次必须包含 lot_id 和 quantity 字段")
            if spec['quantity'] <= 0:
                raise ValueError("指定批次数量必须大于0")
    
    def match_lots_for_sale(self, available_lots: List[PositionLot], 
                           sell_quantity: float) -> List[Tuple[PositionLot, float]]:
        """按用户指定的批次和数量匹配"""
        # 创建批次ID到批次对象的映射
        lot_map = {lot.id: lot for lot in available_lots if lot.id is not None}
        
        matches = []
        total_specified = 0
        
        for spec in self.specific_lots:
            lot_id = spec['lot_id']
            specified_quantity = spec['quantity']
            
            # 检查批次是否存在
            if lot_id not in lot_map:
                raise ValueError(f"指定的批次 {lot_id} 不存在或不可用")
            
            lot = lot_map[lot_id]
            
            # 检查批次是否有足够的剩余数量
            if lot.remaining_quantity < specified_quantity - 0.0001:
                raise ValueError(f"批次 {lot_id} 剩余数量不足: 需要{specified_quantity}, 剩余{lot.remaining_quantity}")
            
            matches.append((lot, specified_quantity))
            total_specified += specified_quantity
            
            self.logger.debug(f"指定批次匹配: 批次{lot_id} {specified_quantity:.4f}@{lot.cost_basis:.4f}")
        
        # 验证指定的总数量是否等于要卖出的数量
        if abs(total_specified - sell_quantity) > 0.0001:
            raise ValueError(f"指定批次总数量({total_specified})与卖出数量({sell_quantity})不匹配")
        
        return matches


class AverageCostMatcher(CostBasisMatcher):
    """平均成本匹配器"""
    
    def match_lots_for_sale(self, available_lots: List[PositionLot], 
                           sell_quantity: float) -> List[Tuple[PositionLot, float]]:
        """
        平均成本法匹配
        按各批次数量比例分配卖出数量，实现类似平均成本的效果
        """
        if not self._validate_sufficient_quantity(available_lots, sell_quantity):
            raise ValueError(f"可用持仓数量不足: 需要{sell_quantity}, 可用{sum(lot.remaining_quantity for lot in available_lots)}")
        
        total_available = sum(lot.remaining_quantity for lot in available_lots)
        matches = []
        remaining_to_sell = sell_quantity
        
        # 按比例分配到各批次
        for i, lot in enumerate(available_lots):
            if remaining_to_sell <= 0.0001:
                break
            
            if lot.remaining_quantity <= 0.0001:
                continue
            
            # 计算该批次应分配的数量
            if i == len(available_lots) - 1:  # 最后一个批次，分配所有剩余
                quantity_from_lot = remaining_to_sell
            else:
                ratio = lot.remaining_quantity / total_available
                quantity_from_lot = min(sell_quantity * ratio, lot.remaining_quantity, remaining_to_sell)
            
            if quantity_from_lot > 0.0001:
                matches.append((lot, quantity_from_lot))
                remaining_to_sell -= quantity_from_lot
                
                self.logger.debug(f"平均成本匹配: 批次{lot.id} {quantity_from_lot:.4f}@{lot.cost_basis:.4f}")
        
        if remaining_to_sell > 0.0001:
            raise ValueError(f"平均成本匹配失败: 还有{remaining_to_sell:.4f}未匹配")
        
        return matches


def create_cost_basis_matcher(method: str, **kwargs) -> CostBasisMatcher:
    """
    创建成本基础匹配器
    
    Args:
        method: 匹配方法 ('FIFO', 'LIFO', 'SpecificLot', 'AverageCost', 'Average')
        **kwargs: 额外参数（如SpecificLot的specific_lots）
        
    Returns:
        CostBasisMatcher: 对应的匹配器实例
    """
    method = method.upper()
    
    # 处理CLI命名与匹配器不一致的问题
    if method == 'AVERAGE':
        method = 'AVERAGECOST'
    
    if method == 'FIFO':
        return FIFOMatcher()
    elif method == 'LIFO':
        return LIFOMatcher()
    elif method == 'SPECIFICLOT':
        specific_lots = kwargs.get('specific_lots')
        if not specific_lots:
            raise ValueError("SpecificLot方法需要提供specific_lots参数")
        return SpecificLotMatcher(specific_lots)
    elif method == 'AVERAGECOST':
        return AverageCostMatcher()
    else:
        raise ValueError(f"不支持的成本基础方法: {method}")