#!/usr/bin/env python3
"""
股票数据下载器
下载从2020年开始的股票价格数据和财务报表
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import time
import logging
import json

class StockDataDownloader:
    def __init__(self, database=None, max_retries=3, base_delay=30):
        """初始化股票数据下载器"""
        self.start_date = "2020-01-01"
        self.logger = logging.getLogger(__name__)
        self.database = database  # 可选的数据库实例，用于增量更新
        self.max_retries = max_retries  # 最大重试次数
        self.base_delay = base_delay  # 基础延迟时间（秒）
    
    def _retry_with_backoff(self, func, symbol: str):
        """带退避策略的重试机制"""
        for attempt in range(self.max_retries):
            try:
                return func()
            except Exception as e:
                error_msg = str(e)
                is_rate_limit = ("429" in error_msg or 
                               "Too Many Requests" in error_msg or 
                               "rate limit" in error_msg.lower())
                
                if is_rate_limit and attempt < self.max_retries - 1:
                    delay = self.base_delay * (2 ** attempt)  # 指数退避
                    self.logger.warning(f"⏰ {symbol} API限制，等待 {delay} 秒后重试 (尝试 {attempt + 1}/{self.max_retries})")
                    time.sleep(delay)
                    continue
                else:
                    # 非限制类错误或已达最大重试次数
                    raise e
        
        raise Exception(f"{symbol} 重试 {self.max_retries} 次后仍然失败")
    
    def _is_api_error_retryable(self, error: Exception) -> bool:
        """判断错误是否可重试"""
        error_msg = str(error)
        retryable_patterns = [
            "429",
            "Too Many Requests", 
            "timeout",
            "connection",
            "network",
            "temporary"
        ]
        return any(pattern in error_msg.lower() for pattern in retryable_patterns)
        
    def get_last_update_date(self, symbol: str) -> Optional[str]:
        """获取股票的最后更新日期"""
        if not self.database:
            return None
        
        try:
            # 查询数据库中该股票的最新日期
            query = "SELECT MAX(date) FROM stock_prices WHERE symbol = ?"
            result = self.database.cursor.execute(query, (symbol,)).fetchone()
            
            if result and result[0]:
                last_date = datetime.strptime(result[0], '%Y-%m-%d')
                # 从最后一天的下一天开始下载，避免重复
                next_date = last_date + timedelta(days=1)
                return next_date.strftime('%Y-%m-%d')
            
            return None
        except Exception as e:
            self.logger.warning(f"获取 {symbol} 最后更新日期失败: {str(e)}")
            return None

    def download_stock_data(self, symbol: str, start_date: str = None, incremental: bool = True, use_retry: bool = True) -> Dict:
        """
        下载股票的历史价格数据
        
        Args:
            symbol: 股票代码
            start_date: 开始日期，默认2020-01-01
            incremental: 是否进行增量下载
            use_retry: 是否使用重试机制
            
        Returns:
            包含价格数据的字典
        """
        def _download_data():
            return self._download_stock_data_internal(symbol, start_date, incremental)
        
        if use_retry:
            return self._retry_with_backoff(_download_data, symbol)
        else:
            return _download_data()
    
    def _download_stock_data_internal(self, symbol: str, start_date: str = None, incremental: bool = True) -> Dict:
        """内部股票数据下载实现"""
        try:
            # 如果启用增量下载且有数据库，尝试从最后更新日期开始
            if incremental and self.database:
                last_update = self.get_last_update_date(symbol)
                if last_update:
                    start_date = last_update
                    self.logger.info(f"🔄 {symbol} 启用增量下载，从 {start_date} 开始")
                elif start_date is None:
                    start_date = self.start_date
            elif start_date is None:
                start_date = self.start_date
                
            self.logger.info(f"📈 下载 {symbol} 股票数据 (从 {start_date})")
            
            # 检查日期范围是否有效
            today = datetime.now().strftime('%Y-%m-%d')
            if start_date >= today:
                self.logger.info(f"📊 {symbol} 数据已是最新，无需更新")
                return {
                    'symbol': symbol,
                    'start_date': start_date,
                    'end_date': today,
                    'data_points': 0,
                    'price_data': {
                        'dates': [], 'open': [], 'high': [], 'low': [], 
                        'close': [], 'volume': [], 'adj_close': []
                    },
                    'summary_stats': {},
                    'downloaded_at': datetime.now().isoformat(),
                    'incremental_update': True,
                    'no_new_data': True
                }
            
            # 下载股票数据
            ticker = yf.Ticker(symbol)
            hist_data = ticker.history(start=start_date, end=today)
            
            if hist_data.empty:
                return {'error': f'无法获取 {symbol} 的历史数据（时间范围: {start_date} 到 {today}）'}
            
            # 转换为字典格式
            stock_data = {
                'symbol': symbol,
                'start_date': start_date,
                'end_date': today,
                'data_points': len(hist_data),
                'price_data': {
                    'dates': [d.strftime('%Y-%m-%d') for d in hist_data.index],
                    'open': hist_data['Open'].tolist(),
                    'high': hist_data['High'].tolist(),
                    'low': hist_data['Low'].tolist(),
                    'close': hist_data['Close'].tolist(),
                    'volume': hist_data['Volume'].tolist(),
                    'adj_close': hist_data['Adj Close'].tolist()
                },
                'summary_stats': {
                    'min_price': float(hist_data['Close'].min()),
                    'max_price': float(hist_data['Close'].max()),
                    'avg_price': float(hist_data['Close'].mean()),
                    'total_volume': int(hist_data['Volume'].sum()),
                    'avg_volume': int(hist_data['Volume'].mean())
                },
                'downloaded_at': datetime.now().isoformat(),
                'incremental_update': incremental and self.database is not None
            }
            
            self.logger.info(f"✅ {symbol} 数据下载完成: {len(hist_data)} 个数据点")
            return stock_data
            
        except Exception as e:
            error_msg = f"下载 {symbol} 股票数据失败: {str(e)}"
            self.logger.error(error_msg)
            return {'error': error_msg}
    
    def download_financial_data(self, symbol: str, use_retry: bool = True) -> Dict:
        """
        下载股票的财务报表数据
        
        Args:
            symbol: 股票代码
            use_retry: 是否使用重试机制
            
        Returns:
            包含财务数据的字典
        """
        def _download_data():
            return self._download_financial_data_internal(symbol)
        
        if use_retry:
            return self._retry_with_backoff(_download_data, symbol)
        else:
            return _download_data()
    
    def _download_financial_data_internal(self, symbol: str) -> Dict:
        """内部财务数据下载实现"""
        try:
            self.logger.info(f"💼 下载 {symbol} 财务报表数据")
            
            ticker = yf.Ticker(symbol)
            
            # 获取财务报表
            financials = ticker.financials
            balance_sheet = ticker.balance_sheet
            cash_flow = ticker.cashflow
            
            # 获取基本信息
            info = ticker.info
            
            financial_data = {
                'symbol': symbol,
                'basic_info': {
                    'company_name': info.get('longName', ''),
                    'sector': info.get('sector', ''),
                    'industry': info.get('industry', ''),
                    'market_cap': info.get('marketCap', 0),
                    'employees': info.get('fullTimeEmployees', 0),
                    'description': info.get('longBusinessSummary', '')
                },
                'financial_statements': {},
                'downloaded_at': datetime.now().isoformat()
            }
            
            # 处理损益表
            if not financials.empty:
                financial_data['financial_statements']['income_statement'] = self._process_financial_statement(
                    financials, '损益表'
                )
            
            # 处理资产负债表
            if not balance_sheet.empty:
                financial_data['financial_statements']['balance_sheet'] = self._process_financial_statement(
                    balance_sheet, '资产负债表'
                )
            
            # 处理现金流量表
            if not cash_flow.empty:
                financial_data['financial_statements']['cash_flow'] = self._process_financial_statement(
                    cash_flow, '现金流量表'
                )
            
            self.logger.info(f"✅ {symbol} 财务数据下载完成")
            return financial_data
            
        except Exception as e:
            error_msg = f"下载 {symbol} 财务数据失败: {str(e)}"
            self.logger.error(error_msg)
            return {'error': error_msg}
    
    def _process_financial_statement(self, df: pd.DataFrame, statement_type: str) -> Dict:
        """处理财务报表数据"""
        try:
            # 获取最近4年的数据
            processed_data = {
                'statement_type': statement_type,
                'periods': [col.strftime('%Y-%m-%d') for col in df.columns],
                'items': {}
            }
            
            for index in df.index:
                # 清理指标名称
                item_name = str(index).strip()
                if item_name and item_name != 'nan':
                    values = []
                    for col in df.columns:
                        value = df.loc[index, col]
                        if pd.isna(value):
                            values.append(None)
                        else:
                            values.append(float(value))
                    processed_data['items'][item_name] = values
            
            return processed_data
            
        except Exception as e:
            self.logger.warning(f"处理财务报表 {statement_type} 时出错: {str(e)}")
            return {'error': f'处理 {statement_type} 失败: {str(e)}'}
    
    def download_comprehensive_data(self, symbol: str, start_date: str = None, incremental: bool = True, use_retry: bool = True) -> Dict:
        """
        下载股票的综合数据（价格+财务）
        
        Args:
            symbol: 股票代码
            start_date: 开始日期
            incremental: 是否进行增量下载
            use_retry: 是否使用重试机制
            
        Returns:
            综合数据字典
        """
        retry_text = "（启用重试）" if use_retry else ""
        self.logger.info(f"🚀 开始下载 {symbol} 的综合数据{'（增量模式）' if incremental else '（全量模式）'}{retry_text}")
        
        # 下载股票价格数据
        stock_data = self.download_stock_data(symbol, start_date, incremental, use_retry)
        
        # 添加延迟避免API限制
        time.sleep(1)
        
        # 下载财务数据
        financial_data = self.download_financial_data(symbol, use_retry)
        
        # 合并数据
        comprehensive_data = {
            'symbol': symbol,
            'download_timestamp': datetime.now().isoformat(),
            'stock_data': stock_data,
            'financial_data': financial_data,
            'data_quality': self._assess_data_quality(stock_data, financial_data)
        }
        
        return comprehensive_data
    
    def batch_download(self, symbols: List[str], start_date: str = None, incremental: bool = True, use_retry: bool = True) -> Dict[str, Dict]:
        """
        批量下载多个股票的数据
        
        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            incremental: 是否进行增量下载
            use_retry: 是否使用重试机制
            
        Returns:
            所有股票数据的字典
        """
        results = {}
        total = len(symbols)
        
        mode_text = "增量下载" if incremental else "全量下载"
        retry_text = "（启用重试）" if use_retry else ""
        self.logger.info(f"🎯 开始批量{mode_text} {total} 个股票的数据{retry_text}")
        
        for i, symbol in enumerate(symbols):
            self.logger.info(f"进度: [{i+1}/{total}] 处理 {symbol}")
            
            try:
                results[symbol] = self.download_comprehensive_data(symbol, start_date, incremental, use_retry)
                
                # 添加延迟避免API限制
                if i < total - 1:  # 最后一个不需要延迟
                    time.sleep(2)
                    
            except Exception as e:
                self.logger.error(f"下载 {symbol} 时出错: {str(e)}")
                results[symbol] = {'error': str(e)}
        
        self.logger.info(f"✅ 批量下载完成，成功: {len([r for r in results.values() if 'error' not in r])}/{total}")
        return results
    
    def _assess_data_quality(self, stock_data: Dict, financial_data: Dict) -> Dict:
        """评估数据质量"""
        quality = {
            'stock_data_available': 'error' not in stock_data,
            'financial_data_available': 'error' not in financial_data,
            'data_completeness': 0.0,
            'issues': []
        }
        
        # 评估股票数据质量
        if quality['stock_data_available']:
            data_points = stock_data.get('data_points', 0)
            expected_points = (datetime.now() - datetime.strptime(self.start_date, '%Y-%m-%d')).days
            quality['stock_data_completeness'] = min(1.0, data_points / (expected_points * 0.7))  # 考虑周末
        else:
            quality['issues'].append('股票价格数据不可用')
        
        # 评估财务数据质量
        if quality['financial_data_available']:
            statements = financial_data.get('financial_statements', {})
            quality['financial_statements_count'] = len(statements)
            if len(statements) < 3:
                quality['issues'].append('财务报表数据不完整')
        else:
            quality['issues'].append('财务数据不可用')
        
        # 总体完整性评分
        completeness_score = 0
        if quality['stock_data_available']:
            completeness_score += 0.6
        if quality['financial_data_available']:
            completeness_score += 0.4
        
        quality['data_completeness'] = completeness_score
        quality['quality_grade'] = self._get_quality_grade(completeness_score)
        
        return quality
    
    def _get_quality_grade(self, score: float) -> str:
        """根据完整性评分获取质量等级"""
        if score >= 0.9:
            return 'A - 优秀'
        elif score >= 0.7:
            return 'B - 良好'
        elif score >= 0.5:
            return 'C - 一般'
        elif score >= 0.3:
            return 'D - 较差'
        else:
            return 'F - 很差'

def create_watchlist() -> List[str]:
    """创建需要关注的股票清单"""
    return [
        # 大型科技股
        "AAPL",   # 苹果
        "GOOGL",  # 谷歌
        "MSFT",   # 微软
        "AMZN",   # 亚马逊
        "META",   # Meta
        "TSLA",   # 特斯拉
        "NVDA",   # 英伟达
        
        # 热门成长股
        "NFLX",   # Netflix
        "UBER",   # Uber
        "ZOOM",   # Zoom
        
        # 中概股
        "BABA",   # 阿里巴巴
        "JD",     # 京东
        "BIDU",   # 百度
        
        # 传统蓝筹股
        "JPM",    # 摩根大通
        "JNJ",    # 强生
        "PG",     # 宝洁
        "KO",     # 可口可乐
        "WMT",    # 沃尔玛
        
        # 其他重要股票
        "DIS",    # 迪士尼
        "V",      # Visa
        "MA"      # Mastercard
    ]

if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    print("🚀 股票数据下载器")
    print("=" * 50)
    
    # 创建下载器
    downloader = StockDataDownloader()
    
    # 获取关注股票列表
    watchlist = create_watchlist()
    
    print(f"📊 将下载 {len(watchlist)} 个股票的数据:")
    for i, symbol in enumerate(watchlist, 1):
        print(f"  {i:2d}. {symbol}")
    
    print(f"\n⏰ 数据时间范围: {downloader.start_date} 至今")
    print("📈 包含: 股票价格数据 + 财务报表数据")
    
    # 执行批量下载
    results = downloader.batch_download(watchlist)
    
    # 显示下载结果摘要
    successful = len([r for r in results.values() if 'error' not in r])
    failed = len(results) - successful
    
    print("\n" + "=" * 50)
    print("📊 下载结果摘要:")
    print(f"✅ 成功: {successful} 个股票")
    print(f"❌ 失败: {failed} 个股票")
    
    if failed > 0:
        print("\n❌ 失败的股票:")
        for symbol, data in results.items():
            if 'error' in data:
                print(f"   • {symbol}: {data['error']}")
    
    # 数据质量报告
    print("\n📈 数据质量报告:")
    for symbol, data in results.items():
        if 'error' not in data:
            quality = data.get('data_quality', {})
            print(f"   {symbol}: {quality.get('quality_grade', 'Unknown')}")
    
    print(f"\n💾 可以将结果保存到数据库或文件中...")