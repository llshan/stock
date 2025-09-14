#!/usr/bin/env python3
"""
财务指标分析工具 - Financial Metrics Analysis Tool

功能 Features:
- 展示股票财务报表的关键指标和趋势
- 支持损益表、资产负债表、现金流量表分析
- 多股票财务对比和历史趋势分析
- 格式化财务数据展示（支持B/M/K单位）

用法示例 Usage Examples:

显示财务概览 Financial Summary:
  financial-metrics summary AAPL
  financial-metrics summary MRK

查看损益表指标 Income Statement Metrics:
  financial-metrics metrics AAPL --type income_statement

查看资产负债表 Balance Sheet Metrics:
  financial-metrics metrics AAPL --type balance_sheet

查看现金流量表 Cash Flow Metrics:
  financial-metrics metrics AAPL --type cash_flow

指定时间期间 Specific Period:
  financial-metrics metrics AAPL --period 2024-12-31

多股票对比 Compare Multiple Stocks:
  financial-metrics compare AAPL MSFT GOOG
  financial-metrics compare AAPL MSFT --type income_statement

趋势分析 Trend Analysis:
  financial-metrics trend AAPL "Net income"
  financial-metrics trend AAPL "Total assets"

自定义数据库路径 Custom Database Path:
  financial-metrics summary AAPL --db-path /path/to/database.db

详细输出模式 Verbose Mode:
  financial-metrics summary AAPL -v

支持的报表类型 Supported Statement Types:
- income_statement: 损益表 (收入、成本、利润等)
- balance_sheet: 资产负债表 (资产、负债、股东权益)  
- cash_flow: 现金流量表 (经营、投资、筹资现金流)
"""

import argparse
import logging
from typing import List

from stock_analysis.utils.logging_utils import setup_logging
from stock_analysis.utils.display_financial_metrics import (
    display_financial_summary,
    display_detailed_metrics,
    display_compare,
    display_metric_trend,
)


def cmd_summary(args: argparse.Namespace) -> int:
    """显示股票财务概览（委托统一展示模块）"""
    setup_logging('INFO' if args.verbose else 'WARNING')
    symbol = args.symbol.upper()
    try:
        display_financial_summary(symbol, args.db_path)
        return 0
    except Exception as e:
        logging.getLogger(__name__).error(f"查询失败: {e}")
        return 1


def cmd_metrics(args: argparse.Namespace) -> int:
    """显示详细财务指标"""
    setup_logging('INFO' if args.verbose else 'WARNING')
    try:
        display_detailed_metrics(
            args.symbol.upper(),
            db_path=args.db_path,
            type=args.type,
            period=args.period,
            limit=args.limit,
        )
        return 0
    except Exception as e:
        logging.getLogger(__name__).error(f"查询失败: {e}")
        return 1


def cmd_compare(args: argparse.Namespace) -> int:
    """比较多个股票的财务指标"""
    setup_logging('INFO' if args.verbose else 'WARNING')
    try:
        display_compare([s.upper() for s in args.symbols], args.db_path)
        return 0
    except Exception as e:
        logging.getLogger(__name__).error(f"对比失败: {e}")
        return 1


def cmd_trend(args: argparse.Namespace) -> int:
    """显示指标趋势"""
    setup_logging('INFO' if args.verbose else 'WARNING')
    try:
        display_metric_trend(args.symbol.upper(), args.metric_name, args.db_path)
        return 0
    except Exception as e:
        logging.getLogger(__name__).error(f"趋势查询失败: {e}")
        return 1


def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器"""
    p = argparse.ArgumentParser(description='财务指标查看工具')
    sub = p.add_subparsers(dest='command', required=True)

    # summary子命令
    summary = sub.add_parser('summary', help='显示财务概览')
    summary.add_argument('symbol', help='股票代码')
    summary.add_argument('--db-path', default='database/stock_data.db', help='数据库路径')
    summary.add_argument('--limit', type=int, default=5, help='显示行数限制')
    summary.add_argument('-v', '--verbose', action='store_true', help='详细日志')
    summary.set_defaults(func=cmd_summary)

    # metrics子命令
    metrics = sub.add_parser('metrics', help='查看详细财务指标')
    metrics.add_argument('symbol', help='股票代码')
    metrics.add_argument('--type', choices=['income_statement', 'balance_sheet', 'cash_flow'],
                        help='报表类型')
    metrics.add_argument('--period', help='指定期间 (如 2024-09-30)')
    metrics.add_argument('--limit', type=int, default=50, help='显示行数限制')
    metrics.add_argument('--db-path', default='database/stock_data.db', help='数据库路径')
    metrics.add_argument('-v', '--verbose', action='store_true', help='详细日志')
    metrics.set_defaults(func=cmd_metrics)

    # compare子命令
    compare = sub.add_parser('compare', help='比较多个股票')
    compare.add_argument('symbols', nargs='+', help='股票代码列表')
    compare.add_argument('--db-path', default='database/stock_data.db', help='数据库路径')
    compare.add_argument('-v', '--verbose', action='store_true', help='详细日志')
    compare.set_defaults(func=cmd_compare)

    # trend子命令
    trend = sub.add_parser('trend', help='显示指标趋势')
    trend.add_argument('symbol', help='股票代码')
    trend.add_argument('metric_name', help='指标名称')
    trend.add_argument('--db-path', default='database/stock_data.db', help='数据库路径')
    trend.add_argument('-v', '--verbose', action='store_true', help='详细日志')
    trend.set_defaults(func=cmd_trend)

    return p


def main() -> int:
    """主函数"""
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == '__main__':
    raise SystemExit(main())

