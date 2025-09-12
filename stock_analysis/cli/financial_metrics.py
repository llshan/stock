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
  python stock_analysis/cli/financial_metrics.py summary AAPL
  python stock_analysis/cli/financial_metrics.py summary MRK

查看损益表指标 Income Statement Metrics:
  python stock_analysis/cli/financial_metrics.py metrics AAPL --type income_statement

查看资产负债表 Balance Sheet Metrics:
  python stock_analysis/cli/financial_metrics.py metrics AAPL --type balance_sheet

查看现金流量表 Cash Flow Metrics:
  python stock_analysis/cli/financial_metrics.py metrics AAPL --type cash_flow

指定时间期间 Specific Period:
  python stock_analysis/cli/financial_metrics.py metrics AAPL --period 2024-12-31

多股票对比 Compare Multiple Stocks:
  python stock_analysis/cli/financial_metrics.py compare AAPL MSFT GOOG
  python stock_analysis/cli/financial_metrics.py compare AAPL MSFT --type income_statement

趋势分析 Trend Analysis:
  python stock_analysis/cli/financial_metrics.py trend AAPL "Net income"
  python stock_analysis/cli/financial_metrics.py trend AAPL "Total assets"

查看所有可用指标 List Available Metrics:
  python stock_analysis/cli/financial_metrics.py list-metrics AAPL

自定义数据库路径 Custom Database Path:
  python stock_analysis/cli/financial_metrics.py summary AAPL --db-path /path/to/database.db

详细输出模式 Verbose Mode:
  python stock_analysis/cli/financial_metrics.py summary AAPL -v

支持的报表类型 Supported Statement Types:
- income_statement: 损益表 (收入、成本、利润等)
- balance_sheet: 资产负债表 (资产、负债、股东权益)  
- cash_flow: 现金流量表 (经营、投资、筹资现金流)

常用财务指标 Common Financial Metrics:
- 净销售额 (Net sales)
- 净利润 (Net income)  
- 总资产 (Total assets)
- 现金及等价物 (Cash and cash equivalents)
- 股东权益 (Shareholders' equity)
- 经营现金流 (Operating cash flow)

数据格式 Data Format:
- 金额自动格式化为 B(十亿)、M(百万)、K(千) 单位
- 日期按照 YYYY-MM-DD 格式显示
- 支持多年度数据对比和趋势分析
"""

import argparse
import logging
import sqlite3
from pathlib import Path
from typing import List, Optional
import sys

import pandas as pd

from stock_analysis.utils.logging_utils import setup_logging
from stock_analysis.utils.display_financial_metrics import display_financial_summary


def get_conn(db_path: str) -> sqlite3.Connection:
    """获取数据库连接"""
    conn = sqlite3.connect(str(Path(db_path)))
    conn.row_factory = sqlite3.Row
    return conn


def format_currency(value):
    """格式化货币值"""
    if value is None:
        return "N/A"
    
    abs_value = abs(value)
    if abs_value >= 1e12:
        return f"${value/1e12:.2f}T"
    elif abs_value >= 1e9:
        return f"${value/1e9:.2f}B"
    elif abs_value >= 1e6:
        return f"${value/1e6:.2f}M"
    elif abs_value >= 1e3:
        return f"${value/1e3:.2f}K"
    else:
        return f"${value:.2f}"


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
    
    conn = get_conn(args.db_path)
    symbol = args.symbol.upper()
    
    try:
        # 根据报表类型选择对应的表
        if args.type == 'income_statement':
            table_name = 'income_statement'
        elif args.type == 'balance_sheet':
            table_name = 'balance_sheet'
        elif args.type == 'cash_flow':
            table_name = 'cash_flow'
        else:
            # 如果没指定类型，从所有表查询
            sql = """
            SELECT 'income_statement' as statement_type, period, metric_name, metric_value
            FROM income_statement WHERE symbol = ?
            UNION ALL
            SELECT 'balance_sheet' as statement_type, period, metric_name, metric_value
            FROM balance_sheet WHERE symbol = ?
            UNION ALL  
            SELECT 'cash_flow' as statement_type, period, metric_name, metric_value
            FROM cash_flow WHERE symbol = ?
            """
            params = [symbol, symbol, symbol]
            
            if args.period:
                sql = sql.replace("WHERE symbol = ?", "WHERE symbol = ? AND period = ?")
                params = [symbol, args.period, symbol, args.period, symbol, args.period]
                
            sql += " ORDER BY period DESC, statement_type, metric_name"
            
            if args.limit:
                sql += f" LIMIT {args.limit}"
                
            df = pd.read_sql_query(sql, conn, params=params)
            
            if df.empty:
                print(f"未找到符合条件的 {symbol} 财务指标数据")
                return 0
                
            # 格式化显示
            df['formatted_value'] = df['metric_value'].apply(format_currency)
            
            print(f"\\n📋 {symbol} 财务指标")
            if args.period:
                print(f"期间: {args.period}")
            print("-" * 80)
            
            print(df[['statement_type', 'period', 'metric_name', 'formatted_value']].to_string(index=False))
            return 0

        sql = f"""
            SELECT period, metric_name, metric_value
            FROM {table_name} 
            WHERE symbol = ?
        """
        params = [symbol]
        
        if args.period:
            sql += " AND period = ?"
            params.append(args.period)
            
        sql += " ORDER BY period DESC, metric_name"
        
        if args.limit:
            sql += f" LIMIT {args.limit}"
        
        df = pd.read_sql_query(sql, conn, params=params)
        
        if df.empty:
            print(f"未找到符合条件的 {symbol} 财务指标数据")
            return 0
            
        # 格式化显示
        df['formatted_value'] = df['metric_value'].apply(format_currency)
        
        print(f"\n📋 {symbol} 财务指标")
        if args.type:
            print(f"报表类型: {args.type}")
        if args.period:
            print(f"期间: {args.period}")
        print("-" * 80)
        
        print(df[['period', 'metric_name', 'formatted_value']].to_string(index=False))
        
        return 0
        
    except Exception as e:
        logging.getLogger(__name__).error(f"查询失败: {e}")
        return 1
    finally:
        conn.close()


def cmd_compare(args: argparse.Namespace) -> int:
    """比较多个股票的财务指标"""
    setup_logging('INFO' if args.verbose else 'WARNING')
    
    conn = get_conn(args.db_path)
    symbols = [s.upper() for s in args.symbols]
    
    try:
        print(f"\n📊 财务指标对比: {', '.join(symbols)}")
        print("=" * 80)
        
        # 比较最新年度的关键指标
        sql = """
            SELECT 
                i.symbol,
                i.period,
                i.revenue,
                i.net_income,
                i.eps_basic,
                b.total_assets,
                b.shareholders_equity,
                c.free_cash_flow
            FROM income_statement_metrics i
            JOIN balance_sheet_metrics b ON i.symbol = b.symbol AND i.period = b.period
            JOIN cash_flow_metrics c ON i.symbol = c.symbol AND i.period = c.period
            WHERE i.symbol IN ({})
            AND i.period = (
                SELECT MAX(period) FROM income_statement_metrics 
                WHERE symbol = i.symbol
            )
            ORDER BY i.symbol
        """.format(','.join('?' * len(symbols)))
        
        df = pd.read_sql_query(sql, conn, params=symbols)
        
        if df.empty:
            print("未找到可比较的数据")
            return 0
        
        # 格式化显示
        for col in ['revenue', 'net_income', 'total_assets', 'shareholders_equity', 'free_cash_flow']:
            df[col] = df[col].apply(format_currency)
        
        df['eps_basic'] = df['eps_basic'].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "N/A")
        
        print(df.to_string(index=False))
        
        return 0
        
    except Exception as e:
        logging.getLogger(__name__).error(f"对比失败: {e}")
        return 1
    finally:
        conn.close()


def cmd_trend(args: argparse.Namespace) -> int:
    """显示指标趋势"""
    setup_logging('INFO' if args.verbose else 'WARNING')
    
    conn = get_conn(args.db_path)
    symbol = args.symbol.upper()
    metric_name = args.metric_name
    
    try:
        # 从所有三个表中查找指标
        sql = """
        SELECT period, metric_value
        FROM income_statement
        WHERE symbol = ? AND metric_name = ?
        UNION ALL
        SELECT period, metric_value  
        FROM balance_sheet
        WHERE symbol = ? AND metric_name = ?
        UNION ALL
        SELECT period, metric_value
        FROM cash_flow 
        WHERE symbol = ? AND metric_name = ?
        ORDER BY period
        """
        df = pd.read_sql_query(sql, conn, params=(symbol, metric_name, symbol, metric_name, symbol, metric_name))
        
        if df.empty:
            print(f"未找到 {symbol} 的 {metric_name} 数据")
            return 0
            
        print(f"\n📈 {symbol} - {metric_name} 趋势")
        print("-" * 60)
        
        # 计算同比变化
        df['formatted_value'] = df['metric_value'].apply(format_currency)
        df['yoy_change'] = df['metric_value'].pct_change() * 100
        df['yoy_change'] = df['yoy_change'].apply(lambda x: f"{x:+.1f}%" if pd.notna(x) else "N/A")
        
        print(df[['period', 'formatted_value', 'yoy_change']].to_string(index=False))
        
        return 0
        
    except Exception as e:
        logging.getLogger(__name__).error(f"趋势查询失败: {e}")
        return 1
    finally:
        conn.close()


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
