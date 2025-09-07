#!/usr/bin/env python3
"""
数据管理器（简化）
按是否为新股选择数据源并直接写库
"""

import logging
import warnings
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union

from .stooq import StooqDataDownloader
from .yfinance import YFinanceDataDownloader
from ..database import StockDatabase


class DataManager:
    """数据管理器（推荐使用）"""
    
    def __init__(self, database: StockDatabase, max_retries: int = 3, base_delay: int = 30):
        """
        初始化混合股票下载器
        
        Args:
            database: 数据库实例
            max_retries: 最大重试次数
            base_delay: 基础延迟时间（秒）
        """
        self.database = database
        self.logger = logging.getLogger(__name__)
        
        # 创建下载器实例
        self.yfinance_downloader = YFinanceDataDownloader(
            max_retries=max_retries, 
            base_delay=base_delay
        )
        self.stooq_downloader = StooqDataDownloader(max_retries=max_retries)
        
        self.logger.info(f"🚀 数据管理器初始化完成")
    
    def _is_new_stock(self, symbol: str) -> bool:
        """检查是否为新股票"""
        existing_symbols = self.database.get_existing_symbols()
        return symbol not in existing_symbols
    
    def _get_last_update_date(self, symbol: str) -> Optional[str]:
        """获取股票的最后更新日期"""
        try:
            query = "SELECT MAX(date) FROM stock_prices WHERE symbol = ?"
            result = self.database.cursor.execute(query, (symbol,)).fetchone()
            
            if result and result[0]:
                last_date = datetime.strptime(result[0], '%Y-%m-%d')
                next_date = last_date + timedelta(days=1)
                return next_date.strftime('%Y-%m-%d')
            
            return None
        except Exception as e:
            self.logger.warning(f"获取 {symbol} 最后更新日期失败: {str(e)}")
            return None
    
    def download_stock_data(self, symbol: str, start_date: str = "2000-01-01", **kwargs) -> Dict:
        """
        智能股票数据下载
        
        Args:
            symbol: 股票代码
            start_date: 开始日期
            **kwargs: 额外参数
            
        Returns:
            下载结果字典
        """
        try:
            is_new = self._is_new_stock(symbol)
            
            if is_new:
                # 新股票使用Stooq进行批量历史数据下载
                self.logger.info(f"🆕 {symbol} 是新股票，使用Stooq进行批量下载")
                strategy = "Stooq批量历史数据"
                
                stock_data = self.stooq_downloader.download_stock_data(symbol, start_date)
                if hasattr(stock_data, 'symbol') and stock_data.data_points > 0:
                    self.database.store_stock_prices(symbol, stock_data.price_data, incremental=False)
                    self.database.store_download_log(symbol, 'stock_prices', 'success', stock_data.data_points)
                    
                    result = {
                        'success': True,
                        'symbol': symbol,
                        'data_points': stock_data.data_points,
                        'used_strategy': strategy,
                        'incremental': False
                    }
                else:
                    result = {'success': False, 'error': 'Stooq下载失败', 'symbol': symbol}
                    
            else:
                # 已有股票使用yfinance进行增量更新
                self.logger.info(f"🔄 {symbol} 已存在，使用yfinance进行增量更新")
                strategy = "yfinance增量更新"
                
                actual_start_date = self._get_last_update_date(symbol) or start_date
                
                stock_data = self.yfinance_downloader.download_stock_data(
                    symbol, actual_start_date, incremental=True
                )
                
                if hasattr(stock_data, 'symbol'):
                    if stock_data.data_points > 0:
                        self.database.store_stock_prices(symbol, stock_data.price_data, incremental=True)
                        self.database.store_download_log(symbol, 'stock_prices', 'success', stock_data.data_points)
                        
                        result = {
                            'success': True,
                            'symbol': symbol,
                            'data_points': stock_data.data_points,
                            'used_strategy': strategy,
                            'incremental': True
                        }
                    else:
                        # 无新数据
                        result = {
                            'success': True,
                            'symbol': symbol,
                            'data_points': 0,
                            'no_new_data': True,
                            'used_strategy': strategy
                        }
                else:
                    result = {'success': False, 'error': 'yfinance下载失败', 'symbol': symbol}
            
            return result
            
        except Exception as e:
            error_msg = f"混合下载器执行失败: {str(e)}"
            self.logger.error(f"❌ {symbol} {error_msg}")
            
            # 记录失败日志
            self.database.store_download_log(symbol, 'stock_prices', 'failed', 0, error_msg)
            
            return {'success': False, 'error': error_msg, 'symbol': symbol}
    
    def batch_download(self, symbols: List[str], start_date: str = "2000-01-01", **kwargs) -> Dict[str, Dict]:
        """
        批量下载股票数据
        
        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            **kwargs: 额外参数
            
        Returns:
            批量下载结果
        """
        results = {}
        total = len(symbols)
        
        self.logger.info(f"🎯 开始混合策略批量下载 {total} 个股票")
        
        # 统计策略使用情况
        strategy_usage = {}
        
        for i, symbol in enumerate(symbols):
            self.logger.info(f"进度: [{i+1}/{total}] 处理 {symbol}")
            
            try:
                result = self.download_stock_data(symbol, start_date, **kwargs)
                
                # 统计策略使用
                used_strategy = result.get('used_strategy', 'Unknown')
                strategy_usage[used_strategy] = strategy_usage.get(used_strategy, 0) + 1
                
                results[symbol] = result
                
                # 添加延迟避免API限制
                if i < total - 1:
                    import time
                    time.sleep(2)
                    
            except Exception as e:
                self.logger.error(f"处理 {symbol} 时出错: {str(e)}")
                results[symbol] = {
                    'success': False,
                    'error': str(e),
                    'symbol': symbol
                }
        
        # 统计结果
        successful = len([r for r in results.values() if r.get('success', False)])
        failed = total - successful
        
        self.logger.info(f"✅ 混合策略批量下载完成，成功: {successful}/{total}")
        
        # 记录策略使用统计
        self.logger.info("📊 策略使用统计:")
        for strategy_name, count in strategy_usage.items():
            self.logger.info(f"   {strategy_name}: {count} 次")
        
        return {
            'total': total,
            'successful': successful,
            'failed': failed,
            'strategy_usage': strategy_usage,
            'results': results
        }
    
    def get_existing_symbols(self) -> List[str]:
        """获取数据库中已存在的股票代码列表"""
        return self.database.get_existing_symbols()
    
    def close(self):
        """关闭混合下载器"""
        if self.database:
            self.database.close()


def create_watchlist() -> List[str]:
    """创建需要关注的股票清单"""
    return [
        "AAPL",   # 苹果
        "GOOG",   # 谷歌
        "LULU"    # Lululemon
    ]


if __name__ == "__main__":
    # 配置日志
    from logging_utils import setup_logging
    setup_logging()
        logging.getLogger(__name__).info("🔄 数据管理器（简化）")
    logging.getLogger(__name__).info("=" * 60)
    logging.getLogger(__name__).info("💡 自动选择最佳下载策略，无需复杂配置")
    logging.getLogger(__name__).info("=" * 60)
    
    try:
        # 创建数据库和混合下载器
        database = StockDatabase("hybrid_stocks.db")
        manager = DataManager(database)
        
        # 获取关注股票列表
        watchlist = create_watchlist()
        
        logging.getLogger(__name__).info(f"📊 将下载 {len(watchlist)} 个股票的数据:")
        for i, symbol in enumerate(watchlist, 1):
            logging.getLogger(__name__).info(f"  {i:2d}. {symbol}")
        
        # 执行批量混合下载
        results = manager.batch_download(watchlist, start_date="2000-01-01")
        
        # 显示下载结果摘要
        logging.getLogger(__name__).info("=" * 60)
        logging.getLogger(__name__).info("📊 混合下载结果摘要:")
        logging.getLogger(__name__).info(f"   总计: {results['total']} 个股票")
        logging.getLogger(__name__).info(f"   成功: {results['successful']} 个")
        logging.getLogger(__name__).info(f"   失败: {results['failed']} 个")
        
        # 显示策略使用统计
        if results.get('strategy_usage'):
            logging.getLogger(__name__).info("📋 策略使用统计:")
            for strategy_name, count in results['strategy_usage'].items():
                logging.getLogger(__name__).info(f"   {strategy_name}: {count} 次")
        
        # 详细结果
        if results.get('results'):
            logging.getLogger(__name__).info("📋 详细结果:")
            for symbol, result in results['results'].items():
                if result.get('success'):
                    data_points = result.get('data_points', 0)
                    if result.get('no_new_data'):
                        logging.getLogger(__name__).info(f"   {symbol}: 数据已最新 ✅")
                    else:
                        logging.getLogger(__name__).info(f"   {symbol}: {data_points} 个数据点 ✅")
                else:
                    error = result.get('error', '未知错误')[:50]
                    logging.getLogger(__name__).error(f"   {symbol}: {error}... ❌")
        
        logging.getLogger(__name__).info("💾 数据已保存到 hybrid_stocks.db")
        logging.getLogger(__name__).info("📈 可以使用数据库工具查看完整的股票数据")
        
    except Exception as e:
        logging.getLogger(__name__).error(f"❌ 程序执行出错: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        # 清理资源
        if 'manager' in locals():
            manager.close()
            logging.getLogger(__name__).info("🔧 数据管理器已关闭")
