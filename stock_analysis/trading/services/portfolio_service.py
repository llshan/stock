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
    
    def get_portfolio_summary(self, as_of_date: str = None) -> Dict[str, Any]:
        """
        获取投资组合摘要

        Args:
            as_of_date: 截止日期（YYYY-MM-DD格式），如果为None则使用今天

        Returns:
            Dict: 投资组合摘要信息
        """
        if as_of_date is None:
            as_of_date = date.today().strftime('%Y-%m-%d')

        self.logger.info(f"获取投资组合摘要: 截止 {as_of_date}")

        # 获取截止到指定日期的持仓（修复bug：不再获取所有当前持仓）
        positions = self.transaction_service.get_positions_as_of_date(as_of_date)
        
        if not positions:
            return {
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
                market_price = float(price_info[1])
                market_value = float(position.quantity) * market_price
                unrealized_pnl = market_value - float(position.total_cost)
                unrealized_pnl_pct = (unrealized_pnl / float(position.total_cost) * 100) if position.total_cost > 0 else 0.0
                
                position_summary = {
                    'symbol': position.symbol,
                    'quantity': float(position.quantity),
                    'avg_cost': float(position.avg_cost),
                    'total_cost': float(position.total_cost),
                    'market_price': market_price,
                    'market_value': market_value,
                    'unrealized_pnl': unrealized_pnl,
                    'unrealized_pnl_pct': unrealized_pnl_pct,
                    'first_buy_date': position.first_buy_date,
                    'last_transaction_date': position.last_transaction_date
                }
                
                total_cost += float(position.total_cost)
                total_market_value += market_value
            else:
                # 无价格数据
                position_summary = {
                    'symbol': position.symbol,
                    'quantity': float(position.quantity),
                    'avg_cost': float(position.avg_cost),
                    'total_cost': float(position.total_cost),
                    'market_price': None,
                    'market_value': None,
                    'unrealized_pnl': None,
                    'unrealized_pnl_pct': None,
                    'first_buy_date': position.first_buy_date,
                    'last_transaction_date': position.last_transaction_date,
                    'note': '无价格数据'
                }

                total_cost += float(position.total_cost)
            
            position_summaries.append(position_summary)
        
        # 计算总体盈亏
        total_unrealized_pnl = total_market_value - total_cost
        total_unrealized_pnl_pct = (total_unrealized_pnl / total_cost * 100) if total_cost > 0 else 0.0
        
        return {
            'as_of_date': as_of_date,
            'total_positions': len(positions),
            'total_cost': total_cost,
            'total_market_value': total_market_value,
            'total_unrealized_pnl': total_unrealized_pnl,
            'total_unrealized_pnl_pct': total_unrealized_pnl_pct,
            'positions': position_summaries
        }
    
    def get_portfolio_performance(self, start_date: str, 
                                end_date: str) -> Dict[str, Any]:
        """
        获取投资组合在指定期间的表现
        
        Args:
            start_date: 开始日期（YYYY-MM-DD格式）
            end_date: 结束日期（YYYY-MM-DD格式）
            
        Returns:
            Dict: 投资组合表现数据
        """
        self.logger.info(f"获取投资组合表现: {start_date} 至 {end_date}")
        
        # 获取期间内的每日盈亏记录
        daily_pnl_records = self.storage.get_daily_pnl(
            start_date=start_date, end_date=end_date
        )
        
        if not daily_pnl_records:
            return {
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
            'start_date': start_date,
            'end_date': end_date,
            'total_days': len(daily_records),
            'performance_summary': performance_summary,
            'daily_records': daily_records
        }

    def get_enhanced_portfolio_analysis(self, as_of_date: str = None) -> Dict[str, Any]:
        """
        获取增强版投资组合分析
        
        Args:
            as_of_date: 截止日期（YYYY-MM-DD格式），如果为None则使用今天
            
        Returns:
            Dict: 包含详细分析的投资组合信息
        """
        if as_of_date is None:
            as_of_date = date.today().strftime('%Y-%m-%d')
        
        self.logger.info(f"生成增强版投资组合分析: 截止 {as_of_date}")
        
        # 获取基础组合摘要
        basic_summary = self.get_portfolio_summary(as_of_date)
        
        if basic_summary['total_positions'] == 0:
            return self._empty_enhanced_analysis(as_of_date)
        
        # 获取交易记录用于平台分析
        transactions = self._get_transaction_details()
        
        # 获取详细分析数据
        historical_performance = self._get_historical_performance(basic_summary['positions'])
        detailed_risk = self._get_detailed_risk_assessment(basic_summary['positions'], basic_summary['total_cost'])
        strategy_insights = self._generate_strategy_insights(
            basic_summary['positions'], 
            basic_summary['total_cost'], 
            historical_performance, 
            detailed_risk
        )
        
        # 获取已实现盈亏
        realized_gains = self.get_realized_gains()

        # 计算总体投资表现（包含当前持仓和已卖出股票）
        overall_performance = self._calculate_overall_performance(basic_summary, realized_gains)

        # 分析结果
        analysis = {
            'analysis_date': as_of_date,
            'basic_summary': basic_summary,
            'sector_analysis': self._analyze_by_sectors(basic_summary['positions']),
            'platform_analysis': self._analyze_by_platforms(basic_summary['positions'], transactions),
            'risk_metrics': detailed_risk,
            'performance_analysis': self._analyze_performance(basic_summary['positions']),
            'historical_performance': historical_performance,
            'strategy_insights': strategy_insights,
            'recommendations': self._generate_recommendations(basic_summary['positions'], basic_summary['total_cost']),
            'realized_gains': realized_gains,
            'overall_performance': overall_performance
        }

        return analysis

    def _empty_enhanced_analysis(self, as_of_date: str) -> Dict[str, Any]:
        """返回空的增强分析结果"""
        return {
            'analysis_date': as_of_date,
            'basic_summary': {
                'as_of_date': as_of_date,
                'total_positions': 0,
                'total_cost': 0.0,
                'total_market_value': 0.0,
                'total_unrealized_pnl': 0.0,
                'total_unrealized_pnl_pct': 0.0,
                'positions': []
            },
            'sector_analysis': {'message': '暂无持仓数据'},
            'platform_analysis': {'message': '暂无交易数据'},
            'risk_metrics': {'message': '无法计算风险指标'},
            'performance_analysis': {'message': '无表现数据'},
            'recommendations': ['建立初始投资组合']
        }

    def _get_transaction_details(self) -> List[Dict]:
        """获取交易详情"""
        # 查询所有交易记录
        try:
            query = """
            SELECT symbol, transaction_type, quantity, price, 
                   transaction_date, platform, external_id
            FROM transactions 
            ORDER BY symbol, transaction_date
            """
            transactions = []
            rows = self.storage.cursor.execute(query).fetchall()
            columns = [desc[0] for desc in self.storage.cursor.description]
            
            for row in rows:
                transaction = dict(zip(columns, row))
                transactions.append(transaction)
            
            return transactions
        except Exception as e:
            self.logger.warning(f"获取交易详情失败: {e}")
            return []

    def _get_company_info(self, symbol: str) -> Dict[str, str]:
        """从数据库获取公司信息"""
        try:
            query = """
            SELECT company_name, sector, industry, description
            FROM stocks WHERE symbol = ?
            """
            result = self.storage.cursor.execute(query, (symbol,)).fetchone()

            if result and result[0]:  # 确保有公司名称
                company_name, sector, industry, description = result

                # 根据行业判断类型
                stock_type = 'ETF' if 'ETF' in sector else '个股'

                return {
                    'type': stock_type,
                    'category': company_name,
                    'sector': sector or '其他',
                    'company_name': company_name,
                    'description': description or f'{symbol} 股票'
                }
            else:
                # 回退到默认值
                return {
                    'type': '未知',
                    'category': symbol,
                    'sector': '其他',
                    'company_name': symbol,
                    'description': f'{symbol} 股票'
                }
        except Exception as e:
            self.logger.warning(f"获取{symbol}公司信息失败: {e}")
            return {
                'type': '未知',
                'category': symbol,
                'sector': '其他',
                'company_name': symbol,
                'description': f'{symbol} 股票'
            }

    def _analyze_by_sectors(self, positions: List[Dict]) -> Dict[str, Any]:
        """按行业分析持仓"""

        etf_positions = []
        stock_positions = []
        etf_total_cost = 0.0
        etf_total_value = 0.0
        stock_total_cost = 0.0
        stock_total_value = 0.0

        for pos in positions:
            symbol = pos['symbol']
            category_info = self._get_company_info(symbol)

            pos_with_category = pos.copy()
            pos_with_category.update(category_info)

            if category_info['type'] == 'ETF':
                etf_positions.append(pos_with_category)
                etf_total_cost += pos['total_cost']
                if pos['market_value']:
                    etf_total_value += pos['market_value']
            else:
                stock_positions.append(pos_with_category)
                stock_total_cost += pos['total_cost']
                if pos['market_value']:
                    stock_total_value += pos['market_value']

        # 按总盈亏从大到小排序（需要处理None值）
        def get_pnl(pos):
            if pos.get('unrealized_pnl') is not None:
                return pos['unrealized_pnl']
            return float('-inf')  # 无盈亏数据的排在最后

        etf_positions.sort(key=get_pnl, reverse=True)
        stock_positions.sort(key=get_pnl, reverse=True)

        return {
            'etf_analysis': {
                'positions': etf_positions,
                'total_cost': etf_total_cost,
                'total_value': etf_total_value,
                'count': len(etf_positions),
                'pnl': etf_total_value - etf_total_cost if etf_total_value else 0
            },
            'stock_analysis': {
                'positions': stock_positions,
                'total_cost': stock_total_cost,
                'total_value': stock_total_value,
                'count': len(stock_positions),
                'pnl': stock_total_value - stock_total_cost if stock_total_value else 0
            }
        }

    def _normalize_platform_name(self, platform_id: str) -> str:
        """将平台ID转换为友好的平台名称"""
        if not platform_id or platform_id == '未知平台':
            return '未知平台'

        # 检查是否包含ML或Merrill相关标识
        if platform_id.upper().startswith('ML_') or 'merrill' in platform_id.lower():
            return 'Merrill Edge'

        # 检查是否包含Schwab相关标识
        if platform_id.upper().startswith('SCHWAB_') or 'schwab' in platform_id.lower():
            return 'Schwab'

        # 检查notes字段是否包含平台信息
        if 'Merrill Edge' in platform_id:
            return 'Merrill Edge'
        elif 'Schwab' in platform_id:
            return 'Schwab'

        # 默认返回原始名称
        return platform_id

    def _analyze_by_platforms(self, positions: List[Dict], transactions: List[Dict]) -> Dict[str, Any]:
        """按平台分析持仓 - 基于实际交易数据动态分配"""
        # 从数据库获取每个position_lot的平台信息
        platform_allocation = self._get_platform_allocation_from_lots()

        # 初始化平台汇总
        platform_summary = {}

        # 分配持仓到各平台
        for pos in positions:
            symbol = pos['symbol']
            symbol_allocations = platform_allocation.get(symbol, [])

            for allocation in symbol_allocations:
                platform = allocation['platform']
                if platform not in platform_summary:
                    platform_summary[platform] = {
                        'symbols': set(),
                        'total_investment': 0.0,
                        'current_value': 0.0
                    }

                # 按实际份额分配投资成本和市值
                # 使用股数比例而非成本比例来确保与原有逻辑一致
                total_shares_for_symbol = sum(alloc['quantity'] for alloc in symbol_allocations)
                share_ratio = allocation['quantity'] / total_shares_for_symbol if total_shares_for_symbol > 0 else 0

                platform_summary[platform]['symbols'].add(symbol)
                platform_summary[platform]['total_investment'] += allocation['cost']
                # Only add to current_value if market_value is not None
                if pos['market_value'] is not None:
                    platform_summary[platform]['current_value'] += pos['market_value'] * share_ratio

        # 转换symbols为列表并计算汇总数据
        for platform, data in platform_summary.items():
            data['symbols'] = list(data['symbols'])
            data['pnl'] = data['current_value'] - data['total_investment']
            data['return_pct'] = (data['pnl'] / data['total_investment'] * 100) if data['total_investment'] > 0 else 0

        return platform_summary

    def _get_platform_allocation_from_lots(self) -> Dict[str, List[Dict]]:
        """从position_lots表获取每个股票在各平台的实际分配"""
        try:
            # 查询position_lots和transactions关联获取平台信息
            query = """
            SELECT
                pl.symbol,
                pl.original_quantity,
                pl.cost_basis,
                CASE
                    -- 排除DRIP批次的成本
                    WHEN t.notes LIKE '%Dividend Reinvestment%' THEN 0
                    ELSE pl.original_quantity * pl.cost_basis
                END as cost,
                CASE
                    WHEN pl.portfolio_id = 1 THEN 'Merrill Edge'
                    WHEN pl.portfolio_id = 2 THEN 'Schwab'
                    ELSE COALESCE(
                        (SELECT CASE
                            WHEN t.platform LIKE '%ml%' OR t.platform = 'ml' THEN 'Merrill Edge'
                            WHEN t.platform LIKE '%schwab%' OR t.platform = 'schwab' THEN 'Schwab'
                            ELSE COALESCE(t.platform, 'Unknown')
                        END
                        FROM transactions t2
                        WHERE t2.id = pl.transaction_id
                        LIMIT 1),
                        'Unknown'
                    )
                END as platform
            FROM position_lots pl
            LEFT JOIN transactions t ON pl.transaction_id = t.id
            WHERE pl.is_closed = 0
            ORDER BY pl.symbol, platform
            """

            rows = self.storage.cursor.execute(query).fetchall()

            allocation = {}
            for row in rows:
                symbol = row[0]
                if symbol not in allocation:
                    allocation[symbol] = []

                allocation[symbol].append({
                    'quantity': row[1],
                    'cost_basis': row[2],
                    'cost': row[3],
                    'platform': row[4]
                })

            return allocation

        except Exception as e:
            # 如果查询失败，返回空字典
            print(f"Error getting platform allocation: {e}")
            return {}

    def _calculate_risk_metrics(self, positions: List[Dict], total_cost: float) -> Dict[str, Any]:
        """计算风险指标"""
        if not positions or total_cost <= 0:
            return {'message': '无法计算风险指标'}

        # 计算集中度风险（确保类型一致）
        max_position_cost = float(max(pos['total_cost'] for pos in positions))
        concentration_risk = max_position_cost / float(total_cost)
        
        # 获取最大持仓
        max_position = max(positions, key=lambda x: float(x['total_cost']))

        # 计算前三大持仓比例
        sorted_positions = sorted(positions, key=lambda x: float(x['total_cost']), reverse=True)
        top3_cost = sum(float(pos['total_cost']) for pos in sorted_positions[:3])
        top3_concentration = top3_cost / float(total_cost)
        
        # 风险等级评估
        risk_level = '低'
        if concentration_risk > 0.4:
            risk_level = '高'
        elif concentration_risk > 0.25:
            risk_level = '中'
        
        return {
            'position_count': len(positions),
            'max_position': {
                'symbol': max_position['symbol'],
                'concentration': concentration_risk,
                'amount': float(max_position['total_cost'])
            },
            'top3_concentration': top3_concentration,
            'risk_level': risk_level,
            'diversification_score': '高' if len(positions) >= 8 else '中' if len(positions) >= 5 else '低'
        }

    def _analyze_performance(self, positions: List[Dict]) -> Dict[str, Any]:
        """分析投资表现"""
        if not positions:
            return {'message': '无表现数据'}
        
        # 分类表现 - filter out positions with None values
        winners = [pos for pos in positions if pos.get('unrealized_pnl') is not None and pos.get('unrealized_pnl', 0) > 0]
        losers = [pos for pos in positions if pos.get('unrealized_pnl') is not None and pos.get('unrealized_pnl', 0) < 0]

        # 最佳和最差表现 - only consider positions with valid P&L data
        positions_with_pnl = [pos for pos in positions if pos.get('unrealized_pnl_pct') is not None]
        if not positions_with_pnl:
            # No positions have P&L data yet
            return {
                'winners': 0,
                'losers': 0,
                'neutral': len(positions),
                'best_performer': None,
                'worst_performer': None,
                'winner_ratio': 0,
                'message': '等待价格数据更新'
            }

        best_performer = max(positions_with_pnl, key=lambda x: x.get('unrealized_pnl_pct', 0))
        worst_performer = min(positions_with_pnl, key=lambda x: x.get('unrealized_pnl_pct', 0))
        
        return {
            'winners': len(winners),
            'losers': len(losers),
            'neutral': len(positions) - len(winners) - len(losers),
            'best_performer': {
                'symbol': best_performer['symbol'],
                'return_pct': best_performer.get('unrealized_pnl_pct', 0),
                'pnl': best_performer.get('unrealized_pnl', 0)
            },
            'worst_performer': {
                'symbol': worst_performer['symbol'],
                'return_pct': worst_performer.get('unrealized_pnl_pct', 0),
                'pnl': worst_performer.get('unrealized_pnl', 0)
            },
            'winner_ratio': len(winners) / len(positions) if positions else 0
        }

    def _generate_recommendations(self, positions: List[Dict], total_cost: float) -> List[str]:
        """生成投资建议"""
        recommendations = []
        
        if not positions:
            recommendations.append("建立初始投资组合，建议从大盘ETF开始")
            return recommendations
        
        # 集中度风险检查
        max_position = max(positions, key=lambda x: x['total_cost'])
        concentration = max_position['total_cost'] / total_cost if total_cost > 0 else 0
        
        if concentration > 0.3:
            recommendations.append(f"降低{max_position['symbol']}的持仓比例，当前占比{concentration:.1%}过高")
        
        # 多样化建议
        if len(positions) < 5:
            recommendations.append("增加持仓品种数量以提高分散化程度")
        
        # 表现分析
        losers = [pos for pos in positions if pos.get('unrealized_pnl_pct') is not None and pos.get('unrealized_pnl_pct', 0) < -5]
        if losers:
            worst = min(losers, key=lambda x: x.get('unrealized_pnl_pct', 0))
            recommendations.append(f"关注{worst['symbol']}的下跌，当前跌幅{worst.get('unrealized_pnl_pct', 0):.1f}%")
        
        # ETF vs 个股比例
        etf_count = sum(1 for pos in positions if pos['symbol'] in ['SPY', 'URTH', 'VGT'])
        if etf_count / len(positions) < 0.3:
            recommendations.append("考虑增加ETF配置以降低个股风险")
        
        return recommendations

    def _get_historical_performance(self, positions: List[Dict]) -> Dict[str, Any]:
        """获取历史表现分析"""
        try:
            # 获取价格变化数据 - 使用与Holdings相同的股票代码格式（不带.US后缀）
            price_changes = {}
            for pos in positions:
                symbol = pos['symbol']  # 直接使用原始symbol，不添加.US后缀
                
                # 获取加权平均成本作为入场价格 - 排除DRIP交易
                actual_entry_price_query = """
                SELECT SUM(pl.cost_basis * pl.original_quantity)/SUM(pl.original_quantity) as avg_price
                FROM position_lots pl
                LEFT JOIN transactions t ON pl.transaction_id = t.id
                WHERE pl.symbol = ? AND pl.remaining_quantity > 0
                AND (t.notes IS NULL OR t.notes NOT LIKE '%Dividend Reinvestment%')
                """
                entry_result = self.storage.cursor.execute(actual_entry_price_query, (symbol,)).fetchone()
                actual_entry_price = float(entry_result[0]) if entry_result else None
                
                # 查询当前价格
                current_price_query = """
                SELECT adj_close FROM stock_prices 
                WHERE symbol = ? ORDER BY date DESC LIMIT 1
                """
                
                try:
                    current_result = self.storage.cursor.execute(current_price_query, (symbol,)).fetchone()
                    if actual_entry_price and current_result and current_result[0]:
                        current_price = float(current_result[0])
                        price_change_pct = ((current_price - actual_entry_price) / actual_entry_price) * 100
                        
                        price_changes[pos['symbol']] = {
                            'first_price': actual_entry_price,
                            'current_price': current_price,
                            'price_change_pct': price_change_pct,
                            'entry_date': self._get_first_purchase_date(pos['symbol'])
                        }
                except Exception as e:
                    self.logger.warning(f"获取{pos['symbol']}价格变化失败: {e}")
            
            return price_changes
            
        except Exception as e:
            self.logger.warning(f"获取历史表现失败: {e}")
            return {}

    def _get_first_purchase_date(self, symbol: str) -> str:
        """获取首次购买日期"""
        try:
            query = """
            SELECT MIN(purchase_date)
            FROM position_lots
            WHERE symbol = ?
            """
            result = self.storage.cursor.execute(query, (symbol,)).fetchone()
            return result[0] if result and result[0] else '未知'
        except:
            return '未知'

    def _get_detailed_risk_assessment(self, positions: List[Dict], total_cost: float) -> Dict[str, Any]:
        """详细风险评估"""
        if not positions or total_cost <= 0:
            return {'message': '无法计算风险指标'}
        
        # 基础风险指标
        basic_risk = self._calculate_risk_metrics(positions, total_cost)
        
        # 额外的风险分析
        sectors = {}
        for pos in positions:
            sector = self._get_sector_for_symbol(pos['symbol'])
            if sector not in sectors:
                sectors[sector] = {'count': 0, 'value': 0}
            sectors[sector]['count'] += 1
            sectors[sector]['value'] += float(pos['total_cost'])

        # 行业集中度
        sector_concentrations = {
            sector: float(data['value']) / float(total_cost)
            for sector, data in sectors.items()
        }

        max_sector = max(sector_concentrations.items(), key=lambda x: x[1])

        # 计算组合贝塔（简化版）
        volatility_scores = {
            'LULU': 1.3,  # 高波动性个股
            'MRK': 0.8,   # 低波动性医药股
            'PPC': 1.1,   # 中等波动性
            'ALSN': 1.2,  # 工业股波动性
            'SPY': 1.0,   # 市场基准
            'URTH': 0.9   # 全球分散化
        }

        weighted_volatility = sum(
            volatility_scores.get(pos['symbol'], 1.0) * (float(pos['total_cost']) / float(total_cost))
            for pos in positions
        )
        
        basic_risk.update({
            'sector_analysis': {
                'max_sector': max_sector[0],
                'max_sector_concentration': max_sector[1],
                'sector_count': len(sectors),
                'sector_distribution': sector_concentrations
            },
            'volatility_analysis': {
                'portfolio_volatility_score': weighted_volatility,
                'volatility_level': '高' if weighted_volatility > 1.2 else '中' if weighted_volatility > 0.9 else '低'
            }
        })
        
        return basic_risk

    def _get_sector_for_symbol(self, symbol: str) -> str:
        """获取股票所属行业"""
        try:
            # 从数据库读取真实的行业信息
            query = "SELECT sector FROM stocks WHERE symbol = ?"
            result = self.storage.cursor.execute(query, (symbol,)).fetchone()
            if result and result[0]:
                return result[0]
        except Exception as e:
            self.logger.warning(f"无法从数据库获取{symbol}的行业信息: {e}")

        # 回退到硬编码映射（保持向后兼容）
        sector_map = {
            'SPY': '大盘指数', 'URTH': '全球指数', 'VGT': '科技ETF', 'LULU': '非必需消费品',
            'MRK': '医疗保健', 'PPC': '必需消费品', 'ALSN': '工业',
            'ANF': '非必需消费品', 'MATX': '工业', 'OGN': '医疗保健',
            'OMC': '传播服务'
        }
        return sector_map.get(symbol, '其他')

    def _generate_strategy_insights(self, positions: List[Dict], total_cost: float,
                                  historical_performance: Dict, risk_assessment: Dict) -> Dict[str, Any]:
        """生成投资策略洞察"""
        
        strengths = []
        improvements = []
        recommendations = []
        
        # 分析优势
        etf_count = sum(1 for pos in positions if pos['symbol'] in ['SPY', 'URTH', 'VGT'])
        if etf_count >= 2:
            strengths.append("多元化基础：ETF基金提供了良好的市场暴露")
        
        platform_diversity = len(self._get_transaction_details())
        if platform_diversity > 0:
            strengths.append("平台分散：资产分布在多个交易平台，降低平台风险")
        
        recent_activity = all(
            pos.get('last_transaction_date', '') >= '2025-09-01' 
            for pos in positions
        )
        if recent_activity:
            strengths.append("投资活跃：所有持仓都是近期建立，反映积极的投资态度")
        
        # 分析改进领域
        max_position = max(positions, key=lambda x: x['total_cost'])
        concentration = max_position['total_cost'] / total_cost
        if concentration > 0.25:
            improvements.append(f"集中度风险：{max_position['symbol']}占比{concentration:.1%}过高")
        
        if risk_assessment.get('sector_analysis', {}).get('max_sector_concentration', 0) > 0.4:
            max_sector = risk_assessment['sector_analysis']['max_sector']
            improvements.append(f"行业集中：{max_sector}板块配置过重")
        
        # 防御性持仓检查
        defensive_sectors = ['医疗保健', '必需消费品']
        defensive_ratio = sum(
            pos['total_cost'] for pos in positions 
            if self._get_sector_for_symbol(pos['symbol']) in defensive_sectors
        ) / total_cost
        
        if defensive_ratio < 0.2:
            improvements.append("防御性配置不足：缺乏防御性行业暴露")
        
        # 生成建议
        if concentration > 0.2:
            recommendations.append(f"重新平衡：考虑将{max_position['symbol']}持仓降至20%以下")
        
        tech_exposure = sum(
            pos['total_cost'] for pos in positions 
            if self._get_sector_for_symbol(pos['symbol']) in ['科技', '信息技术']
        ) / total_cost
        
        if tech_exposure < 0.15:
            recommendations.append("增加科技股：考虑加入科技、公用事业或房地产板块")
        
        # 表现不佳股票监控
        poor_performers = [
            pos for pos in positions
            if pos.get('unrealized_pnl_pct') is not None and pos.get('unrealized_pnl_pct', 0) < -5
        ]
        
        if poor_performers:
            worst = min(poor_performers, key=lambda x: x.get('unrealized_pnl_pct', 0))
            recommendations.append(f"监控{worst['symbol']}：该股票跌幅{worst.get('unrealized_pnl_pct', 0):.1f}%，需要关注")
        
        recommendations.append("继续ETF策略：SPY和URTH提供良好的市场基础配置")
        
        # 计算总体评级
        score = 75  # 基础分
        score += len(strengths) * 5
        score -= len(improvements) * 8
        score = max(60, min(100, score))
        
        grade = 'A' if score >= 90 else 'A-' if score >= 85 else 'B+' if score >= 80 else 'B' if score >= 75 else 'B-' if score >= 70 else 'C+'
        
        return {
            'strengths': strengths,
            'improvements': improvements,
            'recommendations': recommendations,
            'overall_score': score,
            'grade': grade,
            'summary': f"投资组合基础良好，但需关注集中度风险"
        }
    
    def get_position_history(self, symbol: str, 
                           start_date: str = None, end_date: str = None) -> List[DailyPnL]:
        """
        获取特定股票的持仓历史
        
        Args:
            symbol: 股票代码
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
            
        Returns:
            List[DailyPnL]: 每日盈亏记录列表
        """
        pnl_data = self.storage.get_daily_pnl(
            symbol, start_date=start_date, end_date=end_date
        )

        return [DailyPnL.from_dict(data) for data in pnl_data]

    def get_realized_gains(self) -> Dict[str, Any]:
        """
        获取已实现盈亏汇总

        Returns:
            Dict: 包含已卖出股票的盈亏信息
        """
        query = """
            SELECT
                t.symbol,
                s.company_name,
                st.sector,
                st.industry,
                t.transaction_date as sale_date,
                SUM(sa.quantity_sold) as total_quantity_sold,
                SUM(sa.cost_basis) as total_cost_basis,
                SUM(sa.quantity_sold * sa.sale_price) as total_sale_proceeds,
                SUM(sa.realized_pnl) as total_realized_pnl,
                (SUM(sa.realized_pnl) / SUM(sa.cost_basis) * 100) as realized_pnl_pct
            FROM sale_allocations sa
            JOIN transactions t ON sa.sale_transaction_id = t.id
            LEFT JOIN stocks s ON t.symbol = s.symbol
            LEFT JOIN stocks st ON t.symbol = st.symbol
            WHERE t.transaction_type = 'SELL'
            GROUP BY t.symbol, t.transaction_date, s.company_name, st.sector, st.industry
            ORDER BY t.transaction_date DESC
        """

        result = self.storage.connection.execute(query).fetchall()

        realized_sales = []
        total_realized_pnl = 0.0
        total_cost_basis = 0.0
        total_proceeds = 0.0

        for row in result:
            sale_info = {
                'symbol': row[0],
                'company_name': row[1] or row[0],
                'sector': row[2] or '未知',
                'industry': row[3] or '未知',
                'sale_date': row[4],
                'quantity_sold': row[5],
                'cost_basis': row[6],
                'sale_proceeds': row[7],
                'realized_pnl': row[8],
                'realized_pnl_pct': row[9] if row[9] else 0.0
            }
            realized_sales.append(sale_info)
            total_realized_pnl += row[8] or 0.0
            total_cost_basis += row[6] or 0.0
            total_proceeds += row[7] or 0.0

        return {
            'sales': realized_sales,
            'summary': {
                'total_sales': len(realized_sales),
                'total_cost_basis': total_cost_basis,
                'total_proceeds': total_proceeds,
                'total_realized_pnl': total_realized_pnl,
                'average_return_pct': (total_realized_pnl / total_cost_basis * 100) if total_cost_basis > 0 else 0.0
            }
        }

    def _get_total_cash_dividends(self) -> float:
        """获取现金分红总额"""
        try:
            query = """
                SELECT SUM(total_cash_received) as total_cash
                FROM dividends
                WHERE dividend_type = 'CASH'
            """
            result = self.storage.connection.execute(query).fetchone()
            return float(result[0]) if result and result[0] else 0.0
        except Exception as e:
            self.logger.warning(f"获取现金分红总额失败: {e}")
            return 0.0

    def _calculate_overall_performance(self, basic_summary: Dict[str, Any], realized_gains: Dict[str, Any]) -> Dict[str, Any]:
        """
        计算总体投资表现（包含当前持仓和已卖出股票）

        Args:
            basic_summary: 当前持仓摘要
            realized_gains: 已实现盈亏数据

        Returns:
            Dict: 总体投资表现数据
        """
        # 当前持仓数据
        current_cost = basic_summary.get('total_cost', 0.0)
        current_market_value = basic_summary.get('total_market_value', 0.0)
        current_unrealized_pnl = basic_summary.get('total_unrealized_pnl', 0.0)

        # 已实现数据（卖出股票）
        realized_summary = realized_gains.get('summary', {})
        realized_cost = realized_summary.get('total_cost_basis', 0.0)
        realized_proceeds = realized_summary.get('total_proceeds', 0.0)
        realized_pnl = realized_summary.get('total_realized_pnl', 0.0)

        # 现金分红（纯盈利，不涉及成本）
        cash_dividends = self._get_total_cash_dividends()

        # 总体数据（关注当前持仓状态）
        total_invested = current_cost  # 累计投入 = 当前持仓成本（不含已卖出股票）
        total_current_value = current_market_value  # 当前总价值 = 当前持仓市值（不含卖出收入）
        total_pnl = current_unrealized_pnl + realized_pnl + cash_dividends  # 总盈亏 = 未实现 + 已实现 + 现金分红
        total_return_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0.0

        return {
            'total_invested': total_invested,  # 累计投入
            'total_current_value': total_current_value,  # 当前总价值
            'total_pnl': total_pnl,  # 总盈亏
            'total_return_pct': total_return_pct,  # 总收益率
            'cash_dividends': cash_dividends,  # 现金分红总额
            'breakdown': {
                'current_holdings': {
                    'cost': current_cost,
                    'market_value': current_market_value,
                    'unrealized_pnl': current_unrealized_pnl,
                    'unrealized_pnl_pct': basic_summary.get('total_unrealized_pnl_pct', 0.0)
                },
                'realized_sales': {
                    'cost': realized_cost,
                    'proceeds': realized_proceeds,
                    'realized_pnl': realized_pnl,
                    'realized_pnl_pct': realized_summary.get('average_return_pct', 0.0)
                },
                'cash_dividends': {
                    'total_cash': cash_dividends
                }
            }
        }