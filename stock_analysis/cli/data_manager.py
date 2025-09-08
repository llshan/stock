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
from pathlib import Path

import pandas as pd

from stock_analysis.utils.logging_utils import setup_logging
from stock_analysis.data import DataService, create_storage
from stock_analysis.data.config import get_default_watchlist


def cmd_download(args: argparse.Namespace) -> int:
    setup_logging('INFO' if args.verbose else 'WARNING')
    logger = logging.getLogger(__name__)

    dbp = str(Path(args.db_path))
    storage = create_storage('sqlite', db_path=dbp)
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

    # 解析下载模式（默认 stock-only）
    mode = 'stock'
    if getattr(args, 'comprehensive', False):
        mode = 'comprehensive'
    elif getattr(args, 'financial_only', False):
        mode = 'financial'
    else:
        # 显式 stock-only 或未指定
        mode = 'stock'

    if mode == 'comprehensive':
        logger.info(
            f"开始下载综合数据（价格+财务） {len(symbols)} 个，起始: {args.start_date or '自动增量'}"
        )
    elif mode == 'financial':
        logger.info(
            f"开始下载财务数据 {len(symbols)} 个"
        )
    else:
        logger.info(
            f"开始下载价格数据 {len(symbols)} 个，起始: {args.start_date or '自动增量'}（策略：新股Stooq全量，老股<=阈值天数用yfinance，否则Stooq）"
        )

    # 逐只下载并入库（DataService 内部自动选择来源）
    results = {}
    strategy_usage = {}
    ok = 0
    for i, sym in enumerate(symbols):
        try:
            if mode == 'comprehensive':
                stock_r = service.download_and_store_stock_data(
                    sym, start_date=args.start_date or "2000-01-01"
                )
                fin_r = service.download_and_store_financial_data(sym)
                r = {
                    'success': stock_r.get('success', False) and fin_r.get('success', False),
                    'stock': stock_r,
                    'financial': fin_r,
                }
                results[sym] = r
                if r.get('success'):
                    ok += 1
            elif mode == 'financial':
                r = service.download_and_store_financial_data(sym)
                results[sym] = r
                if r.get('success'):
                    ok += 1
            else:
                r = service.download_and_store_stock_data(
                    sym, start_date=args.start_date or "2000-01-01"
                )
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
            if mode == 'comprehensive':
                stock_r = r.get('stock', {})
                fin_r = r.get('financial', {})
                stock_msg = (
                    "已最新" if stock_r.get('no_new_data') else f"入库{stock_r.get('data_points', 0)}条"
                ) if isinstance(stock_r, dict) else "完成"
                if fin_r.get('no_new_data'):
                    fin_msg = "已最新（跳过）"
                else:
                    fin_msg = f"写入{fin_r.get('statements', '?')}份报表" if 'statements' in fin_r else "完成"
                logger.info(f"{sym}: 价格={stock_msg}，财务={fin_msg}")
            elif mode == 'financial':
                if r.get('no_new_data'):
                    logger.info(f"{sym}: 财务已最新（跳过刷新）")
                else:
                    stmts = r.get('statements')
                    logger.info(f"{sym}: 写入财务报表 {stmts} 份")
            else:
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

    dbp = str(Path(args.db_path))
    storage = create_storage('sqlite', db_path=dbp)
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

    # 设置 pandas 显示选项以优化对齐
    try:
        pd.set_option('display.width', 120)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.precision', 4)
        pd.set_option('display.float_format', '{:.4f}'.format)
    except Exception:
        pass
    
    # 打印前后各 N 行
    n = min(args.limit, len(df))
    
    print("\n前几行:")
    print(df.head(n).to_string(index=True, justify='right', col_space=10))
    
    if len(df) > n:
        print("\n后几行:")
        print(df.tail(n).to_string(index=True, justify='right', col_space=10))

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

    # 下载模式：互斥
    mode_group = dl.add_mutually_exclusive_group()
    mode_group.add_argument('--comprehensive', action='store_true', help='下载价格+财务并入库（综合）')
    mode_group.add_argument('--financial-only', dest='financial_only', action='store_true', help='仅下载财务并入库')
    mode_group.add_argument('--stock-only', dest='stock_only', action='store_true', help='仅下载价格并入库（默认）')
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
