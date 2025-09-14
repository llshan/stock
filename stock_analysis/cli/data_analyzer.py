#!/usr/bin/env python3
"""
股票技术分析工具 - Stock Technical Analysis Tool

功能 Features:
- 对指定股票运行可插拔技术分析算子流水线
- 支持移动平均线、RSI、财务比率、健康评分等多种指标
- 分析结果以 JSON 格式保存到本地文件

用法示例 Usage Examples:

基础分析 Basic Analysis:
  stock-analyze -s AAPL

多股票分析 Multiple Stocks:
  stock-analyze -s AAPL MSFT GOOG --period 6mo

自定义分析算子 Custom Operators:
  stock-analyze -s AAPL --operators ma,rsi,fin_ratios,fin_health

指定时间范围 Date Range:
  stock-analyze -s AAPL --start-date 2023-01-01 --end-date 2024-01-01

从文件读取股票列表 From File:
  stock-analyze --symbols-file my_stocks.txt --period 1y

自定义输出文件 Custom Output:
  stock-analyze -s AAPL --output my_analysis.json

详细日志模式 Verbose Mode:
  stock-analyze -s AAPL -v

支持的分析算子 Supported Operators:
- ma: 移动平均线 (5, 10, 20, 50日)
- rsi: 相对强弱指数 (14日)
- fin_ratios: 财务比率 (净利润率、ROE、负债率、PE)
- fin_health: 财务健康评分 (A-F等级)
- drop_alert: 跌幅警报 (1日)
- drop_alert_7d: 7日跌幅警报

支持的时间周期 Supported Periods:
- 6mo, 1y, 2y, 5y, max
- 或使用 --start-date 和 --end-date 指定具体日期
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from stock_analysis.analysis import AnalysisService
from stock_analysis.analysis.config import get_config
from stock_analysis.utils.logging_utils import setup_logging

logger = logging.getLogger(__name__)


def _period_to_start(period: Optional[str]) -> Optional[str]:
    if not period:
        return None
    try:
        now = datetime.now()
        p = period.lower()
        if p.endswith('mo'):
            months = int(p[:-2])
            days = max(months * 30, 1)
            return (now - timedelta(days=days)).strftime('%Y-%m-%d')
        if p.endswith('y'):
            years = int(p[:-1])
            return (now - timedelta(days=years * 365)).strftime('%Y-%m-%d')
        if p in ('max', 'all'):
            return get_config().data.default_start_date
    except Exception:
        pass
    return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='股票数据分析工具')

    # 输入与范围
    parser.add_argument('-s', '--symbols', nargs='+', help='股票代码列表，例如 AAPL MSFT')
    parser.add_argument('--symbols-file', help='包含股票代码的文件（每行一个）')
    parser.add_argument('--db-path', default='database/stock_data.db', help='数据库路径')
    parser.add_argument('--start-date', help='起始日期(YYYY-MM-DD)，优先于 --period')
    parser.add_argument('--end-date', help='结束日期(YYYY-MM-DD)')
    parser.add_argument('--period', default='6mo', help='区间简写（如 6mo, 1y, max）')

    # Operators
    parser.add_argument('--operators', help='逗号分隔的算子列表（默认从配置读取）')

    # 输出与日志
    parser.add_argument(
        '--output',
        help='输出 JSON 路径（默认 analysis_result/analysis_{ts}.json）',
    )
    parser.add_argument('--indent', type=int, default=2, help='JSON缩进（默认2）')
    parser.add_argument('-v', '--verbose', action='store_true', help='详细日志')

    return parser


def _load_symbols(args: argparse.Namespace) -> List[str]:
    symbols: List[str] = []
    if args.symbols:
        symbols.extend([s.strip().upper() for s in args.symbols if s.strip()])
    if args.symbols_file:
        for line in Path(args.symbols_file).read_text(encoding='utf-8').splitlines():
            s = line.strip().upper()
            if s:
                symbols.append(s)
    if not symbols:
        raise SystemExit('No symbols provided. Use --symbols or --symbols-file')
    return symbols


def _resolve_output_path(path: Optional[str]) -> Path:
    if path:
        out = Path(path)
    else:
        out_dir = Path('result')
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        out = out_dir / f'analysis_{ts}.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    return out


def cmd_analyze(args: argparse.Namespace) -> int:
    setup_logging('INFO' if args.verbose else 'WARNING')
    symbols = _load_symbols(args)
    start = args.start_date
    end = args.end_date

    enabled_ops = None
    if args.operators:
        enabled_ops = [s.strip() for s in args.operators.split(',') if s.strip()]
        logger.info(f"启用算子: {enabled_ops}")

    logger.info(
        f"开始分析 {len(symbols)} 个股票，db={args.db_path}，范围 {start or 'auto'} ~ {end or 'latest'}"
    )
    analyzer = AnalysisService(db_path=args.db_path, enabled_operators=enabled_ops)
    results = analyzer.run_analysis(symbols, period=args.period, start=start, end=end)

    out_path = _resolve_output_path(args.output)
    out_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=args.indent),
        encoding='utf-8',
    )
    logger.info(f"✅ 分析结果已保存: {out_path}")
    return 0


def main() -> int:
    parser = build_parser()
    parser.set_defaults(func=cmd_analyze)
    args = parser.parse_args()
    return args.func(args)


if __name__ == '__main__':
    raise SystemExit(main())
