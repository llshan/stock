#!/usr/bin/env python3
"""
Display formatted financial metrics from the normalized database structure
"""

import sqlite3
import sys
import os
from pathlib import Path

def format_currency(value):
    """Format currency values"""
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

def display_financial_summary(symbol: str, db_path: str = None):
    """Display comprehensive financial summary for a symbol"""
    
    # Set default database path relative to project root
    if db_path is None:
        # Find project root (where database directory is located)
        current_dir = Path(__file__).parent
        project_root = current_dir
        while project_root.parent != project_root:
            if (project_root / "database").exists():
                break
            project_root = project_root.parent
        db_path = str(project_root / "database" / "stock_data.db")
    
    conn = sqlite3.connect(db_path)
    
    print(f"\n📊 {symbol} 财务数据总览 (规范化数据库结构)")
    print("=" * 80)
    
    # Income Statement Summary
    print(f"\n💰 损益表 (Income Statement)")
    print("-" * 40)
    
    # Get available periods first
    cursor = conn.execute("""
        SELECT DISTINCT period FROM income_statement 
        WHERE symbol = ? 
        ORDER BY period DESC
        LIMIT 5
    """, (symbol,))
    
    periods = [row[0] for row in cursor.fetchall()]
    
    if periods:
        print(f"{'期间':<12} {'收入':<15} {'毛利润':<15} {'净利润':<15}")
        print("-" * 65)
        
        for period in periods:
            # Get key metrics for this period
            cursor = conn.execute("""
                SELECT metric_name, metric_value FROM income_statement 
                WHERE symbol = ? AND period = ?
            """, (symbol, period))
            
            metrics = dict(cursor.fetchall())
            revenue = metrics.get('Total net sales') or metrics.get('Revenue') or metrics.get('Net sales')
            gross_profit = metrics.get('Gross margin') or metrics.get('Gross profit')
            net_income = metrics.get('Net income')
            
            print(f"{period:<12} {format_currency(revenue):<15} {format_currency(gross_profit):<15} {format_currency(net_income):<15}")
    else:
        print(f"未找到 {symbol} 的损益表数据")
    
    # Balance Sheet Summary
    print(f"\n🏦 资产负债表 (Balance Sheet)")
    print("-" * 40)
    
    # Get available periods for balance sheet
    cursor = conn.execute("""
        SELECT DISTINCT period FROM balance_sheet 
        WHERE symbol = ? 
        ORDER BY period DESC
        LIMIT 5
    """, (symbol,))
    
    periods = [row[0] for row in cursor.fetchall()]
    
    if periods:
        print(f"{'期间':<12} {'总资产':<15} {'流动资产':<15} {'股东权益':<15}")
        print("-" * 65)
        
        for period in periods:
            # Get key metrics for this period
            cursor = conn.execute("""
                SELECT metric_name, metric_value FROM balance_sheet 
                WHERE symbol = ? AND period = ?
            """, (symbol, period))
            
            metrics = dict(cursor.fetchall())
            total_assets = metrics.get('Total assets') or metrics.get('Assets')
            current_assets = metrics.get('Current assets') or metrics.get('Total current assets')
            # Find equity value by searching through keys
            shareholders_equity = None
            for key in metrics:
                if 'Total shareholders' in key and 'liabilities' not in key:
                    shareholders_equity = metrics[key]
                    break
            
            print(f"{period:<12} {format_currency(total_assets):<15} {format_currency(current_assets):<15} {format_currency(shareholders_equity):<15}")
    else:
        print(f"未找到 {symbol} 的资产负债表数据")
    
    # Cash Flow Summary
    print(f"\n💸 现金流量表 (Cash Flow)")
    print("-" * 40)
    
    # Get available periods for cash flow
    cursor = conn.execute("""
        SELECT DISTINCT period FROM cash_flow 
        WHERE symbol = ? 
        ORDER BY period DESC
        LIMIT 5
    """, (symbol,))
    
    periods = [row[0] for row in cursor.fetchall()]
    
    if periods:
        print(f"{'期间':<12} {'经营现金流':<15} {'投资现金流':<15} {'筹资现金流':<15}")
        print("-" * 65)
        
        for period in periods:
            # Get key metrics for this period
            cursor = conn.execute("""
                SELECT metric_name, metric_value FROM cash_flow 
                WHERE symbol = ? AND period = ?
            """, (symbol, period))
            
            metrics = dict(cursor.fetchall())
            operating_cf = metrics.get('Cash generated by operating activities') or metrics.get('Operating cash flow')
            investing_cf = metrics.get('Cash generated by/(used in) investing activities') or metrics.get('Investing cash flow')
            financing_cf = metrics.get('Cash used in financing activities') or metrics.get('Financing cash flow')
            
            print(f"{period:<12} {format_currency(operating_cf):<15} {format_currency(investing_cf):<15} {format_currency(financing_cf):<15}")
    else:
        print(f"未找到 {symbol} 的现金流量表数据")
    
    # Database stats
    print(f"\n📊 数据统计")
    print("-" * 40)
    
    # Count metrics from each table
    cursor = conn.execute("SELECT COUNT(*) FROM income_statement WHERE symbol = ?", (symbol,))
    income_count = cursor.fetchone()[0]
    
    cursor = conn.execute("SELECT COUNT(*) FROM balance_sheet WHERE symbol = ?", (symbol,))
    balance_count = cursor.fetchone()[0]
    
    cursor = conn.execute("SELECT COUNT(*) FROM cash_flow WHERE symbol = ?", (symbol,))
    cash_flow_count = cursor.fetchone()[0]
    
    total_metrics = income_count + balance_count + cash_flow_count
    
    print(f"总计指标数量: {total_metrics}")
    print(f"损益表指标: {income_count}")
    print(f"资产负债表指标: {balance_count}")  
    print(f"现金流量表指标: {cash_flow_count}")
    
    conn.close()


def display_detailed_metrics(symbol: str, db_path: str = None, type: str = None, period: str = None, limit: int = None):
    """Display detailed financial metrics"""
    if db_path is None:
        current_dir = Path(__file__).parent
        project_root = current_dir
        while project_root.parent != project_root:
            if (project_root / "database").exists():
                break
            project_root = project_root.parent
        db_path = str(project_root / "database" / "stock_data.db")
    
    conn = sqlite3.connect(db_path)
    
    print(f"\n📋 {symbol} 详细财务指标")
    if type:
        print(f"报表类型: {type}")
    if period:
        print(f"期间: {period}")
    print("-" * 80)
    
    # Determine table based on type
    if type == 'income_statement':
        table = 'income_statement'
    elif type == 'balance_sheet':
        table = 'balance_sheet'  
    elif type == 'cash_flow':
        table = 'cash_flow'
    else:
        # Show all tables
        for table in ['income_statement', 'balance_sheet', 'cash_flow']:
            print(f"\n{table.replace('_', ' ').title()}:")
            print("-" * 40)
            
            sql = f"SELECT period, metric_name, metric_value FROM {table} WHERE symbol = ?"
            params = [symbol]
            if period:
                sql += " AND period = ?"
                params.append(period)
            sql += " ORDER BY period DESC, metric_name"
            if limit:
                sql += f" LIMIT {limit}"
            
            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()
            
            if rows:
                for p, name, value in rows:
                    print(f"{p:<12} {name:<40} {format_currency(value):<15}")
            else:
                print(f"未找到数据")
        conn.close()
        return
    
    # Single table query
    sql = f"SELECT period, metric_name, metric_value FROM {table} WHERE symbol = ?"
    params = [symbol]
    if period:
        sql += " AND period = ?"
        params.append(period)
    sql += " ORDER BY period DESC, metric_name"
    if limit:
        sql += f" LIMIT {limit}"
        
    cursor = conn.execute(sql, params)
    rows = cursor.fetchall()
    
    if rows:
        for p, name, value in rows:
            print(f"{p:<12} {name:<40} {format_currency(value):<15}")
    else:
        print(f"未找到数据")
    
    conn.close()


def display_compare(symbols: list, db_path: str = None):
    """Compare multiple stocks"""
    if db_path is None:
        current_dir = Path(__file__).parent
        project_root = current_dir
        while project_root.parent != project_root:
            if (project_root / "database").exists():
                break
            project_root = project_root.parent
        db_path = str(project_root / "database" / "stock_data.db")
    
    conn = sqlite3.connect(db_path)
    
    print(f"\n📊 财务指标对比: {', '.join(symbols)}")
    print("=" * 80)
    
    # Compare latest year key metrics
    print(f"{'股票':<8} {'期间':<12} {'收入':<15} {'净利润':<15} {'总资产':<15}")
    print("-" * 80)
    
    for symbol in symbols:
        # Get latest period from income statement
        cursor = conn.execute("""
            SELECT period FROM income_statement 
            WHERE symbol = ? 
            ORDER BY period DESC 
            LIMIT 1
        """, (symbol,))
        latest_period_row = cursor.fetchone()
        
        if not latest_period_row:
            print(f"{symbol:<8} {'无数据':<12} {'N/A':<15} {'N/A':<15} {'N/A':<15}")
            continue
            
        latest_period = latest_period_row[0]
        
        # Get key metrics for this period
        cursor = conn.execute("""
            SELECT metric_name, metric_value FROM income_statement 
            WHERE symbol = ? AND period = ?
        """, (symbol, latest_period))
        income_metrics = dict(cursor.fetchall())
        
        cursor = conn.execute("""
            SELECT metric_name, metric_value FROM balance_sheet 
            WHERE symbol = ? AND period = ?
        """, (symbol, latest_period))
        balance_metrics = dict(cursor.fetchall())
        
        revenue = income_metrics.get('Total net sales') or income_metrics.get('Revenue') or income_metrics.get('Net sales')
        net_income = income_metrics.get('Net income')
        total_assets = balance_metrics.get('Total assets') or balance_metrics.get('Assets')
        
        print(f"{symbol:<8} {latest_period:<12} {format_currency(revenue):<15} {format_currency(net_income):<15} {format_currency(total_assets):<15}")
    
    conn.close()


def display_metric_trend(symbol: str, metric_name: str, db_path: str = None):
    """Display trend for a specific metric"""
    if db_path is None:
        current_dir = Path(__file__).parent
        project_root = current_dir
        while project_root.parent != project_root:
            if (project_root / "database").exists():
                break
            project_root = project_root.parent
        db_path = str(project_root / "database" / "stock_data.db")
    
    conn = sqlite3.connect(db_path)
    
    print(f"\n📈 {symbol} - {metric_name} 趋势分析")
    print("-" * 80)
    
    # Search across all tables for the metric
    found_data = False
    for table in ['income_statement', 'balance_sheet', 'cash_flow']:
        cursor = conn.execute(f"""
            SELECT period, metric_value FROM {table}
            WHERE symbol = ? AND metric_name = ?
            ORDER BY period DESC
        """, (symbol, metric_name))
        
        rows = cursor.fetchall()
        if rows:
            found_data = True
            print(f"\n来源表: {table.replace('_', ' ').title()}")
            print(f"{'期间':<12} {'数值':<15} {'变化':<15}")
            print("-" * 45)
            
            prev_value = None
            for period, value in rows:
                change = ""
                if prev_value is not None and prev_value != 0:
                    change_pct = ((value - prev_value) / prev_value) * 100
                    change = f"{change_pct:+.1f}%"
                
                print(f"{period:<12} {format_currency(value):<15} {change:<15}")
                prev_value = value
            break
    
    if not found_data:
        print(f"未找到指标 '{metric_name}' 的数据")
        print("\n建议使用 financial-metrics metrics 查看可用的指标名称")
    
    conn.close()


if __name__ == "__main__":
    symbol = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    display_financial_summary(symbol)