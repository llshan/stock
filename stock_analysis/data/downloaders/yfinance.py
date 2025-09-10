#!/usr/bin/env python3
"""
股票数据下载器
下载从2000年开始的股票价格数据和财务报表
"""

import logging
import time
import random
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import pandas as pd
import yfinance as yf
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..models import (
    BasicInfo,
    ComprehensiveData,
    FinancialData,
    FinancialStatement,
    PriceData,
    StockData,
    SummaryStats,
)
from ..quality import assess_data_quality
from .base import BaseDownloader


class YFinanceDataDownloader(BaseDownloader):
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: int = 30,
        y_min_interval: float = 0.8,
        y_retry_total: int = 5,
        y_backoff_factor: float = 1.5,
        strict_meta_check: bool = False,
        use_fast_info: bool = True,
    ):
        """初始化股票数据下载器（增强抗限流能力）"""
        super().__init__(max_retries=max_retries, base_delay=base_delay)
        self.start_date = "2000-01-01"
        # 节流配置
        self._min_interval = y_min_interval
        self._last_ts = 0.0
        self._strict_meta_check = strict_meta_check
        self._use_fast_info = use_fast_info
        # 复用会话 + 自动重试
        self.session = requests.Session()
        retries = Retry(
            total=y_retry_total,
            backoff_factor=y_backoff_factor,
            status_forcelist=[429, 502, 503, 504],
            allowed_methods=["GET", "POST"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retries, pool_connections=20, pool_maxsize=20)
        self.session.mount("https://", adapter)
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
        )

    def _throttle(self) -> None:
        now = time.monotonic()
        wait = self._min_interval - (now - self._last_ts)
        if wait > 0:
            time.sleep(wait + random.uniform(0, 0.25))
        self._last_ts = time.monotonic()

    def _ticker(self, symbol: str):
        return yf.Ticker(symbol, session=self.session)

    def download_stock_data(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        incremental: bool = True,
        use_retry: bool = True,
    ) -> Union[StockData, Dict[str, str]]:
        """
        下载股票的历史价格数据

        Args:
            symbol: 股票代码
            start_date: 开始日期，默认2000-01-01
            incremental: 是否进行增量下载
            use_retry: 是否使用重试机制

        Returns:
            包含价格数据的字典
        """

        def _download_data() -> Union[StockData, Dict[str, str]]:
            return self._download_stock_data_internal(symbol, start_date, incremental)

        if use_retry:
            return self._retry_with_backoff(_download_data, symbol)
        else:
            return _download_data()

    def _download_stock_data_internal(
        self, symbol: str, start_date: Optional[str] = None, incremental: bool = True
    ) -> Union[StockData, Dict[str, str]]:
        """内部股票数据下载实现"""
        try:
            # 设置默认开始日期
            if start_date is None:
                start_date = self.start_date

            self.logger.info(f"📈 下载 {symbol} 股票数据 (从 {start_date})")

            # 检查日期范围是否有效
            today = datetime.now().strftime('%Y-%m-%d')
            if start_date >= today:
                self.logger.info(f"📊 {symbol} 数据已是最新，无需更新")
                return StockData(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=today,
                    data_points=0,
                    price_data=PriceData(
                        dates=[],
                        open=[],
                        high=[],
                        low=[],
                        close=[],
                        volume=[],
                        adj_close=[],
                    ),
                    summary_stats=SummaryStats(
                        min_price=0.0,
                        max_price=0.0,
                        mean_price=0.0,
                        std_price=0.0,
                        total_volume=0,
                    ),
                    downloaded_at=datetime.now().isoformat(),
                    incremental_update=True,
                    no_new_data=True,
                )

            # 下载股票数据（统一会话 + 节流，可选元信息预检）
            ticker = self._ticker(symbol)
            if self._strict_meta_check:
                self._throttle()
                try:
                    if hasattr(ticker, 'get_info'):
                        ticker.get_info() or {}
                    else:
                        ticker.info or {}
                except Exception as meta_err:
                    raise RuntimeError(f"yfinance 预检失败: {meta_err}")
            self._throttle()
            hist_data = ticker.history(start=start_date, end=today)

            if hist_data.empty:
                return {
                    'error': f'无法获取 {symbol} 的历史数据（时间范围: {start_date} 到 {today}）'
                }

            # 转换为dataclass格式
            price_data = PriceData(
                dates=[d.strftime('%Y-%m-%d') for d in hist_data.index],
                open=hist_data['Open'].tolist(),
                high=hist_data['High'].tolist(),
                low=hist_data['Low'].tolist(),
                close=hist_data['Close'].tolist(),
                volume=hist_data['Volume'].tolist(),
                adj_close=hist_data['Adj Close'].tolist(),
            )

            summary_stats = SummaryStats(
                min_price=float(hist_data['Close'].min()),
                max_price=float(hist_data['Close'].max()),
                mean_price=float(hist_data['Close'].mean()),
                std_price=float(hist_data['Close'].std()),
                total_volume=int(hist_data['Volume'].sum()),
            )

            stock_data = StockData(
                symbol=symbol,
                start_date=start_date,
                end_date=today,
                data_points=len(hist_data),
                price_data=price_data,
                summary_stats=summary_stats,
                downloaded_at=datetime.now().isoformat(),
                incremental_update=incremental,
            )

            self.logger.info(f"✅ {symbol} 数据下载完成: {len(hist_data)} 个数据点")
            return stock_data

        except Exception as e:
            error_msg = f"下载 {symbol} 股票数据失败: {str(e)}"
            self.logger.error(error_msg)
            return {'error': error_msg}

    def download_financial_data(
        self, symbol: str, use_retry: bool = True
    ) -> Union[FinancialData, Dict[str, str]]:
        """
        下载股票的财务报表数据

        Args:
            symbol: 股票代码
            use_retry: 是否使用重试机制

        Returns:
            包含财务数据的字典
        """

        def _download_data() -> Union[FinancialData, Dict[str, str]]:
            return self._download_financial_data_internal(symbol)

        if use_retry:
            return self._retry_with_backoff(_download_data, symbol)
        else:
            return _download_data()

    def _download_financial_data_internal(
        self, symbol: str
    ) -> Union[FinancialData, Dict[str, str]]:
        """内部财务数据下载实现（更健壮，避免 info 失败中断）"""
        try:
            self.logger.info(f"💼 下载 {symbol} 财务报表数据")
            ticker = self._ticker(symbol)
            # fast_info 优先
            fast = None
            if self._use_fast_info:
                try:
                    self._throttle()
                    fast = ticker.fast_info
                except Exception:
                    fast = None
            # 必要时再获取 info（或启用严格预检时）
            info: Dict[str, Any] = {}
            if self._strict_meta_check or not fast:
                self._throttle()
                if hasattr(ticker, 'get_info'):
                    info = ticker.get_info() or {}
                else:
                    info = ticker.info or {}

            name = (getattr(fast, 'shortName', None) if fast is not None else None) or info.get('longName', '')
            market_cap = (getattr(fast, 'market_cap', None) if fast is not None else None) or info.get('marketCap', 0)
            basic_info = BasicInfo(
                company_name=name or '',
                sector=info.get('sector', ''),
                industry=info.get('industry', ''),
                market_cap=market_cap or 0,
                employees=info.get('fullTimeEmployees', 0),
                description=info.get('longBusinessSummary', ''),
            )

            # 获取财务报表（逐次节流）
            self._throttle()
            financials = ticker.financials
            self._throttle()
            balance_sheet = ticker.balance_sheet
            self._throttle()
            cash_flow = ticker.cashflow

            financial_statements = {}

            # 处理损益表
            if not financials.empty:
                income_stmt = self._process_financial_statement(financials, '损益表')
                if 'error' not in income_stmt:
                    financial_statements['income_statement'] = FinancialStatement.from_dict(
                        income_stmt
                    )

            # 处理资产负债表
            if not balance_sheet.empty:
                balance_stmt = self._process_financial_statement(balance_sheet, '资产负债表')
                if 'error' not in balance_stmt:
                    financial_statements['balance_sheet'] = FinancialStatement.from_dict(
                        balance_stmt
                    )

            # 处理现金流量表
            if not cash_flow.empty:
                cash_flow_stmt = self._process_financial_statement(cash_flow, '现金流量表')
                if 'error' not in cash_flow_stmt:
                    financial_statements['cash_flow'] = FinancialStatement.from_dict(cash_flow_stmt)

            financial_data = FinancialData(
                symbol=symbol,
                basic_info=basic_info,
                financial_statements=financial_statements,
                downloaded_at=datetime.now().isoformat(),
            )

            self.logger.info(f"✅ {symbol} 财务数据下载完成")
            return financial_data

        except Exception as e:
            error_msg = f"下载 {symbol} 财务数据失败: {str(e)}"
            self.logger.error(error_msg)
            return {'error': error_msg}

    def _process_financial_statement(self, df: pd.DataFrame, statement_type: str) -> Dict[str, Any]:
        """处理财务报表数据"""
        try:
            # 获取最近4年的数据
            processed_data: Dict[str, Any] = {
                'statement_type': statement_type,
                'periods': [col.strftime('%Y-%m-%d') for col in df.columns],
                'items': {},
            }

            for index in df.index:
                # 清理指标名称
                item_name = str(index).strip()
                if item_name and item_name != 'nan':
                    values: List[Optional[float]] = []
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

    def download_comprehensive_data(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        incremental: bool = True,
        use_retry: bool = True,
    ) -> ComprehensiveData:
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
        self.logger.info(
            f"🚀 开始下载 {symbol} 的综合数据{'（增量模式）' if incremental else '（全量模式）'}{retry_text}"
        )

        # 下载股票价格数据
        stock_data = self.download_stock_data(symbol, start_date, incremental, use_retry)

        # 添加延迟避免API限制
        time.sleep(1)

        # 下载财务数据
        financial_data = self.download_financial_data(symbol, use_retry)

        # 评估数据质量（统一工具函数）
        data_quality = assess_data_quality(stock_data, financial_data, self.start_date)

        # 创建综合数据对象
        stock_data_obj = None
        financial_data_obj = None

        if isinstance(stock_data, StockData):
            stock_data_obj = stock_data
        elif isinstance(stock_data, dict) and 'error' not in stock_data:
            stock_data_obj = StockData.from_dict(stock_data)

        if isinstance(financial_data, FinancialData):
            financial_data_obj = financial_data
        elif isinstance(financial_data, dict) and 'error' not in financial_data:
            financial_data_obj = FinancialData.from_dict(financial_data)

        comprehensive_data = ComprehensiveData(
            symbol=symbol,
            download_timestamp=datetime.now().isoformat(),
            stock_data=stock_data_obj,
            financial_data=financial_data_obj,
            data_quality=data_quality,
        )

        return comprehensive_data

    # 批量相关操作已移除：此下载器仅提供单只股票下载接口

    # 质量评估与评级逻辑统一在 quality.py 中


if __name__ == "__main__":
    # 配置日志
    from stock_analysis.utils.logging_utils import setup_logging

    from ..config import get_default_watchlist

    setup_logging()

    logging.getLogger(__name__).info("🚀 股票数据下载器（使用DataService）")
    logging.getLogger(__name__).info("=" * 50)
    logging.getLogger(__name__).info("⚠️  注意: 这个示例展示下载器功能，但不包含数据库存储")
    logging.getLogger(__name__).info("💡 要使用完整功能（包括数据库），请使用 DataService 类")

    # 创建下载器
    downloader = YFinanceDataDownloader()

    # 示例股票列表（演示用途，统一方法）
    watchlist = get_default_watchlist()

    logging.getLogger(__name__).info(f"📊 将下载 {len(watchlist)} 个股票的数据:")
    for i, symbol in enumerate(watchlist, 1):
        logging.getLogger(__name__).info(f"  {i:2d}. {symbol}")

    logging.getLogger(__name__).info(f"⏰ 数据时间范围: {downloader.start_date} 至今")
    logging.getLogger(__name__).info("📈 包含: 股票价格数据 + 财务报表数据")

    # 逐个下载（演示单股接口）
    results = {}
    for i, sym in enumerate(watchlist, 1):
        logging.getLogger(__name__).info(f"📥 [{i}/{len(watchlist)}] 下载 {sym} …")
        data = downloader.download_comprehensive_data(sym)
        results[sym] = data
        time.sleep(1)
    logging.getLogger(__name__).info("📊 已完成逐只下载示例。")


def main() -> None:
    """主函数，用于 python -m Stock.data_service.downloaders.yfinance 调用"""
    if __name__ == "__main__":
        # 运行主程序代码
        pass
