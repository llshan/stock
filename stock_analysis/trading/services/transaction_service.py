#!/usr/bin/env python3
"""
交易记录服务
负责处理买入、卖出交易记录，并自动更新持仓
"""

import logging
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from decimal import Decimal

from ...data.storage import create_storage
from ..models.transaction import Transaction
from ..models.portfolio import Position
from ..config import DEFAULT_TRADING_CONFIG
from .lot_transaction_service import LotTransactionService


class TransactionService:
    """交易记录服务"""
    
    def __init__(self, storage, config):
        """
        初始化交易服务
        
        Args:
            storage: 存储实例
            config: 交易配置
        """
        self.storage = storage
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # 使用批次级别服务作为底层实现，并传递配置
        self.lot_service = LotTransactionService(storage, config)
    
    def record_buy_transaction(self, symbol: str, quantity: Decimal,
                             price: Decimal, transaction_date: str,
                             platform: str = None, external_id: str = None, notes: str = None) -> Transaction:
        """
        记录买入交易

        Args:
            symbol: 股票代码
            quantity: 买入数量
            price: 买入价格
            transaction_date: 交易日期（YYYY-MM-DD格式）
            platform: 交易平台 (ml, schwab等)
            external_id: 外部业务ID，用于去重
            notes: 备注

        Returns:
            Transaction: 创建的交易记录
        """
        # 委托给批次级别服务处理，确保创建批次记录
        return self.lot_service.record_buy_transaction(
            symbol, quantity, price, transaction_date, platform, external_id, notes
        )
    
    def record_sell_transaction(self, symbol: str, quantity: Decimal,
                              price: Decimal, transaction_date: str,
                              external_id: str = None,
                              notes: str = None, cost_basis_method: str = 'FIFO') -> Transaction:
        """
        记录卖出交易
        
        Args:
            symbol: 股票代码
            quantity: 卖出数量
            price: 卖出价格
            transaction_date: 交易日期（YYYY-MM-DD格式）
            external_id: 外部业务ID，用于去重
            notes: 备注
            cost_basis_method: 成本基础方法，默认FIFO（向后兼容）
            
        Returns:
            Transaction: 创建的交易记录
            
        Raises:
            ValueError: 卖出数量超过持仓数量时
        """
        # 委托给批次级别服务处理，使用FIFO作为默认方法
        return self.lot_service.record_sell_transaction(
            symbol, quantity, price, transaction_date, 
            external_id, notes, cost_basis_method
        )
    
    def get_user_transactions(self, symbol: str = None,
                            start_date: str = None, end_date: str = None) -> List[Transaction]:
        """
        获取用户交易记录
        
        Args:
            symbol: 股票代码（可选）
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
            
        Returns:
            List[Transaction]: 交易记录列表
        """
        return self.lot_service.get_user_transactions(symbol, start_date, end_date)
    
    def get_active_symbols(self) -> List[str]:
        """获取用户所有活跃持仓的股票代码"""
        return self.lot_service.get_active_symbols()
    
    def get_current_positions(self) -> List[Position]:
        """
        获取用户当前持仓（基于批次汇总）

        Args:

        Returns:
            List[Position]: 持仓列表
        """
        # 从批次级别服务获取持仓汇总，然后转换为Position对象
        position_summaries = self.lot_service.get_position_summary()

        positions = []
        for summary in position_summaries:
            if summary.is_active:
                position = Position(
                    symbol=summary.symbol,
                    quantity=summary.total_quantity,
                    avg_cost=summary.avg_cost,
                    total_cost=summary.total_cost,
                    first_buy_date=summary.first_buy_date,
                    last_transaction_date=summary.last_transaction_date,  # 使用最后买入日期
                    is_active=True
                )
                positions.append(position)

        return positions

    def get_positions_as_of_date(self, as_of_date: str) -> List[Position]:
        """
        获取截止到指定日期的用户持仓（基于批次汇总）

        Args:
            as_of_date: 截止日期（YYYY-MM-DD格式）

        Returns:
            List[Position]: 持仓列表
        """
        # 从批次级别服务获取截止日期的持仓汇总
        position_summaries = self.lot_service.get_position_summary_as_of_date(as_of_date)

        positions = []
        for summary in position_summaries:
            if summary.is_active:
                position = Position(
                    symbol=summary.symbol,
                    quantity=Decimal(str(summary.total_quantity)),
                    avg_cost=Decimal(str(summary.avg_cost)),
                    total_cost=Decimal(str(summary.total_cost)),
                    first_buy_date=summary.first_buy_date,
                    last_transaction_date=summary.last_transaction_date,
                    is_active=True
                )
                positions.append(position)

        return positions
    
    def get_current_position(self, symbol: str) -> Optional[Position]:
        """
        获取特定股票的当前持仓（基于批次汇总）
        
        Args:
            symbol: 股票代码
            
        Returns:
            Optional[Position]: 持仓记录，如果不存在则为None
        """
        # 从批次级别服务获取持仓汇总
        position_summaries = self.lot_service.get_position_summary(symbol)
        
        for summary in position_summaries:
            if summary.symbol == symbol and summary.is_active:
                return Position(
                    symbol=summary.symbol,
                    quantity=summary.total_quantity,
                    avg_cost=summary.avg_cost,
                    total_cost=summary.total_cost,
                    first_buy_date=summary.first_buy_date,
                    last_transaction_date=summary.last_transaction_date,
                    is_active=True
                )
        
        return None
    
    def recalculate_position(self, symbol: str) -> Optional[Position]:
        """
        基于所有交易记录重新计算持仓（使用批次级别重算）
        
        Args:
            symbol: 股票代码
            
        Returns:
            Optional[Position]: 重新计算的持仓记录
        """
        self.logger.info(f"重新计算持仓: {symbol}")
        
        # 注意：批次级别的重算需要重新初始化所有批次
        # 这是一个复杂的操作，建议使用迁移脚本处理
        # 这里提供简化版本，基于当前批次汇总
        return self.get_current_position(symbol)
    
    def close(self):
        """关闭服务"""
        if self.lot_service:
            self.lot_service.close()
        if self.storage:
            self.storage.close()