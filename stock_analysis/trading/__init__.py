#!/usr/bin/env python3
"""
股票交易追踪模块
提供交易记录、持仓管理和盈亏计算功能

核心功能：
- 批次级别追踪：每次买入创建独立批次，支持精确成本基础计算
- 成本基础方法：支持FIFO、LIFO、SpecificLot、AverageCost四种方法
- 交易日模式：only_trading_days 控制是否仅在交易日计算盈亏
- 已实现盈亏：卖出时自动记录到 daily_pnl 表
- 价格回填：缺失价格时使用最近交易日价格并标记

新批次级别API：
- LotTransactionService: 批次级别交易服务
- LotPnLCalculator: 批次级别盈亏计算
- PositionLot: 持仓批次模型
- SaleAllocation: 卖出分配模型
- PositionSummary: 持仓汇总模型

详细配置指南请参考：docs/trading_config_guide.md
"""

# 批次级别API
from .services.lot_transaction_service import LotTransactionService
from .calculators.lot_pnl_calculator import LotPnLCalculator
from .models.position_lot import PositionLot
from .models.sale_allocation import SaleAllocation
from .models.position_summary import PositionSummary

# 配置和枚举
from .config import (
    TradingConfig, 
    CostBasisMethod, 
    PriceSource, 
    MissingPriceStrategy,
    DEFAULT_TRADING_CONFIG
)

__all__ = [
    # 批次级别API
    'LotTransactionService',
    'LotPnLCalculator',
    'PositionLot',
    'SaleAllocation', 
    'PositionSummary',
    
    # 配置
    'TradingConfig',
    'CostBasisMethod',
    'PriceSource',
    'MissingPriceStrategy',
    'DEFAULT_TRADING_CONFIG',
]