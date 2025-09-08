#!/usr/bin/env python3
"""
混合数据下载器（简化）
按策略选择 yfinance / Stooq，并直接写库
"""

import logging
import warnings
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union

from .stooq import StooqDataDownloader
from .yfinance import YFinanceDataDownloader
from ..storage import create_storage


class HybridDataDownloader:
    """混合数据下载器"""
    
    def __init__(self, storage=None, max_retries: int = 3, base_delay: int = 30):
        """
        初始化混合股票下载器
        
        Args:
            storage: 存储实例，默认使用SQLite
            max_retries: 最大重试次数
            base_delay: 基础延迟时间（秒）
        """
        self.storage = storage or create_storage('sqlite')
        self.logger = logging.getLogger(__name__)
        
        # 创建下载器实例
        self.yfinance_downloader = YFinanceDataDownloader(
            max_retries=max_retries, 
            base_delay=base_delay
        )
        self.stooq_downloader = StooqDataDownloader(max_retries=max_retries)
        
        self.logger.info(f"🚀 混合数据下载器初始化完成")
    
    def _is_new_stock(self, symbol: str) -> bool:
        """检查是否为新股票"""
        existing_symbols = self.storage.get_existing_symbols()
        return symbol not in existing_symbols
    
    def _get_last_update_date(self, symbol: str) -> Optional[str]:
        """获取股票的最后更新日期"""
        try:
            last_date = self.storage.get_last_update_date(symbol)
            if last_date:
                last_dt = datetime.strptime(last_date, '%Y-%m-%d')
                next_date = last_dt + timedelta(days=1)
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
                # 新股票使用Stooq进行历史全量数据下载
                self.logger.info(f"🆕 {symbol} 是新股票，使用Stooq进行历史全量下载")
                strategy = "Stooq历史全量"
                
                stock_data = self.stooq_downloader.download_stock_data(symbol, start_date)
                if hasattr(stock_data, 'symbol') and stock_data.data_points > 0:
                    self.storage.store_stock_data(symbol, stock_data)
                    # Download logging is now handled automatically
                    
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
                # 已有股票：按最后更新时间距今的天数选择策略
                raw_last = self.storage.get_last_update_date(symbol)
                actual_start_date = self._get_last_update_date(symbol) or start_date
                days_since = None
                try:
                    if raw_last:
                        days_since = (datetime.now() - datetime.strptime(raw_last, '%Y-%m-%d')).days
                except Exception:
                    days_since = None

                if days_since is not None and days_since > 100:
                    # 超过100天未更新：使用 Stooq 做长期补全（适合大跨度补齐）
                    self.logger.info(f"🔄 {symbol} 距上次更新 {days_since} 天，使用 Stooq 长期补全")
                    strategy = "Stooq长期补全(>100d)"
                    stock_data = self.stooq_downloader.download_stock_data(
                        symbol, actual_start_date
                    )
                else:
                    # 未超过100天：使用 yfinance 做增量更新（更灵活）
                    self.logger.info(f"🔄 {symbol} 距上次更新 {days_since if days_since is not None else '?'} 天，使用 yfinance 增量更新")
                    strategy = "yfinance增量更新(<=100d)"
                    stock_data = self.yfinance_downloader.download_stock_data(
                        symbol, actual_start_date, incremental=True
                    )

                if hasattr(stock_data, 'symbol'):
                    if stock_data.data_points > 0:
                        self.storage.store_stock_data(symbol, stock_data)
                        result = {
                            'success': True,
                            'symbol': symbol,
                            'data_points': stock_data.data_points,
                            'used_strategy': strategy,
                            'incremental': True
                        }
                    else:
                        result = {
                            'success': True,
                            'symbol': symbol,
                            'data_points': 0,
                            'no_new_data': True,
                            'used_strategy': strategy
                        }
                else:
                    err_src = 'yfinance' if 'yfinance' in strategy else 'stooq'
                    result = {'success': False, 'error': f'{err_src}下载失败', 'symbol': symbol}
            
            return result
            
        except Exception as e:
            error_msg = f"混合下载器执行失败: {str(e)}"
            self.logger.error(f"❌ {symbol} {error_msg}")
            
            # 记录失败日志
            # Error logging is now handled automatically by storage
            
            return {'success': False, 'error': error_msg, 'symbol': symbol}
    
    # 批量相关操作已移除：此下载器仅提供单只股票下载接口
    
    def get_existing_symbols(self) -> List[str]:
        """获取数据库中已存在的股票代码列表"""
        return self.storage.get_existing_symbols()
    
    def close(self):
        """关闭混合下载器"""
        if self.storage:
            self.storage.close()



if __name__ == "__main__":
    # 配置日志
    from utils.logging_utils import setup_logging
    from ..config import get_default_watchlist
    setup_logging()
    logging.getLogger(__name__).info("🔄 混合数据下载器（简化）")
    logging.getLogger(__name__).info("=" * 60)
    logging.getLogger(__name__).info("💡 自动选择最佳下载策略，无需复杂配置")
    logging.getLogger(__name__).info("=" * 60)
    
    try:
        # 创建混合下载器
        manager = HybridDataDownloader()  # 使用默认storage
        
        # 示例股票列表（演示用途，统一方法）
        watchlist = get_default_watchlist()
        
        logging.getLogger(__name__).info(f"📊 将下载 {len(watchlist)} 个股票的数据:")
        for i, symbol in enumerate(watchlist, 1):
            logging.getLogger(__name__).info(f"  {i:2d}. {symbol}")
        
        # 逐个下载（演示单股接口）
        total = len(watchlist)
        ok = 0
        for i, symbol in enumerate(watchlist, 1):
            logging.getLogger(__name__).info(f"📥 [{i}/{total}] 下载 {symbol} …")
            res = manager.download_stock_data(symbol, start_date="2000-01-01")
            if res.get('success'):
                ok += 1
                dp = res.get('data_points', 0)
                logging.getLogger(__name__).info(f"   {symbol}: {dp} 条（策略：{res.get('used_strategy','?')}）")
            else:
                logging.getLogger(__name__).error(f"   {symbol}: {res.get('error','未知错误')}")
            import time; time.sleep(2)

        # 摘要
        logging.getLogger(__name__).info("=" * 60)
        logging.getLogger(__name__).info("📊 混合下载结果摘要:")
        logging.getLogger(__name__).info(f"   总计: {total} 个股票")
        logging.getLogger(__name__).info(f"   成功: {ok} 个")
        logging.getLogger(__name__).info(f"   失败: {total-ok} 个")
        
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
            logging.getLogger(__name__).info("🔧 混合数据下载器已关闭")
