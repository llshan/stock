#!/usr/bin/env python3
"""
展示股票数据下载示例
"""

import json
from datetime import datetime, timedelta
import random

def create_sample_stock_data():
    """创建示例股票价格数据"""
    # 生成2020年以来的示例数据
    start_date = datetime(2020, 1, 1)
    end_date = datetime.now()
    
    dates = []
    prices = []
    base_price = 150.0
    
    current_date = start_date
    current_price = base_price
    
    while current_date <= end_date:
        # 跳过周末
        if current_date.weekday() < 5:
            dates.append(current_date.strftime('%Y-%m-%d'))
            
            # 模拟价格变动
            change = random.uniform(-0.05, 0.05)  # -5% to +5% daily change
            current_price *= (1 + change)
            
            # 生成OHLC数据
            high = current_price * random.uniform(1.00, 1.03)
            low = current_price * random.uniform(0.97, 1.00)
            open_price = current_price * random.uniform(0.98, 1.02)
            volume = random.randint(50000000, 200000000)
            
            prices.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'open': round(open_price, 2),
                'high': round(high, 2),
                'low': round(low, 2),
                'close': round(current_price, 2),
                'adj_close': round(current_price, 2),
                'volume': volume
            })
        
        current_date += timedelta(days=1)
    
    return prices[-10:]  # 返回最近10天数据作为示例

def create_sample_financial_data():
    """创建示例财务数据"""
    return {
        'company_name': 'Apple Inc.',
        'sector': 'Technology',
        'industry': 'Consumer Electronics',
        'market_cap': 3000000000000,
        'employees': 164000,
        'description': 'Apple Inc. designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories worldwide.',
        'financial_statements': {
            'income_statement': {
                'periods': ['2023-09-30', '2022-09-30', '2021-09-30', '2020-09-30'],
                'items': {
                    'Total Revenue': [383285000000, 365817000000, 294135000000, 260174000000],
                    'Gross Profit': [169148000000, 152836000000, 105126000000, 91926000000],
                    'Operating Income': [114301000000, 93055000000, 70898000000, 56344000000],
                    'Net Income': [96995000000, 79344000000, 57411000000, 48351000000],
                    'Basic EPS': [6.16, 5.11, 3.71, 3.31],
                    'Diluted EPS': [6.13, 5.06, 3.68, 3.28]
                }
            },
            'balance_sheet': {
                'periods': ['2023-09-30', '2022-09-30', '2021-09-30', '2020-09-30'],
                'items': {
                    'Total Assets': [352583000000, 323888000000, 293531000000, 269502000000],
                    'Current Assets': [143566000000, 135405000000, 127877000000, 123266000000],
                    'Cash and Cash Equivalents': [29965000000, 23646000000, 17635000000, 25913000000],
                    'Total Liabilities': [290020000000, 270498000000, 244094000000, 222912000000],
                    'Current Liabilities': [145308000000, 124618000000, 115458000000, 105392000000],
                    'Total Stockholders Equity': [62563000000, 50672000000, 49437000000, 46590000000]
                }
            },
            'cash_flow': {
                'periods': ['2023-09-30', '2022-09-30', '2021-09-30', '2020-09-30'],
                'items': {
                    'Operating Cash Flow': [110563000000, 122151000000, 104038000000, 80674000000],
                    'Capital Expenditures': [-10959000000, -10708000000, -11085000000, -7309000000],
                    'Free Cash Flow': [99604000000, 111443000000, 92953000000, 73365000000],
                    'Financing Cash Flow': [-108488000000, -110749000000, -90215000000, -86820000000],
                    'Investing Cash Flow': [1337000000, -22354000000, -14545000000, 4289000000]
                }
            }
        }
    }

def show_data_examples():
    """展示下载数据的示例"""
    print("🚀 股票数据下载示例展示")
    print("=" * 60)
    print("📅 数据时间范围: 2020-01-01 至今")
    print("🎯 示例股票: AAPL (苹果公司)")
    print()
    
    # 1. 股票价格数据示例
    print("📈 1. 股票价格数据示例")
    print("-" * 30)
    
    sample_prices = create_sample_stock_data()
    print("最近10个交易日的价格数据:")
    print()
    print("日期        |  开盘价  |  最高价  |  最低价  |  收盘价  |    成交量")
    print("-" * 70)
    
    for price in sample_prices:
        print(f"{price['date']} | ${price['open']:>7.2f} | ${price['high']:>7.2f} | "
              f"${price['low']:>7.2f} | ${price['close']:>7.2f} | {price['volume']:>10,}")
    
    print()
    print("📊 数据统计信息:")
    print(f"  • 数据点总数: 约 1,250+ 个交易日 (2020年至今)")
    print(f"  • 包含字段: 开盘价、最高价、最低价、收盘价、调整收盘价、成交量")
    print(f"  • 最近收盘价: ${sample_prices[-1]['close']}")
    print(f"  • 最近成交量: {sample_prices[-1]['volume']:,}")
    
    print()
    print("=" * 60)
    
    # 2. 财务数据示例
    print("💼 2. 财务报表数据示例")
    print("-" * 30)
    
    financial_data = create_sample_financial_data()
    
    print("🏢 公司基本信息:")
    print(f"  • 公司名称: {financial_data['company_name']}")
    print(f"  • 行业分类: {financial_data['sector']} - {financial_data['industry']}")
    print(f"  • 市值: ${financial_data['market_cap']:,}")
    print(f"  • 员工人数: {financial_data['employees']:,}")
    
    print()
    print("📊 损益表数据 (最近4年):")
    income_statement = financial_data['financial_statements']['income_statement']
    periods = income_statement['periods']
    
    print("会计年度    |      营收         |     净利润        |   每股收益")
    print("-" * 65)
    
    revenues = income_statement['items']['Total Revenue']
    net_incomes = income_statement['items']['Net Income']
    eps_values = income_statement['items']['Diluted EPS']
    
    for i, period in enumerate(periods):
        print(f"{period} | ${revenues[i]/1e9:>10.1f}B | ${net_incomes[i]/1e9:>10.1f}B | ${eps_values[i]:>8.2f}")
    
    print()
    print("🏦 资产负债表数据 (最近年度):")
    balance_sheet = financial_data['financial_statements']['balance_sheet']
    latest_assets = balance_sheet['items']['Total Assets'][0]
    latest_liabilities = balance_sheet['items']['Total Liabilities'][0]
    latest_equity = balance_sheet['items']['Total Stockholders Equity'][0]
    
    print(f"  • 总资产: ${latest_assets/1e9:.1f}B")
    print(f"  • 总负债: ${latest_liabilities/1e9:.1f}B") 
    print(f"  • 股东权益: ${latest_equity/1e9:.1f}B")
    
    print()
    print("💰 现金流量表数据 (最近年度):")
    cash_flow = financial_data['financial_statements']['cash_flow']
    operating_cf = cash_flow['items']['Operating Cash Flow'][0]
    capex = cash_flow['items']['Capital Expenditures'][0]
    free_cf = cash_flow['items']['Free Cash Flow'][0]
    
    print(f"  • 经营现金流: ${operating_cf/1e9:.1f}B")
    print(f"  • 资本支出: ${capex/1e9:.1f}B")
    print(f"  • 自由现金流: ${free_cf/1e9:.1f}B")
    
    print()
    print("=" * 60)
    
    # 3. 数据库存储结构示例
    print("🗄️ 3. 数据库存储结构")
    print("-" * 25)
    
    print("数据库表结构:")
    print()
    
    print("📊 stocks (股票基本信息表)")
    print("  • symbol (股票代码) - 主键")
    print("  • company_name (公司名称)")
    print("  • sector (行业)")
    print("  • industry (细分行业)")
    print("  • market_cap (市值)")
    print("  • employees (员工数)")
    print("  • description (公司描述)")
    print()
    
    print("📈 stock_prices (股票价格表)")
    print("  • symbol (股票代码)")
    print("  • date (交易日期)")
    print("  • open_price (开盘价)")
    print("  • high_price (最高价)")
    print("  • low_price (最低价)")
    print("  • close_price (收盘价)")
    print("  • adj_close (调整收盘价)")
    print("  • volume (成交量)")
    print()
    
    print("💼 financial_statements (财务报表表)")
    print("  • symbol (股票代码)")
    print("  • statement_type (报表类型)")
    print("  • period_date (会计周期)")
    print("  • item_name (财务指标名称)")
    print("  • value (数值)")
    print()
    
    print("📊 data_quality (数据质量表)")
    print("  • symbol (股票代码)")
    print("  • quality_grade (质量等级: A-F)")
    print("  • data_completeness (完整性百分比)")
    print("  • stock_data_available (价格数据可用性)")
    print("  • financial_data_available (财务数据可用性)")
    
    print()
    print("=" * 60)
    
    # 4. 查询示例
    print("🔍 4. 数据查询示例")
    print("-" * 20)
    
    print("常用SQL查询示例:")
    print()
    
    print("📈 获取股票价格数据:")
    print("```sql")
    print("SELECT date, close_price, volume")
    print("FROM stock_prices") 
    print("WHERE symbol = 'AAPL'")
    print("  AND date >= '2023-01-01'")
    print("ORDER BY date DESC;")
    print("```")
    print()
    
    print("💼 获取财务数据:")
    print("```sql")
    print("SELECT period_date, item_name, value")
    print("FROM financial_statements")
    print("WHERE symbol = 'AAPL'")
    print("  AND statement_type = 'income_statement'")
    print("  AND item_name = 'Total Revenue'")
    print("ORDER BY period_date DESC;")
    print("```")
    print()
    
    print("📊 数据质量报告:")
    print("```sql")
    print("SELECT s.symbol, s.company_name,")
    print("       dq.quality_grade, dq.data_completeness")
    print("FROM stocks s")
    print("JOIN data_quality dq ON s.symbol = dq.symbol")
    print("ORDER BY dq.data_completeness DESC;")
    print("```")
    
    print()
    print("🎯 总结:")
    print("- 📈 完整的股票价格历史数据 (2020年至今)")
    print("- 💼 详细的财务报表数据 (损益表、资产负债表、现金流量表)")
    print("- 🗄️ 结构化数据库存储，支持复杂查询")
    print("- 📊 数据质量监控和评估")
    print("- ☁️ 支持本地SQLite和云端PostgreSQL")

if __name__ == "__main__":
    show_data_examples()