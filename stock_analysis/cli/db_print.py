#!/usr/bin/env python3
"""
SQLite数据库查看工具 - Database Inspection Tool

功能 Features:
- 列出数据库中的所有表和视图
- 查看表结构和索引信息
- 执行SQL查询并以表格形式显示数据
- 支持条件过滤、排序、列选择等高级查询

用法示例 Usage Examples:

列出所有表 List All Tables:
  python stock_analysis/cli/db_print.py list

查看表结构 View Table Schema:
  python stock_analysis/cli/db_print.py schema -t stocks
  python stock_analysis/cli/db_print.py schema -t stock_prices

打印表数据 Print Table Data:
  python stock_analysis/cli/db_print.py print -t stocks

查看AAPL股票价格数据 View AAPL Price Data:
  python stock_analysis/cli/db_print.py print -t stock_prices --where "symbol='AAPL'" --limit 10

查看最近的股票数据 View Recent Stock Data:
  python stock_analysis/cli/db_print.py print -t stock_prices --order-by "date DESC" --limit 20

选择特定列 Select Specific Columns:
  python stock_analysis/cli/db_print.py print -t stock_prices --columns symbol,date,close --limit 10

查看财务数据 View Financial Data:
  python stock_analysis/cli/db_print.py print -t income_statement --where "symbol='AAPL'"

复杂查询 Complex Query:
  python stock_analysis/cli/db_print.py print -t stock_prices \\
    --where "symbol='AAPL' AND date >= '2024-01-01'" \\
    --columns symbol,date,open,high,low,close,volume \\
    --order-by "date DESC" \\
    --limit 50

自定义数据库路径 Custom Database Path:
  python stock_analysis/cli/db_print.py list --db-path /path/to/your/database.db

支持的表 Available Tables:
- stocks: 股票基本信息
- stock_prices: 股票价格数据  
- income_statement: 损益表
- balance_sheet: 资产负债表
- cash_flow: 现金流量表
- download_logs: 下载日志

常用查询示例 Common Queries:
- 查看所有股票列表: print -t stocks
- 最新股价: print -t stock_prices --order-by "date DESC" --limit 20
- 特定股票财务: print -t income_statement --where "symbol='AAPL'"
- 下载历史: print -t download_logs --order-by "download_time DESC" --limit 10
"""

import argparse
import logging
import sqlite3
from pathlib import Path

import pandas as pd

from stock_analysis.utils.logging_utils import setup_logging


def get_conn(db_path: str) -> sqlite3.Connection:
    # 统一用 Path 处理路径
    conn = sqlite3.connect(str(Path(db_path)))
    conn.row_factory = sqlite3.Row
    return conn


def cmd_list(args: argparse.Namespace) -> int:
    setup_logging('INFO' if args.verbose else 'WARNING')
    conn = get_conn(args.db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    rows = [r[0] for r in cur.fetchall()]
    print("\nTables:")
    for name in rows:
        print(f" - {name}")
    conn.close()
    return 0


def cmd_schema(args: argparse.Namespace) -> int:
    setup_logging('INFO' if args.verbose else 'WARNING')
    if not args.table:
        logging.getLogger(__name__).error("请使用 -t/--table 指定表名")
        return 2
    conn = get_conn(args.db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(%s)" % args.table)
    cols = cur.fetchall()
    if not cols:
        print(f"表不存在或无列: {args.table}")
    else:
        print(f"\nSchema for {args.table}:")
        print("cid | name | type | notnull | dflt_value | pk")
        for c in cols:
            print(" | ".join(str(x) if x is not None else '' for x in c))
    conn.close()
    return 0


def cmd_print(args: argparse.Namespace) -> int:
    setup_logging('INFO' if args.verbose else 'WARNING')
    if not args.table:
        logging.getLogger(__name__).error("请使用 -t/--table 指定表名")
        return 2
    conn = get_conn(args.db_path)
    try:
        cols = "*"
        if args.columns:
            # 简单的列白名单拆分
            cols = ", ".join([c.strip() for c in args.columns.split(',') if c.strip()]) or '*'
        sql = f"SELECT {cols} FROM {args.table}"
        if args.where:
            sql += f" WHERE {args.where}"
        if args.order_by:
            order_expr = (
                " ".join(args.order_by) if isinstance(args.order_by, list) else str(args.order_by)
            )
            sql += f" ORDER BY {order_expr}"
        if args.limit:
            sql += f" LIMIT {int(args.limit)}"

        df = pd.read_sql_query(sql, conn)
        if df.empty:
            print("(no rows)")
        else:
            try:
                pd.set_option('display.width', 140)
                pd.set_option('display.max_columns', 50)
            except Exception:
                pass
            print(df)
        return 0
    except Exception as e:
        logging.getLogger(__name__).error(f"查询失败: {e}")
        return 1
    finally:
        conn.close()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description='SQLite 数据库查看工具')
    sub = p.add_subparsers(dest='command', required=True)

    sp = sub.add_parser('list', help='列出所有表')
    sp.add_argument('--db-path', default='database/stock_data.db', help='数据库路径')
    sp.add_argument('-v', '--verbose', action='store_true', help='详细日志')
    sp.set_defaults(func=cmd_list)

    ss = sub.add_parser('schema', help='查看表结构')
    ss.add_argument('-t', '--table', required=True, help='表名')
    ss.add_argument('--db-path', default='database/stock_data.db', help='数据库路径')
    ss.add_argument('-v', '--verbose', action='store_true', help='详细日志')
    ss.set_defaults(func=cmd_schema)

    pr = sub.add_parser('print', help='打印表数据')
    pr.add_argument('-t', '--table', required=True, help='表名')
    pr.add_argument('--columns', help='列名（逗号分隔），默认*')
    pr.add_argument('--where', help='原生 WHERE 条件（不包含 WHERE 关键字）')
    pr.add_argument('--order-by', nargs='+', help='排序条件（如 date DESC）')
    pr.add_argument('--limit', type=int, default=20, help='输出行数上限（默认20）')
    pr.add_argument('--db-path', default='database/stock_data.db', help='数据库路径')
    pr.add_argument('-v', '--verbose', action='store_true', help='详细日志')
    pr.set_defaults(func=cmd_print)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == '__main__':
    raise SystemExit(main())
