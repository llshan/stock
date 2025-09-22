#!/usr/bin/env python3
"""
盈亏计算器
负责计算每日Capital Gain/Loss，支持批量计算和历史数据重算
"""

import logging
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any, Tuple

from ...data.storage import create_storage
from ..models.portfolio import Position, DailyPnL
from ..services.transaction_service import TransactionService
from ..config import DEFAULT_TRADING_CONFIG
from .lot_pnl_calculator import LotPnLCalculator


class PnLCalculator:
    """盈亏计算器"""
    
    def __init__(self, storage, config, price_field: str = 'adj_close', 
                 only_trading_days: bool = False):
        """
        初始化盈亏计算器
        
        Args:
            storage: 存储实例
            config: 交易配置
            price_field: 估值价格来源字段，默认使用adj_close
            only_trading_days: 是否只在交易日计算，默认False（包含自然日）
        """
        self.storage = storage
        self.config = config
        self.transaction_service = TransactionService(storage, config)
        self.price_field = price_field
        self.only_trading_days = only_trading_days
        self.logger = logging.getLogger(__name__)
        
        # 使用批次级别计算器作为底层实现
        self.lot_calculator = LotPnLCalculator(storage, config)
    
    def calculate_daily_pnl(self, user_id: str, symbol: str, 
                           calculation_date: str) -> Optional[DailyPnL]:
        """
        计算指定日期的盈亏（基于批次级别计算）
        
        Args:
            user_id: 用户ID
            symbol: 股票代码
            calculation_date: 计算日期（YYYY-MM-DD格式）
            
        Returns:
            Optional[DailyPnL]: 每日盈亏记录，如果无持仓或无价格数据则返回None
        """
        # 委托给批次级别计算器处理
        daily_pnl = self.lot_calculator.calculate_daily_pnl(
            user_id, symbol, calculation_date, self.price_field
        )
        
        if daily_pnl:
            # 保存到数据库
            pnl_id = self.lot_calculator.save_daily_pnl(daily_pnl)
            daily_pnl.id = pnl_id
        
        return daily_pnl
    
    def calculate_all_positions_pnl(self, user_id: str, 
                                   calculation_date: str) -> List[DailyPnL]:
        """
        计算用户所有持仓在指定日期的盈亏
        
        Args:
            user_id: 用户ID
            calculation_date: 计算日期（YYYY-MM-DD格式）
            
        Returns:
            List[DailyPnL]: 所有持仓的盈亏记录列表
        """
        self.logger.info(f"计算所有持仓盈亏: {user_id} {calculation_date}")
        
        # 直接获取所有活跃持仓的股票代码，不再经过Position汇总
        symbols = self.transaction_service.get_active_symbols(user_id)
        if not symbols:
            self.logger.info(f"用户无活跃持仓: {user_id}")
            return []
        
        daily_pnls = []
        
        for symbol in symbols:
            try:
                daily_pnl = self.calculate_daily_pnl(
                    user_id, symbol, calculation_date
                )
                if daily_pnl:
                    daily_pnls.append(daily_pnl)
            except Exception as e:
                self.logger.error(f"计算持仓盈亏失败: {symbol} - {e}")
                continue
        
        self.logger.info(f"✅ 完成所有持仓盈亏计算: {len(daily_pnls)}/{len(symbols)}")
        return daily_pnls
    
    def batch_calculate_historical_pnl(self, user_id: str, start_date: str, 
                                      end_date: str, symbols: List[str] = None) -> Dict[str, int]:
        """
        批量计算历史盈亏数据（基于批次级别计算）
        
        Args:
            user_id: 用户ID
            start_date: 开始日期（YYYY-MM-DD格式）
            end_date: 结束日期（YYYY-MM-DD格式）
            symbols: 指定股票代码列表，如果为None则计算所有持仓
            
        Returns:
            Dict[str, int]: 计算结果统计 {'total_days': 总天数, 'calculated_records': 计算记录数}
        """
        self.logger.info(f"批量计算历史盈亏: {user_id} {start_date} 至 {end_date}")
        
        # 校验输入参数
        self._validate_calculation_inputs(user_id, start_date, end_date)
        
        if symbols is None:
            # 获取用户的所有活跃股票代码（不再依赖Position汇总对象）
            symbols = self.transaction_service.get_active_symbols(user_id)
        
        if not symbols:
            self.logger.info("无持仓股票，跳过批量计算")
            return {'total_days': 0, 'calculated_records': 0}
        
        # 委托给批次级别计算器进行批量计算
        result_by_symbol = self.lot_calculator.batch_calculate_daily_pnl(
            user_id, symbols, start_date, end_date, self.price_field, self.only_trading_days
        )
        
        # 统计结果
        calculated_records = 0
        for symbol_results in result_by_symbol.values():
            calculated_records += len(symbol_results)
        
        # 计算总天数（为指定symbols生成联合交易日）
        date_range = self._generate_date_range(start_date, end_date, symbols)
        
        result = {
            'total_days': len(date_range),
            'calculated_records': calculated_records,
            'symbols_processed': len(symbols)
        }
        
        self.logger.info(f"✅ 批量计算完成: {result}")
        return result
    
    def recalculate_position_pnl(self, user_id: str, symbol: str, 
                                recompute_days: int = 7) -> int:
        """
        重新计算指定持仓的最近N天盈亏
        
        Args:
            user_id: 用户ID
            symbol: 股票代码
            recompute_days: 重算天数，默认最近7天
            
        Returns:
            int: 重算的记录数
        """
        self.logger.info(f"重算持仓盈亏: {user_id} {symbol} 最近{recompute_days}天")
        
        # 计算日期范围
        end_date = date.today()
        start_date = end_date - timedelta(days=recompute_days)
        
        # 批量重算
        result = self.batch_calculate_historical_pnl(
            user_id, 
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d'),
            [symbol]
        )
        
        return result['calculated_records']
    
    def get_price_availability_report(self, symbols: List[str], 
                                    start_date: str, end_date: str) -> Dict[str, Dict]:
        """
        获取价格数据可用性报告
        
        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            Dict: 每个股票的价格数据可用性报告
        """
        report = {}
        date_range = self._generate_date_range(start_date, end_date, symbols)
        
        for symbol in symbols:
            available_dates = []
            missing_dates = []
            stale_dates = []
            
            for calc_date in date_range:
                calc_date_str = calc_date.strftime('%Y-%m-%d')
                
                # 检查当日价格
                current_price = self.storage.get_stock_price_for_date(
                    symbol, calc_date_str, self.price_field
                )
                
                if current_price is not None:
                    available_dates.append(calc_date_str)
                else:
                    # 尝试获取最近价格
                    latest_price_info = self.storage.get_latest_stock_price(
                        symbol, calc_date_str, self.price_field
                    )
                    
                    if latest_price_info:
                        stale_dates.append({
                            'date': calc_date_str,
                            'latest_price_date': latest_price_info[0],
                            'price': latest_price_info[1]
                        })
                    else:
                        missing_dates.append(calc_date_str)
            
            report[symbol] = {
                'total_days': len(date_range),
                'available_days': len(available_dates),
                'stale_days': len(stale_dates),
                'missing_days': len(missing_dates),
                'coverage_pct': len(available_dates) / len(date_range) * 100,
                'available_dates': available_dates[:5],  # 前5个示例
                'missing_dates': missing_dates[:5],     # 前5个示例
                'stale_dates': stale_dates[:5]          # 前5个示例
            }
        
        return report
    
    def _get_market_price(self, symbol: str, valuation_date: str) -> Optional[tuple]:
        """
        获取指定日期的市场价格，支持回填策略
        
        Args:
            symbol: 股票代码
            valuation_date: 估值日期
            
        Returns:
            Optional[tuple]: (price, price_date, is_stale) 或 None
        """
        # 首先尝试获取当日价格
        price = self.storage.get_stock_price_for_date(
            symbol, valuation_date, self.price_field
        )
        
        if price is not None:
            return (price, valuation_date, False)
        
        # 如果当日无价格，尝试获取最近的交易日价格（回填策略）
        latest_price_info = self.storage.get_latest_stock_price(
            symbol, valuation_date, self.price_field
        )
        
        if latest_price_info:
            latest_date, latest_price = latest_price_info
            self.logger.debug(f"使用回填价格: {symbol} {valuation_date} -> {latest_date} {latest_price}")
            return (latest_price, latest_date, True)
        
        return None
    
    def _generate_date_range(self, start_date: str, end_date: str, symbols: List[str] = None) -> List[date]:
        """
        生成日期范围
        
        Args:
            start_date: 开始日期
            end_date: 结束日期  
            symbols: 可选，指定股票代码列表，用于交易日过滤
            
        Returns:
            List[date]: 日期列表
        """
        if self.only_trading_days:
            return self._get_trading_days(start_date, end_date, symbols)
        else:
            return self._get_natural_days(start_date, end_date)
    
    def _get_natural_days(self, start_date: str, end_date: str) -> List[date]:
        """生成自然日期范围"""
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        dates = []
        current_date = start
        while current_date <= end:
            dates.append(current_date)
            current_date += timedelta(days=1)
        
        return dates
    
    def _get_trading_days(self, start_date: str, end_date: str, symbols: List[str] = None) -> List[date]:
        """
        获取有价格数据的交易日
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            symbols: 可选，指定股票代码列表，如果提供则只返回这些股票的联合交易日
            
        Returns:
            List[date]: 交易日列表
        """
        self._check_connection("_get_trading_days")
        
        T = self.storage.config.Tables.STOCK_PRICES
        F = self.storage.config.Fields
        
        if symbols:
            # 获取指定symbols的联合交易日
            placeholders = ','.join(['?' for _ in symbols])
            sql = f"""
            SELECT DISTINCT {F.StockPrices.DATE} 
            FROM {T} 
            WHERE {F.StockPrices.DATE} >= ? AND {F.StockPrices.DATE} <= ?
            AND {F.SYMBOL} IN ({placeholders})
            ORDER BY {F.StockPrices.DATE}
            """
            params = [start_date, end_date] + symbols
        else:
            # 获取时间范围内的所有交易日（去重）
            sql = f"""
            SELECT DISTINCT {F.StockPrices.DATE} 
            FROM {T} 
            WHERE {F.StockPrices.DATE} >= ? AND {F.StockPrices.DATE} <= ?
            ORDER BY {F.StockPrices.DATE}
            """
            params = [start_date, end_date]
        
        self.storage.cursor.execute(sql, params)
        rows = self.storage.cursor.fetchall()
        
        # 转换为date对象
        trading_days = []
        for row in rows:
            try:
                trading_day = datetime.strptime(row[0], '%Y-%m-%d').date()
                trading_days.append(trading_day)
            except ValueError:
                self.logger.warning(f"无效的日期格式: {row[0]}")
                continue
        
        return trading_days
    
    def _check_connection(self, method_name: str):
        """检查存储连接"""
        if not self.storage or not hasattr(self.storage, 'cursor') or not self.storage.cursor:
            raise RuntimeError(f"{method_name}: 存储连接不可用")
    
    def _validate_calculation_inputs(self, user_id: str, start_date: str, end_date: str):
        """校验计算输入参数"""
        # 用户ID校验
        if not user_id or not user_id.strip():
            raise ValueError("盈亏计算错误：用户ID不能为空")
        
        if len(user_id.strip()) > self.config.max_user_id_length:
            raise ValueError(f"盈亏计算错误：用户ID长度不能超过{self.config.max_user_id_length}个字符")
        
        # 日期格式校验
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError as e:
            raise ValueError(f"盈亏计算错误：日期格式错误，应为YYYY-MM-DD。开始日期: {start_date}，结束日期: {end_date}")
        
        # 日期逻辑校验
        if start_dt.date() > end_dt.date():
            raise ValueError(f"盈亏计算错误：开始日期({start_date})不能晚于结束日期({end_date})")
        
        # 未来日期校验
        today = datetime.now().date()
        if start_dt.date() > today:
            raise ValueError(f"盈亏计算错误：不能计算未来日期的盈亏，当前日期: {today}，开始日期: {start_date}")
        
        if end_dt.date() > today:
            raise ValueError(f"盈亏计算错误：不能计算未来日期的盈亏，当前日期: {today}，结束日期: {end_date}")
        
        # 历史日期合理性校验
        min_date = date(1990, 1, 1)
        if start_dt.date() < min_date:
            raise ValueError(f"盈亏计算错误：开始日期不能早于1990-01-01，当前值: {start_date}")
        
        # 计算时间跨度限制（使用配置化的限制）
        time_span = (end_dt.date() - start_dt.date()).days
        if time_span > self.config.max_calculation_days:
            max_years = self.config.max_calculation_days // 365
            raise ValueError(f"盈亏计算错误：计算时间跨度不能超过{max_years}年({self.config.max_calculation_days}天)，当前跨度: {time_span}天")