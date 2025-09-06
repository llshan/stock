#!/usr/bin/env python3
"""
混合股票数据下载器
结合Stooq（批量历史数据）和yfinance（增量更新）的优势
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analyzer.stooq_downloader import StooqDataDownloader
from analyzer.data_downloader import StockDataDownloader
from analyzer.database import StockDatabase

class HybridStockDownloader:
    def __init__(self, database: StockDatabase, max_retries: int = 3, base_delay: int = 30):
        """
        初始化混合股票下载器
        
        Args:
            database: 数据库实例
            max_retries: 最大重试次数
            base_delay: 基础延迟时间（秒）
        """
        self.database = database
        self.stooq_downloader = StooqDataDownloader(max_retries=max_retries)
        self.yfinance_downloader = StockDataDownloader(
            database=database, 
            max_retries=max_retries, 
            base_delay=base_delay
        )
        self.logger = logging.getLogger(__name__)
        
    def download_stock_data(self, symbol: str, start_date: str = "2000-01-01") -> Dict:
        """
        智能股票数据下载：新股票用Stooq批量下载，已有股票用yfinance增量更新
        
        Args:
            symbol: 股票代码
            start_date: 开始日期（仅用于新股票）
            
        Returns:
            下载结果字典
        """
        try:
            # 检查股票是否已存在于数据库
            existing_symbols = self.database.get_existing_symbols()
            is_new_stock = symbol not in existing_symbols
            
            if is_new_stock:
                self.logger.info(f"🆕 {symbol} 是新股票，使用Stooq进行批量历史数据下载")
                return self._download_with_stooq(symbol, start_date)
            else:
                self.logger.info(f"🔄 {symbol} 已存在，使用yfinance进行增量更新")
                return self._download_with_yfinance(symbol)
                
        except Exception as e:
            self.logger.error(f"混合下载 {symbol} 失败: {str(e)}")
            return {'error': f'混合下载失败: {str(e)}'}
    
    def _download_with_stooq(self, symbol: str, start_date: str) -> Dict:
        """使用Stooq下载历史数据"""
        try:
            # 使用Stooq下载完整历史数据
            stooq_data = self.stooq_downloader.download_stock_data(symbol, start_date)
            
            if 'error' in stooq_data:
                self.logger.warning(f"⚠️ {symbol} Stooq下载失败，尝试yfinance全量下载")
                # 如果Stooq失败，fallback到yfinance全量下载
                return self.yfinance_downloader.download_comprehensive_data(
                    symbol, start_date, incremental=False, use_retry=True
                )
            
            # 转换为comprehensive格式并存储
            comprehensive_data = self._convert_stooq_to_comprehensive(stooq_data)
            self.database.store_comprehensive_data(symbol, comprehensive_data)
            
            self.logger.info(f"✅ {symbol} Stooq批量下载完成: {stooq_data['data_points']} 个数据点")
            
            # 然后尝试用yfinance更新到最新
            self._update_with_yfinance(symbol)
            
            return comprehensive_data
            
        except Exception as e:
            self.logger.error(f"Stooq下载 {symbol} 失败: {str(e)}")
            return {'error': f'Stooq下载失败: {str(e)}'}
    
    def _download_with_yfinance(self, symbol: str) -> Dict:
        """使用yfinance进行增量更新"""
        try:
            # 使用yfinance进行增量下载
            result = self.yfinance_downloader.download_comprehensive_data(
                symbol, incremental=True, use_retry=True
            )
            
            if 'error' not in result:
                self.logger.info(f"✅ {symbol} yfinance增量更新完成")
            else:
                self.logger.warning(f"⚠️ {symbol} yfinance增量更新失败: {result.get('error', '未知错误')}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"yfinance增量更新 {symbol} 失败: {str(e)}")
            return {'error': f'yfinance增量更新失败: {str(e)}'}
    
    def _update_with_yfinance(self, symbol: str):
        """使用yfinance更新到最新数据（用于Stooq下载后的补充更新）"""
        try:
            # 获取最后更新日期
            last_date = self.database.get_last_update_date(symbol)
            if not last_date:
                self.logger.info(f"📊 {symbol} 无法获取最后更新日期，跳过yfinance补充更新")
                return
            
            # 检查是否需要更新
            last_datetime = datetime.strptime(last_date, '%Y-%m-%d')
            today = datetime.now()
            days_diff = (today - last_datetime).days
            
            if days_diff <= 1:
                self.logger.info(f"📊 {symbol} 数据已是最新，无需补充更新")
                return
            
            self.logger.info(f"🔄 {symbol} 使用yfinance补充更新最近 {days_diff} 天的数据")
            
            # 使用yfinance进行增量更新
            next_date = (last_datetime + timedelta(days=1)).strftime('%Y-%m-%d')
            yf_result = self.yfinance_downloader.download_stock_data(
                symbol, start_date=next_date, incremental=True, use_retry=True
            )
            
            if 'error' not in yf_result and yf_result.get('data_points', 0) > 0:
                # 存储yfinance增量数据
                self.database.store_stock_prices(symbol, yf_result['price_data'], incremental=True)
                self.logger.info(f"✅ {symbol} yfinance补充更新完成: {yf_result['data_points']} 个新数据点")
            elif yf_result.get('no_new_data'):
                self.logger.info(f"📊 {symbol} yfinance确认无新数据需要更新")
            else:
                self.logger.warning(f"⚠️ {symbol} yfinance补充更新失败")
                
        except Exception as e:
            self.logger.warning(f"yfinance补充更新 {symbol} 时出错: {str(e)}")
    
    def _convert_stooq_to_comprehensive(self, stooq_data: Dict) -> Dict:
        """将Stooq数据转换为comprehensive格式"""
        symbol = stooq_data['symbol']
        
        # 创建基本信息
        basic_info = {
            'company_name': f'{symbol} Inc.',
            'sector': 'Unknown',
            'industry': 'Unknown',
            'market_cap': 0,
            'employees': 0,
            'description': f'{symbol} stock data from Stooq via hybrid downloader'
        }
        
        # 评估数据质量
        data_quality = {
            'stock_data_available': True,
            'financial_data_available': False,
            'data_completeness': 0.6,
            'quality_grade': 'B - 良好（Stooq批量下载）',
            'issues': ['仅提供价格数据，无财务报表', '来自Stooq数据源']
        }
        
        # 构造comprehensive格式
        comprehensive_data = {
            'symbol': symbol,
            'download_timestamp': datetime.now().isoformat(),
            'stock_data': stooq_data,
            'financial_data': {
                'error': 'Stooq不提供财务数据',
                'basic_info': basic_info
            },
            'data_quality': data_quality,
            'download_strategy': 'hybrid_stooq_bulk'
        }
        
        return comprehensive_data
    
    def batch_download(self, symbols: List[str], start_date: str = "2000-01-01") -> Dict[str, Dict]:
        """
        批量混合下载
        
        Args:
            symbols: 股票代码列表
            start_date: 新股票的开始日期
            
        Returns:
            批量下载结果
        """
        results = {}
        total = len(symbols)
        
        self.logger.info(f"🎯 开始混合批量下载 {total} 个股票（Stooq批量 + yfinance增量）")
        
        # 分类股票：新股票和已有股票
        existing_symbols = self.database.get_existing_symbols()
        new_stocks = [s for s in symbols if s not in existing_symbols]
        existing_stocks = [s for s in symbols if s in existing_symbols]
        
        print(f"📊 股票分类:")
        print(f"   🆕 新股票: {len(new_stocks)} 个 - 将使用Stooq批量下载")
        print(f"   🔄 已有股票: {len(existing_stocks)} 个 - 将使用yfinance增量更新")
        print("=" * 60)
        
        # 处理所有股票
        for i, symbol in enumerate(symbols):
            print(f"\n[{i+1}/{total}] 处理 {symbol}...")
            
            try:
                results[symbol] = self.download_stock_data(symbol, start_date)
                
                if 'error' not in results[symbol]:
                    data_points = results[symbol].get('stock_data', {}).get('data_points', 0)
                    strategy = "Stooq批量" if symbol in new_stocks else "yfinance增量"
                    print(f"✅ {symbol} 完成 ({strategy}): {data_points} 个数据点")
                else:
                    print(f"❌ {symbol} 失败: {results[symbol]['error']}")
                
                # 添加延迟避免API限制
                if i < total - 1:
                    import time
                    time.sleep(1)
                    
            except Exception as e:
                self.logger.error(f"处理 {symbol} 时出错: {str(e)}")
                results[symbol] = {'error': str(e)}
                print(f"❌ {symbol} 处理失败: {str(e)}")
        
        # 统计结果
        successful = len([r for r in results.values() if 'error' not in r])
        failed = len(results) - successful
        
        print(f"\n" + "=" * 60)
        print(f"📊 混合批量下载结果:")
        print(f"✅ 成功: {successful}/{total}")
        print(f"❌ 失败: {failed}/{total}")
        print(f"📊 成功率: {successful/total*100:.1f}%")
        
        return results
    
    def get_download_strategy_info(self, symbols: List[str]) -> Dict:
        """获取下载策略信息"""
        existing_symbols = self.database.get_existing_symbols()
        
        strategy_info = {
            'new_stocks': [s for s in symbols if s not in existing_symbols],
            'existing_stocks': [s for s in symbols if s in existing_symbols],
            'strategies': {}
        }
        
        for symbol in symbols:
            if symbol in existing_symbols:
                last_update = self.database.get_last_update_date(symbol)
                strategy_info['strategies'][symbol] = {
                    'method': 'yfinance_incremental',
                    'reason': '股票已存在，进行增量更新',
                    'last_update': last_update
                }
            else:
                strategy_info['strategies'][symbol] = {
                    'method': 'stooq_bulk_then_yfinance',
                    'reason': '新股票，先Stooq批量下载历史数据，再yfinance补充最新',
                    'last_update': None
                }
        
        return strategy_info

if __name__ == "__main__":
    # 测试混合下载器
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    print("🔄 混合股票数据下载器测试")
    print("=" * 50)
    
    # 创建数据库和下载器
    database = StockDatabase("database/hybrid_test.db")
    downloader = HybridStockDownloader(database)
    
    try:
        # 测试单个股票下载
        print("\n📈 测试单个股票下载...")
        result = downloader.download_stock_data('NVDA')
        
        if 'error' not in result:
            data_points = result.get('stock_data', {}).get('data_points', 0)
            print(f"✅ NVDA下载成功: {data_points} 个数据点")
        else:
            print(f"❌ NVDA下载失败: {result['error']}")
        
        # 测试批量下载
        print(f"\n📊 测试批量下载...")
        symbols = ['AAPL', 'NVDA', 'AMD']  # 混合新旧股票
        batch_results = downloader.batch_download(symbols)
        
        print(f"\n🔍 下载策略分析:")
        strategy_info = downloader.get_download_strategy_info(symbols)
        for symbol, info in strategy_info['strategies'].items():
            print(f"   {symbol}: {info['method']} - {info['reason']}")
        
    finally:
        database.close()