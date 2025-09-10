#!/usr/bin/env python3
"""
简单的 Twelve Data 下载测试脚本

示例:
  export TWELVE_DATA_API_KEY=your_key
  python cli/twelvedata_test.py --symbol AAPL --start-date 2024-01-01
"""

import argparse
import logging
from typing import Optional

from stock_analysis.data import StockData
from stock_analysis.data.downloaders.twelvedata import TwelveDataDownloader
from stock_analysis.utils.logging_utils import setup_logging


def run(symbol: str, start_date: Optional[str], end_date: Optional[str], api_key: Optional[str]) -> int:
    setup_logging("INFO")
    logger = logging.getLogger(__name__)

    dl = TwelveDataDownloader(api_key=api_key)
    res = dl.download_stock_data(symbol, start_date=start_date, end_date=end_date, use_retry=True)

    if isinstance(res, dict) and res.get("error"):
        logger.error(f"下载失败: {res['error']}")
        return 1

    assert isinstance(res, StockData)
    logger.info(
        f"✅ {symbol} 下载成功: 点数={res.data_points}, 范围={res.start_date} ~ {res.end_date}, 来源={res.data_source}"
    )

    # 打印前后各 3 条
    dates = res.price_data.dates
    closes = res.price_data.close
    n = min(3, len(dates))
    if n > 0:
        head = ", ".join(f"{dates[i]}:{closes[i]:.2f}" for i in range(n))
        print("前几条:", head)
        print("后几条:", ", ".join(f"{dates[-n+i]}:{closes[-n+i]:.2f}" for i in range(n)))

    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Twelve Data API 下载测试")
    p.add_argument("--symbol", default="AAPL", help="股票代码，默认 AAPL")
    p.add_argument("--start-date", dest="start_date", help="开始日期 YYYY-MM-DD")
    p.add_argument("--end-date", dest="end_date", help="结束日期 YYYY-MM-DD")
    p.add_argument("--api-key", dest="api_key", help="Twelve Data API Key（默认读环境变量）")
    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return run(args.symbol.upper(), args.start_date, args.end_date, args.api_key)


if __name__ == "__main__":
    raise SystemExit(main())

