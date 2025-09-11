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
from .base import BaseDownloader


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
                return {'error': f'从Stooq无法获取 {symbol} 的历史数据'}

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


if __name__ == "__main__":
    # 测试Stooq下载器
    from utils.logging_utils import setup_logging

    from ..config import get_default_watchlist

    setup_logging()
    logging.getLogger(__name__).info("🌐 Stooq股票数据下载器测试")
    logging.getLogger(__name__).info("=" * 50)

    downloader = StooqDataDownloader()

    # 测试连接
    if downloader.test_connection():
        logging.getLogger(__name__).info("✅ Stooq连接测试成功")

        # 示例：逐只下载一个简短的关注列表
        symbols = get_default_watchlist()
        for i, sym in enumerate(symbols, 1):
            logging.getLogger(__name__).info(f"📈 [{i}/{len(symbols)}] 测试下载 {sym} 数据…")
            result = downloader.download_stock_data(sym, start_date='2000-01-01')
            if isinstance(result, dict) and 'error' in result:
                logging.getLogger(__name__).error(f"❌ {sym} 数据下载失败: {result['error']}")
            elif isinstance(result, StockData):
                logging.getLogger(__name__).info(
                    f"✅ {sym}: {result.data_points} 个数据点，范围 {result.start_date} ~ {result.end_date}"
                )
            time.sleep(1)

    else:
        logging.getLogger(__name__).error("❌ Stooq连接测试失败，请检查网络连接")
