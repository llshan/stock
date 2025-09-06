#!/usr/bin/env python3
"""
验证Stooq数据的时间范围
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from analyzer.database import StockDatabase

def verify_data_range(db_path: str):
    """验证数据库中数据的时间范围"""
    print(f"🔍 验证数据库: {db_path}")
    print("=" * 50)
    
    database = StockDatabase(db_path)
    
    try:
        # 获取所有股票
        symbols = database.get_existing_symbols()
        
        print(f"📈 数据库中共有 {len(symbols)} 个股票\n")
        
        for symbol in symbols:
            # 获取股票价格数据
            price_data = database.get_stock_prices(symbol)
            
            if len(price_data) > 0:
                earliest_date = price_data['date'].min()
                latest_date = price_data['date'].max()
                total_records = len(price_data)
                
                # 获取一些样本价格
                first_price = price_data.iloc[0]['close_price']
                last_price = price_data.iloc[-1]['close_price']
                
                print(f"📊 {symbol}:")
                print(f"   时间范围: {earliest_date} 到 {latest_date}")
                print(f"   总记录数: {total_records} 个交易日")
                print(f"   首日价格: ${first_price:.2f}")
                print(f"   最新价格: ${last_price:.2f}")
                print(f"   涨幅: {((last_price - first_price) / first_price * 100):+.1f}%")
                print()
            else:
                print(f"❌ {symbol}: 无价格数据")
        
    except Exception as e:
        print(f"❌ 验证失败: {str(e)}")
    
    finally:
        database.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = "aapl_full_2020.db"
    
    verify_data_range(db_path)