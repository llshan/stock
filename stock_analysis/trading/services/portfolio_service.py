#!/usr/bin/env python3
"""
投资组合服务
提供投资组合管理和分析功能
"""

import os
import json
import logging
from datetime import datetime, date
from typing import List, Optional, Dict, Any

import openai

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
        
        # 初始化OpenAI客户端
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key:
            self.openai_client = openai.OpenAI(api_key=api_key)
        else:
            self.openai_client = None
            self.logger.warning("未设置OPENAI_API_KEY环境变量，将使用默认策略洞察")
    
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
        
        # 获取当前持仓
        positions = self.transaction_service.get_current_positions()
        
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
            'recommendations': self._generate_recommendations(basic_summary['positions'], basic_summary['total_cost'])
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

    def _analyze_by_sectors(self, positions: List[Dict]) -> Dict[str, Any]:
        """按行业分析持仓"""
        # 股票类型分类（这里使用简单的分类，实际应该从数据库获取）
        stock_categories = {
            'SPY': {
                'type': 'ETF', 
                'category': 'SPDR S&P 500 ETF', 
                'sector': '大盘指数',
                'company_name': 'SPDR S&P 500 ETF Trust',
                'description': '跟踪标普500指数的ETF基金'
            },
            'URTH': {
                'type': 'ETF', 
                'category': 'iShares Core MSCI全球市场ETF', 
                'sector': '全球指数',
                'company_name': 'iShares Core MSCI Total International Stock ETF',
                'description': '跟踪全球市场的ETF基金'
            },
            'LULU': {
                'type': '个股', 
                'category': 'Lululemon Athletica', 
                'sector': '非必需消费品',
                'company_name': 'Lululemon Athletica Inc.',
                'description': '高端运动服装和瑜伽用品零售商'
            },
            'MRK': {
                'type': '个股', 
                'category': 'Merck & Co', 
                'sector': '医疗保健',
                'company_name': 'Merck & Co., Inc.',
                'description': '全球领先的制药和生物技术公司'
            },
            'PPC': {
                'type': '个股', 
                'category': "Pilgrim's Pride Corp", 
                'sector': '必需消费品',
                'company_name': "Pilgrim's Pride Corporation",
                'description': '北美领先的家禽生产和加工公司'
            },
            'ALSN': {
                'type': '个股', 
                'category': 'Allison Transmission', 
                'sector': '工业',
                'company_name': 'Allison Transmission Holdings, Inc.',
                'description': '商用车自动变速箱制造商'
            }
        }
        
        etf_positions = []
        stock_positions = []
        etf_total_cost = 0.0
        etf_total_value = 0.0
        stock_total_cost = 0.0
        stock_total_value = 0.0
        
        for pos in positions:
            symbol = pos['symbol']
            category_info = stock_categories.get(symbol, {'type': '未知', 'category': '其他', 'sector': '其他'})
            
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

    def _analyze_by_platforms(self, positions: List[Dict], transactions: List[Dict]) -> Dict[str, Any]:
        """按平台分析持仓"""
        platform_summary = {}
        
        # 按平台分组交易
        for transaction in transactions:
            platform = transaction.get('platform', '未知平台')
            symbol = transaction['symbol']
            
            if platform not in platform_summary:
                platform_summary[platform] = {
                    'symbols': set(),
                    'total_investment': 0.0,
                    'transactions': []
                }
            
            platform_summary[platform]['symbols'].add(symbol)
            platform_summary[platform]['total_investment'] += transaction['quantity'] * transaction['price']
            platform_summary[platform]['transactions'].append(transaction)
        
        # 计算每个平台的当前价值
        for platform, data in platform_summary.items():
            data['symbols'] = list(data['symbols'])
            data['symbol_count'] = len(data['symbols'])
            
            # 计算当前市值（需要根据持仓分配）
            current_value = 0.0
            for pos in positions:
                if pos['symbol'] in data['symbols'] and pos['market_value']:
                    # 简化处理：按投资金额比例分配
                    symbol_investment = sum(t['quantity'] * t['price'] for t in data['transactions'] 
                                          if t['symbol'] == pos['symbol'])
                    total_symbol_investment = sum(t['quantity'] * t['price'] for t in transactions 
                                                if t['symbol'] == pos['symbol'])
                    if total_symbol_investment > 0:
                        allocation_ratio = symbol_investment / total_symbol_investment
                        current_value += pos['market_value'] * allocation_ratio
            
            data['current_value'] = current_value
            data['pnl'] = current_value - data['total_investment']
            data['return_pct'] = (data['pnl'] / data['total_investment'] * 100) if data['total_investment'] > 0 else 0
        
        return platform_summary

    def _calculate_risk_metrics(self, positions: List[Dict], total_cost: float) -> Dict[str, Any]:
        """计算风险指标"""
        if not positions or total_cost <= 0:
            return {'message': '无法计算风险指标'}
        
        # 计算集中度风险
        max_position_cost = max(pos['total_cost'] for pos in positions)
        concentration_risk = max_position_cost / total_cost
        
        # 获取最大持仓
        max_position = max(positions, key=lambda x: x['total_cost'])
        
        # 计算前三大持仓比例
        sorted_positions = sorted(positions, key=lambda x: x['total_cost'], reverse=True)
        top3_cost = sum(pos['total_cost'] for pos in sorted_positions[:3])
        top3_concentration = top3_cost / total_cost
        
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
                'amount': max_position['total_cost']
            },
            'top3_concentration': top3_concentration,
            'risk_level': risk_level,
            'diversification_score': '高' if len(positions) >= 8 else '中' if len(positions) >= 5 else '低'
        }

    def _analyze_performance(self, positions: List[Dict]) -> Dict[str, Any]:
        """分析投资表现"""
        if not positions:
            return {'message': '无表现数据'}
        
        # 分类表现
        winners = [pos for pos in positions if pos.get('unrealized_pnl', 0) > 0]
        losers = [pos for pos in positions if pos.get('unrealized_pnl', 0) < 0]
        
        # 最佳和最差表现
        best_performer = max(positions, key=lambda x: x.get('unrealized_pnl_pct', 0))
        worst_performer = min(positions, key=lambda x: x.get('unrealized_pnl_pct', 0))
        
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
        losers = [pos for pos in positions if pos.get('unrealized_pnl_pct', 0) < -5]
        if losers:
            worst = min(losers, key=lambda x: x.get('unrealized_pnl_pct', 0))
            recommendations.append(f"关注{worst['symbol']}的下跌，当前跌幅{worst.get('unrealized_pnl_pct', 0):.1f}%")
        
        # ETF vs 个股比例
        etf_count = sum(1 for pos in positions if pos['symbol'] in ['SPY', 'URTH'])
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
                
                # 获取实际交易价格作为入场价格
                actual_entry_price_query = """
                SELECT price FROM transactions 
                WHERE symbol = ? AND transaction_type = 'BUY' 
                ORDER BY transaction_date ASC LIMIT 1
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
            SELECT MIN(transaction_date) 
            FROM transactions 
            WHERE symbol = ? AND transaction_type = 'BUY'
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
            sectors[sector]['value'] += pos['total_cost']
        
        # 行业集中度
        sector_concentrations = {
            sector: data['value'] / total_cost 
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
            volatility_scores.get(pos['symbol'], 1.0) * (pos['total_cost'] / total_cost)
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
        sector_map = {
            'SPY': '大盘指数', 'URTH': '全球指数', 'LULU': '非必需消费品',
            'MRK': '医疗保健', 'PPC': '必需消费品', 'ALSN': '工业'
        }
        return sector_map.get(symbol, '其他')

    def _generate_strategy_insights(self, positions: List[Dict], total_cost: float, 
                                  historical_performance: Dict, risk_assessment: Dict) -> Dict[str, Any]:
        """生成投资策略洞察"""
        
        if self.openai_client:
            return self._generate_ai_strategy_insights(positions, total_cost, historical_performance, risk_assessment)
        else:
            return self._generate_default_strategy_insights(positions, total_cost, historical_performance, risk_assessment)

    def _generate_ai_strategy_insights(self, positions: List[Dict], total_cost: float, 
                                     historical_performance: Dict, risk_assessment: Dict) -> Dict[str, Any]:
        """使用OpenAI API生成投资策略洞察"""
        try:
            # 构建投资组合数据摘要
            portfolio_data = {
                "total_portfolio_value": total_cost,
                "positions": [
                    {
                        "symbol": pos['symbol'],
                        "shares": pos.get('shares', pos.get('quantity', 0)),
                        "cost_basis": pos['avg_cost'],
                        "current_value": pos['total_cost'],
                        "weight": pos['total_cost'] / total_cost,
                        "unrealized_pnl_pct": pos.get('unrealized_pnl_pct', 0),
                        "sector": self._get_sector_for_symbol(pos['symbol'])
                    }
                    for pos in positions
                ],
                "risk_metrics": {
                    "sector_concentration": risk_assessment.get('sector_analysis', {}),
                    "volatility_score": risk_assessment.get('volatility_analysis', {}).get('portfolio_volatility_score', 1.0)
                },
                "performance": historical_performance
            }
            
            prompt = f"""
作为专业的投资顾问，请分析以下投资组合数据并提供策略洞察。

投资组合数据：
{json.dumps(portfolio_data, ensure_ascii=False, indent=2)}

请以JSON格式返回分析结果，包含以下字段：
- strengths: 投资组合优势列表（3-5个要点）
- improvements: 需要改进的领域列表（2-4个要点）
- recommendations: 具体投资建议列表（3-5个建议）
- overall_score: 总体评分（60-100分）
- grade: 等级评定（A, A-, B+, B, B-, C+）
- summary: 一句话总结

注意：
1. 分析要基于实际数据，不要编造信息
2. 建议要具体且可操作
3. 考虑风险分散、行业配置、投资表现等因素
4. 使用中文回复
"""

            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "你是一位专业的投资顾问，擅长投资组合分析和风险管理。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            ai_response = response.choices[0].message.content
            
            # 尝试解析JSON响应
            try:
                # 提取JSON部分
                start_idx = ai_response.find('{')
                end_idx = ai_response.rfind('}') + 1
                if start_idx != -1 and end_idx != 0:
                    json_str = ai_response[start_idx:end_idx]
                    insights = json.loads(json_str)
                    return insights
                else:
                    raise ValueError("无法找到有效的JSON响应")
            except (json.JSONDecodeError, ValueError) as e:
                self.logger.warning(f"AI响应JSON解析失败: {e}, 使用默认策略")
                return self._generate_default_strategy_insights(positions, total_cost, historical_performance, risk_assessment)
                
        except Exception as e:
            self.logger.error(f"OpenAI API调用失败: {e}")
            return self._generate_default_strategy_insights(positions, total_cost, historical_performance, risk_assessment)

    def _generate_default_strategy_insights(self, positions: List[Dict], total_cost: float, 
                                          historical_performance: Dict, risk_assessment: Dict) -> Dict[str, Any]:
        """默认的策略洞察生成逻辑（作为AI调用失败时的备选方案）"""
        
        strengths = []
        improvements = []
        recommendations = []
        
        # 分析优势
        etf_count = sum(1 for pos in positions if pos['symbol'] in ['SPY', 'URTH'])
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
            if pos.get('unrealized_pnl_pct', 0) < -5
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