#!/usr/bin/env python3
"""
Stooq股票数据下载器
使用pandas_datareader从Stooq获取历史股票数据
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Union

import pandas_datareader as pdr

from ..models import PriceData, StockData, SummaryStats
from .base import BaseDownloader, DownloaderError


class StooqDataDownloader(BaseDownloader):
    def __init__(self, max_retries: int = 3, base_delay: int = 5):
        """
        初始化Stooq数据下载器

        Args:
            max_retries: 最大重试次数
            base_delay: 基础延迟时间（秒）
        """
        super().__init__(max_retries=max_retries, base_delay=base_delay)
        # Stooq数据源配置
        self.data_source = 'stooq'

    def download_stock_data(
        self, symbol: str, start_date: str = "2000-01-01", end_date: Optional[str] = None
    ) -> Union[StockData, Dict[str, str]]:
        """
        从Stooq下载股票历史数据

        Args:
            symbol: 股票代码（如AAPL.US）
            start_date: 开始日期
            end_date: 结束日期（默认今天）

        Returns:
            包含价格数据的字典
        """

        def _download() -> Union[StockData, Dict[str, str]]:
            return self._download_stock_data_internal(symbol, start_date, end_date)

        return self._retry_with_backoff(_download, symbol)

    def _download_stock_data_internal(
        self, symbol: str, start_date: str, end_date: Optional[str] = None
    ) -> Union[StockData, Dict[str, str]]:
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
                raise DownloaderError(f'从Stooq无法获取 {symbol} 的历史数据')

            # 转换为dataclass格式
            price_data = PriceData(
                dates=[d.strftime('%Y-%m-%d') for d in data.index],
                open=data['Open'].tolist(),
                high=data['High'].tolist(),
                low=data['Low'].tolist(),
                close=data['Close'].tolist(),
                volume=data['Volume'].tolist(),
                adj_close=data['Close'].tolist(),  # Stooq数据通常已调整
            )

            # Note(jlshan): need to check the logic. Is it calculation the summary for the whole period?
            summary_stats = SummaryStats(
                min_price=float(data['Close'].min()),
                max_price=float(data['Close'].max()),
                mean_price=float(data['Close'].mean()),
                std_price=float(data['Close'].std()),
                total_volume=int(data['Volume'].sum()),
            )

            stock_data = StockData(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                data_points=len(data),
                price_data=price_data,
                summary_stats=summary_stats,
                downloaded_at=datetime.now().isoformat(),
                data_source='Stooq',
                incremental_update=False,
            )

            self.logger.info(f"✅ {symbol} Stooq数据下载完成: {len(data)} 个数据点")
            return stock_data

        except Exception as e:
            error_msg = f"从Stooq下载 {symbol} 数据失败: {str(e)}"
            self.logger.error(error_msg)
            if isinstance(e, DownloaderError):
                raise
            raise DownloaderError(error_msg)
