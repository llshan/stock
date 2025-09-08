#!/usr/bin/env python3
"""
简化版数据管理工具

功能:
- download: 针对一个或多个股票下载数据并入库
- query: 查询某一只股票的价格数据
"""

import argparse
import logging
from typing import List

import pandas as pd

from utils.logging_utils import setup_logging
from data_service import DataService, create_storage
from data_service.config import get_default_watchlist


def cmd_download(args: argparse.Namespace) -> int:
    setup_logging('INFO' if args.verbose else 'WARNING')
    logger = logging.getLogger(__name__)

    storage = create_storage('sqlite', db_path=args.db_path)
    service = DataService(storage)

    # 选择股票列表
    if args.symbols:
        symbols: List[str] = [s.upper() for s in args.symbols]
    elif args.use_default_watchlist:
        symbols = [s.upper() for s in get_default_watchlist()]
        logger.info(f"使用默认关注列表（{len(symbols)} 个）")
    else:
        logger.error("请使用 -s/--symbols 指定股票，或加上 --use-default-watchlist")
        return 2

    logger.info(f"开始下载 {len(symbols)} 个股票，起始: {args.start_date or '自动增量'}（混合：新股Stooq全量，老股>100天yfinance，否则Stooq）")

    # 逐只下载并入库（DataService 内部统一走 Hybrid）
    results = {}
    strategy_usage = {}
    ok = 0
    for i, sym in enumerate(symbols):
        try:
            r = service.download_and_store_stock_data(sym, start_date=args.start_date or "2000-01-01")
            results[sym] = r
            used = r.get('used_strategy', 'Unknown') if isinstance(r, dict) else 'Unknown'
            strategy_usage[used] = strategy_usage.get(used, 0) + 1
            if r.get('success'):
                ok += 1
        except Exception as e:
            results[sym] = {'success': False, 'error': str(e)}
        if i < len(symbols) - 1:
            import time; time.sleep(2)

    fail = len(symbols) - ok
    logger.info(f"完成：成功{ok}，失败{fail}")
    if strategy_usage:
        logger.info("策略使用统计：" + ", ".join(f"{k}={v}" for k, v in strategy_usage.items()))

    # 逐个结果
    for sym, r in results.items():
        if r.get('success'):
            used = r.get('used_strategy')
            if r.get('no_new_data'):
                logger.info(f"{sym}: 已最新，无需更新{f'（策略：{used}）' if used else ''}")
            else:
                logger.info(f"{sym}: 入库 {r.get('data_points', 0)} 条{f'（策略：{used}）' if used else ''}")
        else:
            logger.warning(f"{sym}: 失败 - {r.get('error','未知错误')}")

    service.close()
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    setup_logging('INFO' if args.verbose else 'WARNING')
    logger = logging.getLogger(__name__)

    if not args.symbol:
        logger.error("请使用 -s/--symbol 指定股票代码")
        return 2

    storage = create_storage('sqlite', db_path=args.db_path)
    data = storage.get_stock_data(args.symbol.upper(), start_date=args.start_date, end_date=args.end_date)

    if data is None or data.data_points == 0:
        logger.info("无数据")
        storage.close()
        return 0

    # 转为 DataFrame 以便展示
    pd_data = {
        'date': data.price_data.dates,
        'open': data.price_data.open,
        'high': data.price_data.high,
        'low': data.price_data.low,
        'close': data.price_data.close,
        'volume': data.price_data.volume,
        'adj_close': data.price_data.adj_close,
    }
    df = pd.DataFrame(pd_data)

    # 统计与范围
    first = min(df['date']) if not df.empty else None
    last = max(df['date']) if not df.empty else None
    logger.info(f"{args.symbol.upper()}: 共 {len(df)} 行，范围 {first} ~ {last}")

    # 打印前后各 N 行
    n = min(args.limit, len(df))
    try:
        pd.set_option('display.width', 120)
    except Exception:
        pass
    print("\n前几行:\n", df.head(n))
    if len(df) > n:
        print("\n后几行:\n", df.tail(n))

    storage.close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description='股票数据管理工具')
    sub = p.add_subparsers(dest='command', required=True)

    # download 子命令
    dl = sub.add_parser('download', help='下载一个或多个股票的数据并入库')
    dl.add_argument('-s', '--symbols', nargs='+', help='股票代码列表，例如 AAPL MSFT')
    dl.add_argument('--db-path', default='database/stock_data.db', help='数据库路径')
    dl.add_argument('--start-date', help='起始日期(YYYY-MM-DD)，默认自动增量')
    dl.add_argument('--max-retries', type=int, default=3, help='最大重试次数')
    dl.add_argument('--base-delay', type=int, default=30, help='重试基础延迟(秒)')
    dl.add_argument('--use-default-watchlist', action='store_true', help='使用默认关注列表（配置或环境变量 WATCHLIST）')
    dl.add_argument('-v', '--verbose', action='store_true', help='详细日志')
    dl.set_defaults(func=cmd_download)

    # query 子命令
    q = sub.add_parser('query', help='查询某只股票的价格数据')
    q.add_argument('-s', '--symbol', required=True, help='股票代码')
    q.add_argument('--db-path', default='database/stock_data.db', help='数据库路径')
    q.add_argument('--start-date', help='起始日期(YYYY-MM-DD)')
    q.add_argument('--end-date', help='结束日期(YYYY-MM-DD)')
    q.add_argument('--limit', type=int, default=5, help='每端显示的行数（前/后）')
    q.add_argument('-v', '--verbose', action='store_true', help='详细日志')
    q.set_defaults(func=cmd_query)

    return p


def main():
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == '__main__':
    raise SystemExit(main())
