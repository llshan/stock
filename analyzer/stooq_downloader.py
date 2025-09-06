#!/usr/bin/env python3
"""
Stooq股票数据下载器
使用pandas_datareader从Stooq获取历史股票数据
"""

import pandas as pd
import pandas_datareader as pdr
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time
import logging
import requests

class StooqDataDownloader:
    def __init__(self, max_retries: int = 3, base_delay: int = 5):
        """
        初始化Stooq数据下载器
        
        Args:
            max_retries: 最大重试次数
            base_delay: 基础延迟时间（秒）
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.logger = logging.getLogger(__name__)
        
        # Stooq数据源配置
        self.data_source = 'stooq'
        
    def _retry_with_backoff(self, func, symbol: str):
        """带退避策略的重试机制"""
        for attempt in range(self.max_retries):
            try:
                return func()
            except Exception as e:
                error_msg = str(e)
                is_retryable = any(pattern in error_msg.lower() for pattern in [
                    'timeout', 'connection', 'network', 'temporary', 'unavailable'
                ])
                
                if is_retryable and attempt < self.max_retries - 1:
                    delay = self.base_delay * (2 ** attempt)
                    self.logger.warning(f"⏰ {symbol} Stooq请求失败，等待 {delay} 秒后重试 (尝试 {attempt + 1}/{self.max_retries})")
                    time.sleep(delay)
                    continue
                else:
                    raise e
        
        raise Exception(f"{symbol} 重试 {self.max_retries} 次后仍然失败")
    
    def download_stock_data(self, symbol: str, start_date: str = "2000-01-01", end_date: str = None) -> Dict:
        """
        从Stooq下载股票历史数据
        
        Args:
            symbol: 股票代码（如AAPL.US）
            start_date: 开始日期
            end_date: 结束日期（默认今天）
            
        Returns:
            包含价格数据的字典
        """
        def _download():
            return self._download_stooq_data(symbol, start_date, end_date)
        
        return self._retry_with_backoff(_download, symbol)
    
    def _download_stooq_data(self, symbol: str, start_date: str, end_date: str = None) -> Dict:
        """内部Stooq数据下载实现"""
        try:
            if end_date is None:
                end_date = datetime.now().strftime('%Y-%m-%d')
            
            # 确保symbol格式正确（Stooq需要.US后缀）
            if not symbol.endswith('.US'):
                stooq_symbol = f"{symbol}.US"
            else:
                stooq_symbol = symbol
                symbol = symbol.replace('.US', '')  # 去掉后缀用于返回数据
            
            self.logger.info(f"📈 从Stooq下载 {symbol} 数据 ({start_date} 到 {end_date})")
            
            # 从Stooq获取数据
            data = pdr.DataReader(stooq_symbol, self.data_source, start_date, end_date)
            
            if data.empty:
                return {'error': f'从Stooq无法获取 {symbol} 的历史数据'}
            
            # 转换为与yfinance兼容的格式
            stock_data = {
                'symbol': symbol,
                'start_date': start_date,
                'end_date': end_date,
                'data_points': len(data),
                'price_data': {
                    'dates': [d.strftime('%Y-%m-%d') for d in data.index],
                    'open': data['Open'].tolist(),
                    'high': data['High'].tolist(),
                    'low': data['Low'].tolist(),
                    'close': data['Close'].tolist(),
                    'volume': data['Volume'].tolist(),
                    'adj_close': data['Close'].tolist()  # Stooq数据通常已调整
                },
                'summary_stats': {
                    'min_price': float(data['Close'].min()),
                    'max_price': float(data['Close'].max()),
                    'avg_price': float(data['Close'].mean()),
                    'total_volume': int(data['Volume'].sum()),
                    'avg_volume': int(data['Volume'].mean())
                },
                'downloaded_at': datetime.now().isoformat(),
                'data_source': 'Stooq',
                'incremental_update': False
            }
            
            self.logger.info(f"✅ {symbol} Stooq数据下载完成: {len(data)} 个数据点")
            return stock_data
            
        except Exception as e:
            error_msg = f"从Stooq下载 {symbol} 数据失败: {str(e)}"
            self.logger.error(error_msg)
            return {'error': error_msg}
    
    def test_connection(self) -> bool:
        """测试Stooq连接"""
        try:
            self.logger.info("🔍 测试Stooq连接...")
            
            # 尝试获取AAPL的最近一天数据
            end_date = datetime.now()
            start_date = end_date - timedelta(days=5)  # 多取几天确保有数据
            
            data = pdr.DataReader('AAPL.US', 'stooq', start_date, end_date)
            
            if not data.empty:
                self.logger.info(f"✅ Stooq连接正常，获取到 {len(data)} 条AAPL数据")
                return True
            else:
                self.logger.warning("⚠️ Stooq连接正常但无数据")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Stooq连接失败: {str(e)}")
            return False
    
    def get_available_symbols(self) -> List[str]:
        """获取可用的股票代码列表"""
        # Stooq支持的主要美股代码
        us_stocks = [
            'AAPL', 'GOOGL', 'MSFT', 'AMZN', 'META', 'TSLA', 'NVDA',
            'NFLX', 'UBER', 'ZOOM', 'JPM', 'JNJ', 'PG', 'KO', 'WMT',
            'DIS', 'V', 'MA', 'BABA', 'JD', 'BIDU', 'CRM', 'ORCL',
            'IBM', 'INTC', 'AMD', 'QCOM', 'ADBE', 'PYPL', 'SHOP',
            'SQ', 'TWTR', 'SNAP', 'PINS', 'ROKU', 'ZM', 'DOCU',
            'PTON', 'ABNB', 'COIN', 'HOOD', 'RBLX', 'U', 'PLTR'
        ]
        return us_stocks
    
    def batch_download(self, symbols: List[str], start_date: str = "2000-01-01", end_date: str = None) -> Dict[str, Dict]:
        """
        批量下载股票数据
        
        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            所有股票数据的字典
        """
        results = {}
        total = len(symbols)
        
        self.logger.info(f"🎯 开始从Stooq批量下载 {total} 个股票的数据")
        
        for i, symbol in enumerate(symbols):
            self.logger.info(f"进度: [{i+1}/{total}] 处理 {symbol}")
            
            try:
                results[symbol] = self.download_stock_data(symbol, start_date, end_date)
                
                # 添加延迟避免请求过快
                if i < total - 1:
                    time.sleep(1)  # Stooq通常比Yahoo Finance更宽松
                    
            except Exception as e:
                self.logger.error(f"下载 {symbol} 时出错: {str(e)}")
                results[symbol] = {'error': str(e)}
        
        successful = len([r for r in results.values() if 'error' not in r])
        self.logger.info(f"✅ Stooq批量下载完成，成功: {successful}/{total}")
        return results
    
    def compare_with_yfinance_format(self, stooq_data: Dict) -> Dict:
        """
        确保Stooq数据格式与yfinance兼容
        
        Args:
            stooq_data: Stooq下载的数据
            
        Returns:
            格式化后的数据
        """
        if 'error' in stooq_data:
            return stooq_data
        
        # 已经在_download_stooq_data中处理了格式兼容性
        stooq_data['data_source'] = 'Stooq (compatible with yfinance format)'
        return stooq_data

if __name__ == "__main__":
    # 测试Stooq下载器
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    print("🌐 Stooq股票数据下载器测试")
    print("=" * 50)
    
    downloader = StooqDataDownloader()
    
    # 测试连接
    if downloader.test_connection():
        print("\n✅ Stooq连接测试成功")
        
        # 测试单个股票下载
        print(f"\n📈 测试下载AAPL数据...")
        result = downloader.download_stock_data('AAPL', start_date='2000-01-01')
        
        if 'error' not in result:
            print(f"✅ AAPL数据下载成功:")
            print(f"   数据点数: {result['data_points']}")
            print(f"   时间范围: {result['start_date']} 到 {result['end_date']}")
            print(f"   最新价格: ${result['price_data']['close'][-1]:.2f}")
        else:
            print(f"❌ AAPL数据下载失败: {result['error']}")
        
        # 测试批量下载
        print(f"\n📊 测试批量下载...")
        symbols = ['AAPL', 'GOOGL', 'MSFT']
        batch_results = downloader.batch_download(symbols, start_date='2000-01-01')
        
        for symbol, data in batch_results.items():
            if 'error' not in data:
                print(f"✅ {symbol}: {data['data_points']} 个数据点")
            else:
                print(f"❌ {symbol}: {data['error']}")
    
    else:
        print("\n❌ Stooq连接测试失败，请检查网络连接")