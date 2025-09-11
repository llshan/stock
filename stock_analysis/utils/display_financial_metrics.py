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
    
    cursor = conn.execute("""
        SELECT period, revenue, gross_profit, operating_income, net_income, eps_basic
        FROM income_statement_metrics 
        WHERE symbol = ? 
        ORDER BY period DESC
    """, (symbol,))
    
    rows = cursor.fetchall()
    if rows:
        print(f"{'期间':<12} {'收入':<12} {'毛利润':<12} {'营业利润':<12} {'净利润':<12} {'基本EPS':<8}")
        print("-" * 75)
        for period, revenue, gross_profit, operating_income, net_income, eps_basic in rows:
            print(f"{period:<12} {format_currency(revenue):<12} {format_currency(gross_profit):<12} "
                  f"{format_currency(operating_income):<12} {format_currency(net_income):<12} ${eps_basic:.2f}")
    
    # Balance Sheet Summary
    print(f"\n🏦 资产负债表 (Balance Sheet)")
    print("-" * 40)
    
    cursor = conn.execute("""
        SELECT period, total_assets, current_assets, cash, total_liabilities, shareholders_equity
        FROM balance_sheet_metrics 
        WHERE symbol = ? 
        ORDER BY period DESC
    """, (symbol,))
    
    rows = cursor.fetchall()
    if rows:
        print(f"{'期间':<12} {'总资产':<12} {'流动资产':<12} {'现金':<12} {'总负债':<12} {'股东权益':<12}")
        print("-" * 85)
        for period, total_assets, current_assets, cash, total_liabilities, shareholders_equity in rows:
            print(f"{period:<12} {format_currency(total_assets):<12} {format_currency(current_assets):<12} "
                  f"{format_currency(cash):<12} {format_currency(total_liabilities):<12} "
                  f"{format_currency(shareholders_equity):<12}")
    
    # Cash Flow Summary
    print(f"\n💸 现金流量表 (Cash Flow)")
    print("-" * 40)
    
    cursor = conn.execute("""
        SELECT period, operating_cash_flow, investing_cash_flow, financing_cash_flow, free_cash_flow
        FROM cash_flow_metrics 
        WHERE symbol = ? 
        ORDER BY period DESC
    """, (symbol,))
    
    rows = cursor.fetchall()
    if rows:
        print(f"{'期间':<12} {'经营现金流':<12} {'投资现金流':<12} {'筹资现金流':<12} {'自由现金流':<12}")
        print("-" * 75)
        for period, operating_cf, investing_cf, financing_cf, free_cf in rows:
            print(f"{period:<12} {format_currency(operating_cf):<12} {format_currency(investing_cf):<12} "
                  f"{format_currency(financing_cf):<12} {format_currency(free_cf):<12}")
    
    # Key Ratios and Trends
    print(f"\n📈 关键指标趋势")
    print("-" * 40)
    
    if len(rows) >= 2:
        # Get latest 2 years for trend analysis
        cursor = conn.execute("""
            SELECT 
                i.period,
                i.revenue,
                i.net_income,
                b.total_assets,
                b.shareholders_equity,
                c.free_cash_flow
            FROM income_statement_metrics i
            JOIN balance_sheet_metrics b ON i.symbol = b.symbol AND i.period = b.period
            JOIN cash_flow_metrics c ON i.symbol = c.symbol AND i.period = c.period
            WHERE i.symbol = ?
            ORDER BY i.period DESC
            LIMIT 2
        """, (symbol,))
        
        metrics = cursor.fetchall()
        if len(metrics) == 2:
            current, previous = metrics
            
            # Calculate changes
            revenue_change = ((current[1] - previous[1]) / previous[1] * 100) if previous[1] else 0
            profit_change = ((current[2] - previous[2]) / previous[2] * 100) if previous[2] else 0
            
            print(f"收入增长率: {revenue_change:+.1f}%")
            print(f"净利润增长率: {profit_change:+.1f}%")
            
            # ROE calculation
            if current[4]:  # shareholders_equity
                roe = (current[2] / current[4] * 100)
                print(f"净资产收益率 (ROE): {roe:.1f}%")
            
            # Asset turnover
            if current[3]:  # total_assets
                asset_turnover = current[1] / current[3]
                print(f"资产周转率: {asset_turnover:.2f}")
    
    # Database stats
    print(f"\n📊 数据统计")
    print("-" * 40)
    cursor = conn.execute("SELECT COUNT(*) FROM financial_metrics WHERE symbol = ?", (symbol,))
    total_metrics = cursor.fetchone()[0]
    
    cursor = conn.execute("""
        SELECT statement_type, COUNT(*) 
        FROM financial_metrics 
        WHERE symbol = ? 
        GROUP BY statement_type
    """, (symbol,))
    
    print(f"总计指标数量: {total_metrics}")
    for stmt_type, count in cursor.fetchall():
        print(f"{stmt_type}: {count} 个指标")
    
    conn.close()

if __name__ == "__main__":
    symbol = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    display_financial_summary(symbol)