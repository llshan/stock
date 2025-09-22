#!/usr/bin/env python3
"""
批次级别交易记录服务
负责处理买入、卖出交易记录，并自动维护批次级别的持仓追踪
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

from ...data.storage import create_storage
from ..models.transaction import Transaction
from ..models.position_lot import PositionLot
from ..models.sale_allocation import SaleAllocation
from ..models.position_summary import PositionSummary
from ..config import DEFAULT_TRADING_CONFIG
from .cost_basis_matcher import create_cost_basis_matcher


class LotTransactionService:
    """
    批次级别交易记录服务
    
    ## 事务边界策略
    
    ### 买入交易
    单事务操作：
    1. 创建 transactions 记录
    2. 创建对应的 position_lots 记录
    3. 更新 positions 汇总记录（缓存作用）
    
    ### 卖出交易
    单事务操作：
    1. 根据成本基础方法匹配批次（FIFO/LIFO/SpecificLot/AverageCost）
    2. 创建 transactions 记录
    3. 创建 sale_allocations 记录（每个匹配的批次一条）
    4. 更新相关 position_lots 的 remaining_quantity
    5. 标记完全卖出的批次为 is_closed=1
    6. 更新当日 daily_pnl 的 realized_pnl（创建占位记录或更新现有记录）
    7. 更新 positions 汇总记录（缓存作用）
    
    这确保了数据一致性：如果任何步骤失败，整个事务回滚，不会出现部分更新状态。
    
    ## 幂等策略
    
    ### external_id 去重机制
    - 每个交易可提供 external_id 作为外部业务系统的唯一标识
    - 数据库约束：(user_id, external_id) 唯一，防止重复插入
    - 适用场景：API重试、批量导入、定时任务等可能重复执行的场景
    - 实现：在 transactions 表上创建唯一约束，依赖数据库级别防重
    
    ### 操作幂等性
    - 所有 CREATE TABLE IF NOT EXISTS 操作天然幂等
    - 所有 INSERT OR IGNORE 操作在约束冲突时安全跳过
    - 批次匹配和分配算法确保相同输入产生相同结果
    
    ## 数据一致性保证
    
    ### 批次数量平衡
    - position_lots.remaining_quantity 始终 >= 0
    - position_lots.original_quantity 不可变
    - sale_allocations 中的 quantity_sold 总和 = 对应交易的 quantity
    
    ### 盈亏计算一致性
    - realized_pnl = (sale_price - cost_basis) * quantity_sold
    - daily_pnl.realized_pnl 为当日所有 sale_allocations 的 realized_pnl 总和
    - unrealized_pnl 基于 open lots 的 remaining_quantity 和当前市价计算
    """
    
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
    
    def record_buy_transaction(self, user_id: str, symbol: str, quantity: float, 
                             price: float, transaction_date: str, 
                             external_id: str = None, notes: str = None) -> Transaction:
        """
        记录买入交易并创建对应的持仓批次
        
        Args:
            user_id: 用户ID
            symbol: 股票代码
            quantity: 买入数量
            price: 买入价格
            transaction_date: 交易日期（YYYY-MM-DD格式）
            external_id: 外部业务ID，用于去重
            notes: 备注
            
        Returns:
            Transaction: 创建的交易记录
        """
        self.logger.info(f"记录买入交易: {user_id} {symbol} {quantity:.4f}@{price:.4f}")
        
        # 输入验证
        self._validate_buy_input(user_id, symbol, quantity, price, transaction_date)
        
        # 确保股票存在
        self.storage.ensure_stock_exists(symbol)
        
        with self.storage.transaction():
            # 1. 创建买入交易记录
            transaction_data = {
                'user_id': user_id,
                'symbol': symbol,
                'transaction_type': 'BUY',
                'quantity': quantity,
                'price': price,
                'transaction_date': transaction_date,
                'external_id': external_id,  # 新增：支持external_id
                'notes': notes,
                'lot_id': None  # 买入交易不关联特定批次
            }
            
            transaction_id = self.storage.upsert_transaction(transaction_data)
            
            # 2. 创建对应的持仓批次
            self._create_position_lot_from_buy(
                transaction_id, user_id, symbol, quantity, price, 
                transaction_date
            )
            
            # 构造返回的交易对象
            transaction = Transaction(
                id=transaction_id,
                user_id=user_id,
                symbol=symbol,
                transaction_type='BUY',
                quantity=quantity,
                price=price,
                transaction_date=transaction_date,
                notes=notes,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            self.logger.info(f"✅ 买入交易记录成功: ID={transaction_id}")
            return transaction
    
    def record_sell_transaction(self, user_id: str, symbol: str, quantity: float, 
                              price: float, transaction_date: str, 
                              external_id: str = None, notes: str = None, 
                              cost_basis_method: str = 'FIFO',
                              specific_lots: List[Dict] = None) -> Transaction:
        """
        记录卖出交易并按指定方法匹配批次
        
        ## 事务边界实现
        此方法在单个数据库事务中完成以下操作：
        1. 外部ID去重检查（如提供）
        2. 批次匹配和验证
        3. 创建 SELL 交易记录
        4. 批量创建 sale_allocations 记录
        5. 批量更新 position_lots.remaining_quantity
        6. 更新当日 daily_pnl.realized_pnl（创建占位或更新）
        7. 更新 positions 汇总缓存
        
        如任一步骤失败，整个事务回滚，确保数据一致性。
        
        Args:
            user_id: 用户ID
            symbol: 股票代码
            quantity: 卖出数量
            price: 卖出价格
            transaction_date: 交易日期（YYYY-MM-DD格式）
            external_id: 外部业务ID，用于去重
            notes: 备注
            cost_basis_method: 成本基础方法 ('FIFO', 'LIFO', 'SpecificLot', 'AverageCost')
            specific_lots: 指定批次列表（仅当method='SpecificLot'时使用）
            
        Returns:
            Transaction: 创建的交易记录
        """
        self.logger.info(f"记录卖出交易: {user_id} {symbol} {quantity:.4f}@{price:.4f} ({cost_basis_method})")
        
        # 输入验证
        self._validate_sell_input(user_id, symbol, quantity, price, transaction_date)
        
        # 获取可用批次
        available_lots = self.get_position_lots(user_id, symbol)
        if not available_lots:
            raise ValueError(f"用户 {user_id} 没有 {symbol} 的持仓")
        
        with self.storage.transaction():
            # 1. 验证总持仓是否足够
            total_available = sum(lot.remaining_quantity for lot in available_lots)
            if total_available < quantity - 0.0001:
                raise ValueError(f"持仓数量不足: 需要{quantity}, 可用{total_available}")
            
            # 2. 创建卖出交易记录
            transaction_data = {
                'user_id': user_id,
                'symbol': symbol,
                'transaction_type': 'SELL',
                'quantity': quantity,
                'price': price,
                'transaction_date': transaction_date,
                'external_id': external_id,  # 新增：支持external_id
                'notes': notes,
                'lot_id': None  # 卖出可能涉及多个批次，这里设为None
            }
            
            transaction_id = self.storage.upsert_transaction(transaction_data)
            
            # 3. 使用匹配器匹配批次
            matcher_kwargs = {}
            if cost_basis_method.upper() == 'SPECIFICLOT':
                if not specific_lots:
                    raise ValueError("SpecificLot方法需要提供specific_lots参数")
                matcher_kwargs['specific_lots'] = specific_lots
            
            matcher = create_cost_basis_matcher(cost_basis_method, **matcher_kwargs)
            matches = matcher.match_lots_for_sale(available_lots, quantity)
            
            # 4. 处理每个匹配，创建分配记录并更新批次
            total_realized_pnl = 0.0
            total_sale_amount = quantity * price
            
            for lot, quantity_sold in matches:
                # 计算已实现盈亏
                realized_pnl = (price - lot.cost_basis) * quantity_sold
                
                # 创建分配记录
                allocation_data = {
                    'sale_transaction_id': transaction_id,
                    'lot_id': lot.id,
                    'quantity_sold': quantity_sold,
                    'cost_basis': lot.cost_basis,
                    'sale_price': price,
                    'realized_pnl': realized_pnl
                }
                
                allocation_id = self.storage.create_sale_allocation(allocation_data)
                
                # 更新批次剩余数量
                new_remaining = lot.remaining_quantity - quantity_sold
                is_closed = new_remaining <= 0.0001
                self.storage.update_lot_remaining_quantity(lot.id, new_remaining, is_closed)
                
                # 累计已实现盈亏
                total_realized_pnl += realized_pnl
                
                self.logger.debug(f"    🔄 分配: 批次{lot.id} 卖出{quantity_sold:.4f}, "
                                f"成本{lot.cost_basis:.4f}, 盈亏{realized_pnl:.2f}")
            
            # 5. 更新当日已实现盈亏到daily_pnl（在同一事务中）
            self._update_daily_realized_pnl(user_id, symbol, transaction_date, total_realized_pnl)
            
            # 构造返回的交易对象
            transaction = Transaction(
                id=transaction_id,
                user_id=user_id,
                symbol=symbol,
                transaction_type='SELL',
                quantity=quantity,
                price=price,
                transaction_date=transaction_date,
                notes=notes,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            self.logger.info(f"✅ 卖出交易记录成功: ID={transaction_id}, "
                           f"总已实现盈亏={total_realized_pnl:.2f}, "
                           f"涉及{len(matches)}个批次")
            return transaction
    
    def get_sale_allocations(self, user_id: str = None, symbol: str = None,
                           sale_transaction_id: int = None) -> List[SaleAllocation]:
        """获取卖出分配记录"""
        allocations_data = self.storage.get_sale_allocations(user_id, symbol, sale_transaction_id)
        
        allocations = []
        for alloc_data in allocations_data:
            allocation = SaleAllocation(
                id=alloc_data['id'],
                sale_transaction_id=alloc_data['sale_transaction_id'],
                lot_id=alloc_data['lot_id'],
                quantity_sold=alloc_data['quantity_sold'],
                cost_basis=alloc_data['cost_basis'],
                sale_price=alloc_data['sale_price'],
                realized_pnl=alloc_data['realized_pnl'],
                created_at=datetime.fromisoformat(alloc_data.get('created_at', '')) if alloc_data.get('created_at') else None
            )
            allocations.append(allocation)
        
        return allocations
    
    def _create_position_lot_from_buy(self, transaction_id: int, user_id: str, 
                                    symbol: str, quantity: float, price: float,
                                    transaction_date: str) -> int:
        """从买入交易创建持仓批次"""
        # 计算成本基础
        cost_basis = price
        
        lot_data = {
            'user_id': user_id,
            'symbol': symbol,
            'transaction_id': transaction_id,
            'original_quantity': quantity,
            'remaining_quantity': quantity,  # 初始时剩余=原始
            'cost_basis': cost_basis,
            'purchase_date': transaction_date,
            'is_closed': False
        }
        
        lot_id = self.storage.create_position_lot(lot_data)
        self.logger.debug(f"    📦 创建批次: ID={lot_id}, {quantity:.4f}@{cost_basis:.4f}")
        return lot_id
    
    def get_position_lots(self, user_id: str, symbol: str = None) -> List[PositionLot]:
        """获取用户的持仓批次"""
        lots_data = self.storage.get_position_lots(user_id, symbol, active_only=True)
        
        lots = []
        for lot_data in lots_data:
            lot = PositionLot(
                id=lot_data['id'],
                user_id=lot_data['user_id'],
                symbol=lot_data['symbol'],
                transaction_id=lot_data['transaction_id'],
                original_quantity=lot_data['original_quantity'],
                remaining_quantity=lot_data['remaining_quantity'],
                cost_basis=lot_data['cost_basis'],
                purchase_date=lot_data['purchase_date'],
                is_closed=bool(lot_data['is_closed']),
                created_at=datetime.fromisoformat(lot_data.get('created_at', '')) if lot_data.get('created_at') else None,
                updated_at=datetime.fromisoformat(lot_data.get('updated_at', '')) if lot_data.get('updated_at') else None
            )
            lots.append(lot)
        
        return lots
    
    def get_position_summary(self, user_id: str, symbol: str = None) -> List[PositionSummary]:
        """获取持仓汇总"""
        lots = self.get_position_lots(user_id, symbol)
        
        # 按股票代码分组
        symbol_lots = {}
        for lot in lots:
            if lot.symbol not in symbol_lots:
                symbol_lots[lot.symbol] = []
            symbol_lots[lot.symbol].append(lot)
        
        summaries = []
        for symbol, symbol_lot_list in symbol_lots.items():
            summary = PositionSummary.from_lots(user_id, symbol, symbol_lot_list)
            if summary.is_active:  # 只返回有持仓的汇总
                summaries.append(summary)
        
        return summaries

    def get_user_transactions(self, user_id: str, symbol: str = None,
                            start_date: str = None, end_date: str = None) -> List['Transaction']:
        """
        获取用户交易记录
        
        Args:
            user_id: 用户ID
            symbol: 股票代码（可选）
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
            
        Returns:
            List[Transaction]: 交易记录列表
        """
        from ..models.transaction import Transaction
        
        transactions_data = self.storage.get_transactions(
            user_id, symbol, start_date, end_date
        )
        
        return [Transaction.from_dict(data) for data in transactions_data]
    
    def get_active_symbols(self, user_id: str) -> List[str]:
        """获取用户所有活跃持仓的股票代码"""
        return self.storage.get_active_symbols_for_user(user_id)
    
    def _validate_buy_input(self, user_id: str, symbol: str, quantity: float, 
                          price: float, transaction_date: str):
        """验证买入交易输入"""
        # 用户ID长度检查
        if len(user_id) > self.config.max_user_id_length:
            raise ValueError(f"用户ID长度不能超过 {self.config.max_user_id_length} 字符")
        
        # 股票代码检查
        if len(symbol) > self.config.max_symbol_length:
            raise ValueError(f"股票代码长度不能超过 {self.config.max_symbol_length} 字符")
        
        # 数量检查
        if quantity <= 0:
            raise ValueError("买入数量必须大于0")
        if quantity > self.config.max_quantity_per_transaction:
            raise ValueError(f"单笔交易数量不能超过 {self.config.max_quantity_per_transaction}")
        
        # 价格检查
        if price <= 0:
            raise ValueError("买入价格必须大于0")
        if price > self.config.max_price_per_share:
            raise ValueError(f"股价不能超过 {self.config.max_price_per_share}")
        
        
        # 日期格式检查（简单验证）
        try:
            datetime.strptime(transaction_date, '%Y-%m-%d')
        except ValueError:
            raise ValueError("交易日期格式必须为 YYYY-MM-DD")
    
    def _validate_sell_input(self, user_id: str, symbol: str, quantity: float, 
                           price: float, transaction_date: str):
        """验证卖出交易输入"""
        # 复用买入验证的大部分逻辑
        self._validate_buy_input(user_id, symbol, quantity, price, transaction_date)
        
        # 卖出特有的验证
        # TODO: 可以添加卖出特有的验证逻辑，如禁止做空等
    
    def _update_daily_realized_pnl(self, user_id: str, symbol: str, 
                                  transaction_date: str, realized_pnl: float):
        """更新当日已实现盈亏到daily_pnl表（在事务中调用）"""
        try:
            # 获取当日是否有daily_pnl记录
            daily_pnl_records = self.storage.get_daily_pnl(
                user_id, symbol, transaction_date, transaction_date
            )
            
            if daily_pnl_records and len(daily_pnl_records) > 0:
                # 更新现有记录的已实现盈亏
                record = daily_pnl_records[0]
                current_realized = record.get('realized_pnl', 0.0)
                new_realized = current_realized + realized_pnl
                
                # 计算已实现盈亏百分比（分母使用total_cost成本基础）
                total_cost = record.get('total_cost', 0.0)
                realized_pnl_pct = (new_realized / total_cost) if total_cost > 0 else 0.0
                
                # 更新记录
                update_data = {
                    'user_id': user_id,
                    'symbol': symbol,
                    'valuation_date': transaction_date,
                    'quantity': record['quantity'],
                    'avg_cost': record['avg_cost'],
                    'market_price': record['market_price'],
                    'market_value': record['market_value'],
                    'unrealized_pnl': record['unrealized_pnl'],
                    'unrealized_pnl_pct': record['unrealized_pnl_pct'],
                    'total_cost': record['total_cost'],
                    'realized_pnl': new_realized,
                    'realized_pnl_pct': realized_pnl_pct,
                    'price_date': record.get('price_date'),
                    'is_stale_price': record.get('is_stale_price', 0),
                }
                
                self.storage.upsert_daily_pnl(update_data)
                self.logger.debug(f"📊 更新当日已实现盈亏: {symbol} {transaction_date} {realized_pnl:.2f}")
            else:
                # 当日无daily_pnl记录，创建占位记录
                self.logger.debug(f"📊 当日无daily_pnl记录，创建占位记录: {symbol} {transaction_date}")
                self._create_placeholder_daily_pnl(user_id, symbol, transaction_date, realized_pnl)
                
        except Exception as e:
            self.logger.error(f"❌ 更新当日已实现盈亏失败: {e}")
            # 重新抛出异常以触发事务回滚
            raise
    
    def _create_placeholder_daily_pnl(self, user_id: str, symbol: str, 
                                     transaction_date: str, realized_pnl: float):
        """
        创建占位的daily_pnl记录，仅包含已实现盈亏
        市场相关字段（market_price、unrealized_pnl等）由PnL计算器稍后补足
        """
        try:
            # 获取用户当前持仓信息来计算成本基础
            lots_data = self.storage.get_position_lots(user_id, symbol, active_only=True)
            
            if lots_data:
                # 从剩余批次计算总量和平均成本
                total_quantity = sum(lot['remaining_quantity'] for lot in lots_data)
                total_cost = sum(lot['remaining_quantity'] * lot['cost_basis'] for lot in lots_data)
                avg_cost = total_cost / total_quantity if total_quantity > 0 else 0.0
            else:
                # 如果没有活跃批次，使用最近的Position记录作为后备
                positions = self.storage.get_positions(user_id, active_only=True)
                position = next((p for p in positions if p['symbol'] == symbol), None)
                
                if position:
                    total_quantity = position['quantity']
                    avg_cost = position['avg_cost']
                    total_cost = position['total_cost']
                else:
                    # 完全没有持仓数据，创建最小占位记录
                    total_quantity = 0.0
                    avg_cost = 0.0
                    total_cost = 0.0
            
            # 计算已实现盈亏百分比（分母使用total_cost成本基础）
            realized_pnl_pct = (realized_pnl / total_cost) if total_cost > 0 else 0.0
            
            # 创建占位记录（market字段留空，等待PnL计算器补足）
            placeholder_data = {
                'user_id': user_id,
                'symbol': symbol,
                'valuation_date': transaction_date,
                'quantity': total_quantity,
                'avg_cost': avg_cost,
                'market_price': 0.0,  # 占位，需要PnL计算器补足
                'market_value': 0.0,  # 占位，需要PnL计算器补足
                'unrealized_pnl': 0.0,  # 占位，需要PnL计算器补足
                'unrealized_pnl_pct': 0.0,  # 占位，需要PnL计算器补足
                'total_cost': total_cost,
                'realized_pnl': realized_pnl,
                'realized_pnl_pct': realized_pnl_pct,
                'price_date': None,  # 占位，需要PnL计算器补足
                'is_stale_price': 1,  # 标记为需要刷新
            }
            
            self.storage.upsert_daily_pnl(placeholder_data)
            self.logger.info(f"📊 创建占位daily_pnl记录: {symbol} {transaction_date}, realized={realized_pnl:.2f}")
            
        except Exception as e:
            self.logger.error(f"❌ 创建占位daily_pnl记录失败: {e}")
            raise
    
    def get_lots_batch(self, user_symbols: List[tuple], active_only: bool = True, 
                      page_size: int = 1000, page_offset: int = 0) -> Dict[tuple, List[PositionLot]]:
        """
        批量获取多个用户/股票的批次数据（性能优化版本）
        
        Args:
            user_symbols: [(user_id, symbol), ...] 用户股票对列表
            active_only: 是否只返回活跃批次
            page_size: 每页大小，默认1000
            page_offset: 页偏移量，默认0
            
        Returns:
            Dict[tuple, List[PositionLot]]: {(user_id, symbol): [lots...]}
        """
        if not user_symbols:
            return {}
        
        results = {}
        
        # 分批查询以避免SQL IN子句过长
        batch_size = 50  # 每次查询最多50个用户-股票对
        
        for i in range(0, len(user_symbols), batch_size):
            batch = user_symbols[i:i + batch_size]
            
            # 构建批量查询条件
            user_ids = [user_id for user_id, symbol in batch]
            symbols = [symbol for user_id, symbol in batch]
            
            # 使用存储层的批量查询方法
            batch_lots_data = self.storage.get_position_lots_batch(
                user_ids, symbols, active_only, page_size, page_offset
            )
            
            # 转换为PositionLot对象并按(user_id, symbol)分组
            for (user_id, symbol), lots_data in batch_lots_data.items():
                lots = [PositionLot.from_dict(data) for data in lots_data]
                results[(user_id, symbol)] = lots
        
        return results
    
    def get_position_lots_paginated(self, user_id: str, symbol: str = None, 
                                   active_only: bool = True, page_size: int = 100, 
                                   page_offset: int = 0) -> tuple:
        """
        分页获取持仓批次（用于大数据量场景）
        
        Args:
            user_id: 用户ID
            symbol: 股票代码，可选
            active_only: 是否只返回活跃批次
            page_size: 每页大小
            page_offset: 页偏移量
            
        Returns:
            tuple: (lots, total_count, has_more)
        """
        lots_data, total_count, has_more = self.storage.get_position_lots_paginated(
            user_id, symbol, active_only, page_size, page_offset
        )
        
        lots = [PositionLot.from_dict(data) for data in lots_data]
        return lots, total_count, has_more
    
    def archive_closed_lots(self, older_than_days: int = 365) -> int:
        """
        归档老旧的已关闭批次（性能优化）
        
        Args:
            older_than_days: 归档超过多少天的已关闭批次
            
        Returns:
            int: 归档的批次数量
        """
        return self.storage.archive_closed_lots(older_than_days)
    
    def get_user_transactions(self, user_id: str, symbol: str = None,
                            start_date: str = None, end_date: str = None) -> List[Transaction]:
        """
        获取用户交易记录（完整实现从TransactionService迁移）
        
        Args:
            user_id: 用户ID
            symbol: 股票代码（可选）
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
            
        Returns:
            List[Transaction]: 交易记录列表
        """
        transactions_data = self.storage.get_transactions(
            user_id, symbol, start_date, end_date
        )
        return [Transaction.from_dict(data) for data in transactions_data]
    
    def validate_data_consistency(self, user_id: str, symbol: str = None) -> Dict[str, Any]:
        """
        验证批次数据与交易记录的一致性
        
        Args:
            user_id: 用户ID
            symbol: 股票代码，可选
            
        Returns:
            Dict: 一致性检查结果
        """
        issues = []
        statistics = {}
        
        # 获取需要检查的股票
        if symbol:
            symbols_to_check = [symbol]
        else:
            symbols_to_check = self.get_active_symbols(user_id)
        
        for sym in symbols_to_check:
            # 检查买入交易是否都有对应的批次
            buy_transactions = self.storage.get_transactions(user_id, sym, transaction_type='buy')
            lots = self.get_position_lots(user_id, sym, active_only=False)
            
            buy_count = len(buy_transactions)
            lot_count = len(lots)
            
            # 检查买入交易数量与批次数量是否匹配
            if buy_count != lot_count:
                issues.append({
                    'type': 'lot_transaction_mismatch',
                    'symbol': sym,
                    'buy_transactions': buy_count,
                    'position_lots': lot_count,
                    'description': f"买入交易数({buy_count})与批次数({lot_count})不匹配"
                })
            
            # 检查卖出分配的一致性
            sell_transactions = self.storage.get_transactions(user_id, sym, transaction_type='sell')
            for sell_txn in sell_transactions:
                allocations = self.get_sale_allocations(user_id, sym, sale_transaction_id=sell_txn['id'])
                
                # 验证分配数量总和是否等于卖出数量
                total_allocated = sum(alloc.quantity_sold for alloc in allocations)
                if abs(total_allocated - sell_txn['quantity']) > 0.0001:  # 允许小的浮点误差
                    issues.append({
                        'type': 'allocation_quantity_mismatch',
                        'symbol': sym,
                        'transaction_id': sell_txn['id'],
                        'sell_quantity': sell_txn['quantity'],
                        'allocated_quantity': total_allocated,
                        'description': f"卖出数量({sell_txn['quantity']})与分配总量({total_allocated})不匹配"
                    })
            
            # 统计信息
            statistics[sym] = {
                'buy_transactions': buy_count,
                'sell_transactions': len(sell_transactions),
                'position_lots': lot_count,
                'active_lots': len([lot for lot in lots if not lot.is_closed]),
                'closed_lots': len([lot for lot in lots if lot.is_closed])
            }
        
        return {
            'user_id': user_id,
            'symbols_checked': len(symbols_to_check),
            'issues_found': len(issues),
            'issues': issues,
            'statistics': statistics,
            'is_consistent': len(issues) == 0
        }
    
    def close(self):
        """关闭服务"""
        if self.storage:
            self.storage.close()