#!/usr/bin/env python3
"""
投资组合服务
提供投资组合管理和分析功能
"""

import logging
from datetime import datetime, date
from typing import List, Optional, Dict, Any

from ...data.storage import create_storage
from ..models.portfolio import Position, DailyPnL
from .transaction_service import TransactionService


class PortfolioService:
    """投资组合服务"""
    
    def __init__(self, storage, config):
        """
        初始化投资组合服务
        
        Args:
            storage: 存储实例
            config: 交易配置
        """
        self.storage = storage
        self.config = config
        self.transaction_service = TransactionService(storage, config)
        self.logger = logging.getLogger(__name__)
    
    def get_portfolio_summary(self, user_id: str, as_of_date: str = None) -> Dict[str, Any]:
        """
        获取投资组合摘要
        
        Args:
            user_id: 用户ID
            as_of_date: 截止日期（YYYY-MM-DD格式），如果为None则使用今天
            
        Returns:
            Dict: 投资组合摘要信息
        """
        if as_of_date is None:
            as_of_date = date.today().strftime('%Y-%m-%d')
        
        self.logger.info(f"获取投资组合摘要: {user_id} 截止 {as_of_date}")
        
        # 获取当前持仓
        positions = self.transaction_service.get_current_positions(user_id)
        
        if not positions:
            return {
                'user_id': user_id,
                'as_of_date': as_of_date,
                'total_positions': 0,
                'total_cost': 0.0,
                'total_market_value': 0.0,
                'total_unrealized_pnl': 0.0,
                'total_unrealized_pnl_pct': 0.0,
                'positions': []
            }
        
        # 获取每个持仓的最新市场价格和盈亏
        position_summaries = []
        total_cost = 0.0
        total_market_value = 0.0
        
        for position in positions:
            # 获取最新价格
            price_info = self.storage.get_latest_stock_price(
                position.symbol, as_of_date, 'adj_close'
            )
            
            if price_info:
                market_price = price_info[1]
                market_value = position.quantity * market_price
                unrealized_pnl = market_value - position.total_cost
                unrealized_pnl_pct = (unrealized_pnl / position.total_cost * 100) if position.total_cost > 0 else 0.0
                
                position_summary = {
                    'symbol': position.symbol,
                    'quantity': position.quantity,
                    'avg_cost': position.avg_cost,
                    'total_cost': position.total_cost,
                    'market_price': market_price,
                    'market_value': market_value,
                    'unrealized_pnl': unrealized_pnl,
                    'unrealized_pnl_pct': unrealized_pnl_pct,
                    'first_buy_date': position.first_buy_date,
                    'last_transaction_date': position.last_transaction_date
                }
                
                total_cost += position.total_cost
                total_market_value += market_value
            else:
                # 无价格数据
                position_summary = {
                    'symbol': position.symbol,
                    'quantity': position.quantity,
                    'avg_cost': position.avg_cost,
                    'total_cost': position.total_cost,
                    'market_price': None,
                    'market_value': None,
                    'unrealized_pnl': None,
                    'unrealized_pnl_pct': None,
                    'first_buy_date': position.first_buy_date,
                    'last_transaction_date': position.last_transaction_date,
                    'note': '无价格数据'
                }
                
                total_cost += position.total_cost
            
            position_summaries.append(position_summary)
        
        # 计算总体盈亏
        total_unrealized_pnl = total_market_value - total_cost
        total_unrealized_pnl_pct = (total_unrealized_pnl / total_cost * 100) if total_cost > 0 else 0.0
        
        return {
            'user_id': user_id,
            'as_of_date': as_of_date,
            'total_positions': len(positions),
            'total_cost': total_cost,
            'total_market_value': total_market_value,
            'total_unrealized_pnl': total_unrealized_pnl,
            'total_unrealized_pnl_pct': total_unrealized_pnl_pct,
            'positions': position_summaries
        }
    
    def get_portfolio_performance(self, user_id: str, start_date: str, 
                                end_date: str) -> Dict[str, Any]:
        """
        获取投资组合在指定期间的表现
        
        Args:
            user_id: 用户ID
            start_date: 开始日期（YYYY-MM-DD格式）
            end_date: 结束日期（YYYY-MM-DD格式）
            
        Returns:
            Dict: 投资组合表现数据
        """
        self.logger.info(f"获取投资组合表现: {user_id} {start_date} 至 {end_date}")
        
        # 获取期间内的每日盈亏记录
        daily_pnl_records = self.storage.get_daily_pnl(
            user_id, start_date=start_date, end_date=end_date
        )
        
        if not daily_pnl_records:
            return {
                'user_id': user_id,
                'start_date': start_date,
                'end_date': end_date,
                'total_days': 0,
                'performance_summary': {},
                'daily_records': []
            }
        
        # 按日期分组
        daily_data = {}
        for record in daily_pnl_records:
            date_key = record['valuation_date']
            if date_key not in daily_data:
                daily_data[date_key] = {
                    'date': date_key,
                    'total_cost': 0.0,
                    'total_market_value': 0.0,
                    'total_unrealized_pnl': 0.0,
                    'positions': []
                }
            
            daily_data[date_key]['total_cost'] += record['total_cost']
            daily_data[date_key]['total_market_value'] += record['market_value']
            daily_data[date_key]['total_unrealized_pnl'] += record['unrealized_pnl']
            daily_data[date_key]['positions'].append({
                'symbol': record['symbol'],
                'quantity': record['quantity'],
                'avg_cost': record['avg_cost'],
                'market_price': record['market_price'],
                'market_value': record['market_value'],
                'unrealized_pnl': record['unrealized_pnl'],
                'unrealized_pnl_pct': record['unrealized_pnl_pct']
            })
        
        # 计算每日盈亏百分比
        daily_records = []
        for date_key in sorted(daily_data.keys()):
            data = daily_data[date_key]
            total_unrealized_pnl_pct = (data['total_unrealized_pnl'] / data['total_cost'] * 100) if data['total_cost'] > 0 else 0.0
            data['total_unrealized_pnl_pct'] = total_unrealized_pnl_pct
            daily_records.append(data)
        
        # 计算表现统计（统一基于市值口径）
        if daily_records:
            start_market_value = daily_records[0]['total_market_value']
            end_market_value = daily_records[-1]['total_market_value']
            total_return = end_market_value - start_market_value
            total_return_pct = (total_return / start_market_value * 100) if start_market_value > 0 else 0.0
            
            # 计算最大回撤等指标（基于市值序列）
            peak_value = start_market_value
            max_drawdown = 0.0
            
            for record in daily_records:
                current_value = record['total_market_value']
                if current_value > peak_value:
                    peak_value = current_value
                else:
                    drawdown = (peak_value - current_value) / peak_value * 100
                    max_drawdown = max(max_drawdown, drawdown)
            
            # 计算总盈亏（基于成本对比）
            start_cost = daily_records[0]['total_cost']
            end_cost = daily_records[-1]['total_cost']
            total_pnl = end_market_value - end_cost
            total_pnl_pct = (total_pnl / end_cost * 100) if end_cost > 0 else 0.0
            
            performance_summary = {
                'start_market_value': start_market_value,
                'end_market_value': end_market_value,
                'market_value_return': total_return,
                'market_value_return_pct': total_return_pct,
                'total_cost': end_cost,
                'total_pnl': total_pnl,
                'total_pnl_pct': total_pnl_pct,
                'max_drawdown_pct': max_drawdown,
                'total_days': len(daily_records),
                'note': '市值收益基于期初期末市值，总盈亏基于成本与期末市值对比'
            }
        else:
            performance_summary = {}
        
        return {
            'user_id': user_id,
            'start_date': start_date,
            'end_date': end_date,
            'total_days': len(daily_records),
            'performance_summary': performance_summary,
            'daily_records': daily_records
        }
    
    def get_position_history(self, user_id: str, symbol: str, 
                           start_date: str = None, end_date: str = None) -> List[DailyPnL]:
        """
        获取特定股票的持仓历史
        
        Args:
            user_id: 用户ID
            symbol: 股票代码
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
            
        Returns:
            List[DailyPnL]: 每日盈亏记录列表
        """
        pnl_data = self.storage.get_daily_pnl(
            user_id, symbol, start_date, end_date
        )
        
        return [DailyPnL.from_dict(data) for data in pnl_data]