#!/usr/bin/env python3
"""
批次级别盈亏计算器
基于批次数据计算精确的每日盈亏
"""

import logging
from decimal import Decimal
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any

from ...data.storage import create_storage
from ..models.position_lot import PositionLot
from ..models.portfolio import DailyPnL
from ..config import DEFAULT_TRADING_CONFIG


class LotPnLCalculator:
    """批次级别盈亏计算器"""
    
    def __init__(self, storage, config):
        """
        初始化盈亏计算器
        
        Args:
            storage: 存储实例
            config: 交易配置
        """
        self.storage = storage
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def calculate_daily_pnl(self, symbol: str, 
                           calculation_date: str, 
                           price_source: str = 'adj_close') -> Optional[DailyPnL]:
        """
        计算指定日期的盈亏
        
        Args:
            symbol: 股票代码
            calculation_date: 计算日期（YYYY-MM-DD格式）
            price_source: 价格来源（adj_close或close）
            
        Returns:
            DailyPnL: 当日盈亏记录，如果无持仓则返回None
        """
        self.logger.debug(f"计算批次级别盈亏: {symbol} {calculation_date}")
        
        # 获取用户的所有活跃批次
        lots_data = self.storage.get_position_lots(symbol, active_only=True)
        if not lots_data:
            self.logger.debug(f"在 {calculation_date} 没有 {symbol} 的活跃持仓")
            return None
        
        # 转换为PositionLot对象
        lots = self._convert_to_position_lots(lots_data)
        
        # 获取市场价格
        market_price, price_date, is_stale = self._get_market_price(
            symbol, calculation_date, price_source
        )
        
        if market_price is None:
            self.logger.warning(f"无法获取 {symbol} 在 {calculation_date} 的价格")
            return None
        
        # 计算基于批次的未实现盈亏
        unrealized_pnl = self.calculate_unrealized_pnl_by_lots(lots, market_price)
        
        # 计算加权平均成本
        total_quantity = sum(lot.remaining_quantity for lot in lots)
        total_cost = sum(lot.total_cost for lot in lots)
        avg_cost = total_cost / total_quantity if total_quantity > 0 else 0.0
        
        # 计算市场价值
        market_value = total_quantity * market_price
        
        # 计算未实现盈亏百分比
        unrealized_pnl_pct = (unrealized_pnl / total_cost) if total_cost > 0 else 0.0
        
        # 获取当日已实现盈亏
        realized_pnl = self.storage.get_daily_realized_pnl(symbol, calculation_date)
        # 已实现盈亏百分比分母使用total_cost（成本基础），符合财务惯例
        realized_pnl_pct = (realized_pnl / total_cost) if total_cost > 0 else 0.0
        
        # 构造DailyPnL对象
        daily_pnl = DailyPnL(
            symbol=symbol,
            valuation_date=calculation_date,
            quantity=total_quantity,
            avg_cost=avg_cost,
            market_price=market_price,
            market_value=market_value,
            unrealized_pnl=unrealized_pnl,
            unrealized_pnl_pct=unrealized_pnl_pct,
            realized_pnl=realized_pnl,
            realized_pnl_pct=realized_pnl_pct,
            total_cost=total_cost,
            price_date=price_date,
            is_stale_price=is_stale,
            created_at=datetime.now()
        )
        
        # 检查是否是占位记录的补全
        if market_price > 0 and price_date:
            self._check_placeholder_completion(symbol, calculation_date, daily_pnl)
        
        # 一致性校验（如果不是陈旧价格）
        if not is_stale:
            self._validate_pnl_consistency(lots, market_price, unrealized_pnl, realized_pnl, calculation_date)
        
        self.logger.debug(f"✅ 批次级别盈亏计算完成: {total_quantity:.4f}股, "
                         f"未实现{unrealized_pnl:.2f}, 已实现{realized_pnl:.2f}")
        
        return daily_pnl
    
    def calculate_unrealized_pnl_by_lots(self, lots: List[PositionLot], 
                                       market_price: float) -> float:
        """
        基于批次计算未实现盈亏
        
        Args:
            lots: 持仓批次列表
            market_price: 市场价格
            
        Returns:
            float: 总未实现盈亏
        """
        total_unrealized_pnl = 0.0
        
        for lot in lots:
            if lot.remaining_quantity <= 0:
                continue
            
            # 计算该批次的未实现盈亏
            lot_unrealized_pnl = (market_price - lot.cost_basis) * lot.remaining_quantity
            total_unrealized_pnl += lot_unrealized_pnl
            
            self.logger.debug(f"    批次{lot.id}: {lot.remaining_quantity:.4f}@{lot.cost_basis:.4f} "
                            f"-> 未实现{lot_unrealized_pnl:.2f}")
        
        return total_unrealized_pnl
    
    def calculate_weighted_avg_cost(self, lots: List[PositionLot]) -> float:
        """
        计算基于批次的加权平均成本
        
        Args:
            lots: 持仓批次列表
            
        Returns:
            float: 加权平均成本
        """
        total_quantity = 0.0
        total_cost = 0.0
        
        for lot in lots:
            if lot.remaining_quantity <= 0:
                continue
            
            total_quantity += lot.remaining_quantity
            total_cost += lot.total_cost
        
        return total_cost / total_quantity if total_quantity > 0 else 0.0
    
    def batch_calculate_daily_pnl(self, symbols: List[str],
                                 start_date: str, end_date: str,
                                 price_source: str = 'adj_close',
                                 only_trading_days: bool = False) -> Dict[str, List[DailyPnL]]:
        """
        批量计算历史盈亏（优化版，减少N+1查询）
        
        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            price_source: 价格来源
            only_trading_days: 是否仅计算交易日
            
        Returns:
            Dict[str, List[DailyPnL]]: 按股票代码分组的每日盈亏记录
        """
        self.logger.info(f"批量计算批次级别盈亏: {len(symbols)}只股票, "
                        f"{start_date} 到 {end_date}")
        
        results = {}
        
        # 优化：批量获取所有symbols的lots数据，避免N+1查询
        all_lots_by_symbol = {}
        for symbol in symbols:
            lots_data = self.storage.get_position_lots(symbol, active_only=True)
            if lots_data:
                all_lots_by_symbol[symbol] = self._convert_to_position_lots(lots_data)
        
        # 生成日期范围
        dates = self._generate_date_range(start_date, end_date, only_trading_days)
        
        # 优化：批量获取价格数据，减少数据库往返
        price_cache = self._batch_get_prices(symbols, dates, price_source)
        
        for symbol in symbols:
            self.logger.debug(f"处理 {symbol}...")
            symbol_results = []
            
            lots = all_lots_by_symbol.get(symbol, [])
            if not lots:
                self.logger.debug(f"没有 {symbol} 的活跃持仓")
                continue
                
            for date in dates:
                # 从缓存获取价格
                price_info = price_cache.get((symbol, date))
                if not price_info:
                    continue

                market_price, price_date, is_stale = price_info

                # 过滤出在当前日期之前已购买的批次
                active_lots_on_date = [lot for lot in lots if lot.purchase_date <= date]
                if not active_lots_on_date:
                    continue  # 该日期没有持仓，跳过

                # 计算加权平均成本和其他指标
                # 注意：市值包含所有批次（含DRIP），但成本只计算非DRIP批次
                total_quantity = sum(lot.remaining_quantity for lot in active_lots_on_date)
                market_value = total_quantity * market_price

                # 排除DRIP批次的成本（DRIP是用分红买的，不是自己投入的钱）
                def is_drip(lot):
                    return lot.notes and 'Dividend Reinvestment' in lot.notes

                non_drip_lots = [lot for lot in active_lots_on_date if not is_drip(lot)]
                total_cost = sum(lot.total_cost for lot in non_drip_lots)
                non_drip_quantity = sum(lot.remaining_quantity for lot in non_drip_lots)
                avg_cost = total_cost / non_drip_quantity if non_drip_quantity > Decimal('0') else Decimal('0.0')

                # 未实现盈亏 = 市值(所有股份) - 成本(排除DRIP)
                unrealized_pnl = market_value - total_cost
                unrealized_pnl_pct = (unrealized_pnl / total_cost) if total_cost > Decimal('0') else Decimal('0.0')
                
                # 获取当日已实现盈亏
                realized_pnl = self.storage.get_daily_realized_pnl(symbol, date)
                realized_pnl_pct = (realized_pnl / total_cost) if total_cost > Decimal('0') else Decimal('0.0')
                
                # 构造DailyPnL对象
                daily_pnl = DailyPnL(
                    symbol=symbol,
                    valuation_date=date,
                    quantity=total_quantity,
                    avg_cost=avg_cost,
                    market_price=market_price,
                    market_value=market_value,
                    unrealized_pnl=unrealized_pnl,
                    unrealized_pnl_pct=unrealized_pnl_pct,
                    realized_pnl=realized_pnl,
                    realized_pnl_pct=realized_pnl_pct,
                    total_cost=total_cost,
                    price_date=price_date,
                    is_stale_price=is_stale,
                    created_at=datetime.now()
                )
                
                symbol_results.append(daily_pnl)
            
            if symbol_results:
                results[symbol] = symbol_results
                self.logger.debug(f"  {symbol}: 计算了 {len(symbol_results)} 个交易日")
        
        return results
    
    def save_daily_pnl(self, daily_pnl: DailyPnL) -> int:
        """保存每日盈亏记录到数据库"""
        pnl_data = {
            'symbol': daily_pnl.symbol,
            'valuation_date': daily_pnl.valuation_date,
            'quantity': daily_pnl.quantity,
            'avg_cost': daily_pnl.avg_cost,
            'market_price': daily_pnl.market_price,
            'market_value': daily_pnl.market_value,
            'unrealized_pnl': daily_pnl.unrealized_pnl,
            'unrealized_pnl_pct': daily_pnl.unrealized_pnl_pct,
            'realized_pnl': daily_pnl.realized_pnl,
            'realized_pnl_pct': daily_pnl.realized_pnl_pct,
            'total_cost': daily_pnl.total_cost,
            'price_date': daily_pnl.price_date,
            'is_stale_price': daily_pnl.is_stale_price
        }
        
        return self.storage.upsert_daily_pnl(pnl_data)
    
    def _convert_to_position_lots(self, lots_data: List[Dict[str, Any]]) -> List[PositionLot]:
        """将数据库记录转换为PositionLot对象"""
        lots = []
        for lot_data in lots_data:
            lot = PositionLot(
                id=lot_data['id'],
                symbol=lot_data['symbol'],
                transaction_id=lot_data['transaction_id'],
                original_quantity=lot_data['original_quantity'],
                remaining_quantity=lot_data['remaining_quantity'],
                cost_basis=lot_data['cost_basis'],
                purchase_date=lot_data['purchase_date'],
                is_closed=bool(lot_data['is_closed']),
                created_at=datetime.fromisoformat(lot_data.get('created_at', '')) if lot_data.get('created_at') else None,
                updated_at=datetime.fromisoformat(lot_data.get('updated_at', '')) if lot_data.get('updated_at') else None,
                notes=lot_data.get('notes')  # 包含notes用于识别DRIP
            )
            lots.append(lot)
        return lots
    
    def _get_market_price(self, symbol: str, date: str, 
                         price_source: str) -> tuple[Optional[float], Optional[str], bool]:
        """
        获取市场价格
        
        Returns:
            tuple: (价格, 价格日期, 是否为陈旧价格)
        """
        # 首先尝试获取指定日期的价格
        price = self.storage.get_stock_price_for_date(symbol, date, price_source)
        if price is not None:
            return price, date, False
        
        # 如果没有找到，尝试获取最近的价格（回填）
        latest_price_info = self.storage.get_latest_stock_price(symbol, date, price_source)
        if latest_price_info:
            price_date, price = latest_price_info
            is_stale = price_date != date
            return price, price_date, is_stale
        
        return None, None, False
    
    def _generate_date_range(self, start_date: str, end_date: str, 
                           only_trading_days: bool, symbols: List[str] = None) -> List[str]:
        """
        生成日期范围
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            only_trading_days: 是否仅包含交易日
            symbols: 可选，指定股票代码列表，用于交易日过滤
            
        Returns:
            List[str]: 日期字符串列表
        """
        if only_trading_days and symbols:
            # 获取指定symbols的联合交易日
            T = self.storage.config.Tables.STOCK_PRICES
            F = self.storage.config.Fields
            
            placeholders = ','.join(['?' for _ in symbols])
            sql = f"""
            SELECT DISTINCT {F.StockPrices.DATE} 
            FROM {T} 
            WHERE {F.StockPrices.DATE} >= ? AND {F.StockPrices.DATE} <= ?
            AND {F.SYMBOL} IN ({placeholders})
            ORDER BY {F.StockPrices.DATE}
            """
            params = [start_date, end_date] + symbols
            
            self.storage.cursor.execute(sql, params)
            rows = self.storage.cursor.fetchall()
            return [row[0] for row in rows]
        
        elif only_trading_days:
            # 获取所有股票的交易日
            T = self.storage.config.Tables.STOCK_PRICES
            F = self.storage.config.Fields
            
            sql = f"""
            SELECT DISTINCT {F.StockPrices.DATE} 
            FROM {T} 
            WHERE {F.StockPrices.DATE} >= ? AND {F.StockPrices.DATE} <= ?
            ORDER BY {F.StockPrices.DATE}
            """
            
            self.storage.cursor.execute(sql, (start_date, end_date))
            rows = self.storage.cursor.fetchall()
            return [row[0] for row in rows]
        
        else:
            # 生成自然日期范围
            dates = []
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            
            current = start
            while current <= end:
                dates.append(current.strftime('%Y-%m-%d'))
                current = current + timedelta(days=1)
            
            return dates
    
    def _batch_get_prices(self, symbols: List[str], dates: List[str], 
                         price_source: str) -> Dict[tuple, tuple]:
        """
        批量获取价格数据，减少数据库往返
        
        Returns:
            Dict[(symbol, date), (price, price_date, is_stale)]: 价格缓存
        """
        price_cache = {}
        
        for symbol in symbols:
            for date in dates:
                # 首先尝试获取指定日期的价格
                price = self.storage.get_stock_price_for_date(symbol, date, price_source)
                if price is not None:
                    price_cache[(symbol, date)] = (price, date, False)
                else:
                    # 尝试获取最近的价格（回填）
                    latest_price_info = self.storage.get_latest_stock_price(symbol, date, price_source)
                    if latest_price_info:
                        price_date, latest_price = latest_price_info
                        is_stale = price_date != date
                        price_cache[(symbol, date)] = (latest_price, price_date, is_stale)
        
        return price_cache
    
    def _validate_pnl_consistency(self, lots: List[PositionLot], market_price: float,
                                 calculated_unrealized: float, calculated_realized: float,
                                 calculation_date: str):
        """
        验证PnL计算的一致性
        
        Args:
            lots: 持仓批次列表
            market_price: 市场价格
            calculated_unrealized: 已计算的未实现盈亏
            calculated_realized: 已计算的已实现盈亏
            calculation_date: 计算日期
        """
        try:
            # 重新计算未实现盈亏
            recalc_unrealized = self.calculate_unrealized_pnl_by_lots(lots, market_price)
            
            # 检查未实现盈亏差异
            unrealized_diff = abs(calculated_unrealized - recalc_unrealized)
            if unrealized_diff > 0.01:  # 容忍1分钱的浮点误差
                self.logger.warning(f"⚠️  未实现盈亏不一致: 计算值{calculated_unrealized:.2f}, "
                                  f"重算值{recalc_unrealized:.2f}, 差异{unrealized_diff:.2f}")
            
            # 检查批次数量与计算结果的一致性
            total_quantity = sum(lot.remaining_quantity for lot in lots)
            total_cost_from_lots = sum(lot.remaining_quantity * lot.cost_basis for lot in lots)
            market_value_from_lots = total_quantity * market_price
            
            calculated_market_value = total_quantity * market_price
            if abs(market_value_from_lots - calculated_market_value) > 0.01:
                self.logger.warning(f"⚠️  市场价值不一致: lots计算{market_value_from_lots:.2f}, "
                                  f"直接计算{calculated_market_value:.2f}")
            
            # 记录校验结果（debug级别）
            self.logger.debug(f"📋 一致性校验通过: {calculation_date}, "
                            f"未实现差异{unrealized_diff:.4f}, 总量{total_quantity:.4f}")
            
        except Exception as e:
            self.logger.error(f"❌ 一致性校验失败: {e}")
            # 不重新抛出异常，避免影响主流程
    
    def _check_placeholder_completion(self, symbol: str, 
                                    calculation_date: str, daily_pnl: DailyPnL):
        """
        检查是否是对占位记录的补全
        
        Args:
            symbol: 股票代码
            calculation_date: 计算日期
            daily_pnl: 当前计算的PnL记录
        """
        try:
            # 获取现有的daily_pnl记录
            existing_records = self.storage.get_daily_pnl(
                symbol, calculation_date, calculation_date
            )
            
            if existing_records:
                existing = existing_records[0]
                # 检查是否是占位记录（market_price为0或is_stale_price为1）
                is_placeholder = (
                    existing.get('market_price', 0) == 0 or 
                    existing.get('is_stale_price', 0) == 1
                )
                
                if is_placeholder:
                    self.logger.info(f"📊 补全占位记录: {symbol} {calculation_date}, "
                                   f"市价{daily_pnl.market_price:.4f}, "
                                   f"未实现{daily_pnl.unrealized_pnl:.2f}")
                    
                    # 验证已实现盈亏是否保持一致
                    existing_realized = existing.get('realized_pnl', 0)
                    if abs(existing_realized - daily_pnl.realized_pnl) > 0.01:
                        self.logger.warning(f"⚠️  补全时已实现盈亏发生变化: "
                                          f"原值{existing_realized:.2f}, "
                                          f"新值{daily_pnl.realized_pnl:.2f}")
                
        except Exception as e:
            self.logger.error(f"❌ 占位记录检查失败: {e}")
            # 不重新抛出异常，避免影响主流程
    
    def close(self):
        """关闭计算器"""
        if self.storage:
            self.storage.close()