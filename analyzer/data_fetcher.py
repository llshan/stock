#!/usr/bin/env python3
"""
统一数据获取模块
消除重复的yfinance调用，提供统一的数据获取接口
"""

import yfinance as yf
import pandas as pd
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
from abc import ABC, abstractmethod
import logging


class DataFetcher(ABC):
    """数据获取抽象基类"""
    
    @abstractmethod
    def get_stock_data(self, symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
        """获取股票历史数据"""
        pass
    
    @abstractmethod
    def get_real_time_data(self, symbol: str) -> Dict:
        """获取实时数据"""
        pass
    
    @abstractmethod
    def get_company_info(self, symbol: str) -> Dict:
        """获取公司基本信息"""
        pass
    
    @abstractmethod
    def get_financial_data(self, symbol: str) -> Dict:
        """获取财务数据"""
        pass


class YFinanceDataFetcher(DataFetcher):
    """
    Yahoo Finance数据获取器
    统一所有yfinance相关的数据获取逻辑
    """
    
    def __init__(self, rate_limit_delay: float = 1.0, max_retries: int = 3):
        """
        初始化YFinance数据获取器
        
        Args:
            rate_limit_delay: API调用间隔时间（秒）
            max_retries: 最大重试次数
        """
        self.rate_limit_delay = rate_limit_delay
        self.max_retries = max_retries
        self.logger = logging.getLogger(__name__)
        self._ticker_cache = {}  # 缓存ticker对象
    
    def _get_ticker(self, symbol: str) -> yf.Ticker:
        """获取ticker对象，使用缓存避免重复创建"""
        if symbol not in self._ticker_cache:
            self._ticker_cache[symbol] = yf.Ticker(symbol)
        return self._ticker_cache[symbol]
    
    def _rate_limit(self):
        """API调用频率限制"""
        time.sleep(self.rate_limit_delay)
    
    def _retry_wrapper(self, func, *args, **kwargs):
        """重试机制包装器"""
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise e
                self.logger.warning(f"尝试 {attempt + 1} 失败: {str(e)}, 重试中...")
                time.sleep(2 ** attempt)  # 指数退避
    
    def get_stock_data(self, symbol: str, period: str = "1y", interval: str = "1d", 
                      start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        获取股票历史数据
        
        Args:
            symbol: 股票代码
            period: 时间周期 (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: 数据间隔 (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
        
        Returns:
            包含OHLCV数据的DataFrame
        """
        self._rate_limit()
        
        def _fetch():
            ticker = self._get_ticker(symbol)
            if start_date or end_date:
                return ticker.history(start=start_date, end=end_date, interval=interval)
            else:
                return ticker.history(period=period, interval=interval)
        
        try:
            data = self._retry_wrapper(_fetch)
            if data.empty:
                raise ValueError(f"无法获取 {symbol} 的历史数据")
            return data
        except Exception as e:
            self.logger.error(f"获取股票数据失败: {symbol}, 错误: {str(e)}")
            raise
    
    def get_real_time_data(self, symbol: str) -> Dict:
        """
        获取实时数据
        
        Args:
            symbol: 股票代码
            
        Returns:
            包含实时价格信息的字典
        """
        self._rate_limit()
        
        def _fetch():
            ticker = self._get_ticker(symbol)
            # 获取当日5分钟间隔数据作为实时数据
            history = ticker.history(period="1d", interval="5m")
            if history.empty:
                raise ValueError(f"无法获取 {symbol} 的实时数据")
            
            current_price = history['Close'].iloc[-1]
            prev_price = history['Close'].iloc[0] if len(history) > 1 else current_price
            change = current_price - prev_price
            change_percent = (change / prev_price) * 100 if prev_price != 0 else 0
            
            return {
                'symbol': symbol,
                'current_price': float(current_price),
                'change': float(change),
                'change_percent': float(change_percent),
                'volume': int(history['Volume'].iloc[-1]),
                'timestamp': history.index[-1].isoformat(),
                'high': float(history['High'].iloc[-1]),
                'low': float(history['Low'].iloc[-1]),
                'open': float(history['Open'].iloc[-1])
            }
        
        try:
            return self._retry_wrapper(_fetch)
        except Exception as e:
            self.logger.error(f"获取实时数据失败: {symbol}, 错误: {str(e)}")
            return {'error': f'获取实时数据时出错: {str(e)}'}
    
    def get_company_info(self, symbol: str) -> Dict:
        """
        获取公司基本信息
        
        Args:
            symbol: 股票代码
            
        Returns:
            公司基本信息字典
        """
        self._rate_limit()
        
        def _fetch():
            ticker = self._get_ticker(symbol)
            info = ticker.info
            if not info:
                raise ValueError(f"无法获取 {symbol} 的公司信息")
            return info
        
        try:
            return self._retry_wrapper(_fetch)
        except Exception as e:
            self.logger.error(f"获取公司信息失败: {symbol}, 错误: {str(e)}")
            return {'error': f'获取公司信息时出错: {str(e)}'}
    
    def get_financial_data(self, symbol: str) -> Dict:
        """
        获取财务数据
        
        Args:
            symbol: 股票代码
            
        Returns:
            包含财务报表的字典
        """
        self._rate_limit()
        
        def _fetch():
            ticker = self._get_ticker(symbol)
            
            financial_data = {}
            
            # 获取各种财务报表
            try:
                financial_data['income_statement'] = ticker.financials
            except:
                financial_data['income_statement'] = pd.DataFrame()
            
            try:
                financial_data['balance_sheet'] = ticker.balance_sheet
            except:
                financial_data['balance_sheet'] = pd.DataFrame()
            
            try:
                financial_data['cash_flow'] = ticker.cashflow
            except:
                financial_data['cash_flow'] = pd.DataFrame()
            
            try:
                financial_data['quarterly_financials'] = ticker.quarterly_financials
            except:
                financial_data['quarterly_financials'] = pd.DataFrame()
            
            try:
                financial_data['quarterly_balance_sheet'] = ticker.quarterly_balance_sheet
            except:
                financial_data['quarterly_balance_sheet'] = pd.DataFrame()
            
            try:
                financial_data['quarterly_cashflow'] = ticker.quarterly_cashflow
            except:
                financial_data['quarterly_cashflow'] = pd.DataFrame()
            
            # 获取基本信息
            try:
                financial_data['info'] = ticker.info
            except:
                financial_data['info'] = {}
            
            return financial_data
        
        try:
            return self._retry_wrapper(_fetch)
        except Exception as e:
            self.logger.error(f"获取财务数据失败: {symbol}, 错误: {str(e)}")
            return {'error': f'获取财务数据时出错: {str(e)}'}
    
    def clear_cache(self):
        """清除ticker缓存"""
        self._ticker_cache.clear()
    
    def get_multiple_stocks_data(self, symbols: List[str], **kwargs) -> Dict[str, pd.DataFrame]:
        """
        批量获取多个股票的数据
        
        Args:
            symbols: 股票代码列表
            **kwargs: 传递给get_stock_data的参数
            
        Returns:
            股票代码到数据DataFrame的映射
        """
        results = {}
        for symbol in symbols:
            try:
                results[symbol] = self.get_stock_data(symbol, **kwargs)
            except Exception as e:
                self.logger.error(f"批量获取 {symbol} 数据失败: {str(e)}")
                results[symbol] = pd.DataFrame()  # 空DataFrame表示失败
        
        return results


# 创建全局实例
default_data_fetcher = YFinanceDataFetcher()


def get_data_fetcher() -> DataFetcher:
    """获取默认的数据获取器实例"""
    return default_data_fetcher