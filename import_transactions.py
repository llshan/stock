#!/usr/bin/env python3
"""
导入transactions.txt文件中的交易数据
"""

import sys
import csv
import os
from datetime import datetime
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from stock_analysis.data.storage.sqlite_storage import SQLiteStorage
from stock_analysis.trading.services.lot_transaction_service import LotTransactionService
from stock_analysis.trading.config import DEFAULT_TRADING_CONFIG


def parse_date(date_str):
    """解析日期字符串，支持MM/DD/YYYY格式"""
    try:
        return datetime.strptime(date_str.strip(), "%m/%d/%Y").strftime("%Y-%m-%d")
    except ValueError:
        # 如果已经是YYYY-MM-DD格式，直接返回
        return date_str.strip()


def import_transactions_from_file(file_path: str, db_path: str = None):
    """从CSV文件导入交易数据"""
    
    print("🏦 初始化股票交易系统...")
    
    # 初始化存储和服务
    if db_path is None:
        db_path = "database/stock_data.db"
    
    # 确保数据库目录存在
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    storage = SQLiteStorage(db_path)
    service = LotTransactionService(storage, DEFAULT_TRADING_CONFIG)
    
    print(f"📁 读取交易文件: {file_path}")
    
    # 读取并导入交易数据
    imported_count = 0
    error_count = 0
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            # 使用csv.DictReader自动处理标题行
            reader = csv.DictReader(file, skipinitialspace=True)
            
            print(f"📋 检测到以下字段: {list(reader.fieldnames)}")
            
            for i, row in enumerate(reader, 1):
                try:
                    # 提取数据（去除空格）
                    symbol = row['symbol'].strip().upper()
                    action = row['action'].strip().lower()
                    date = parse_date(row['date'])
                    unit_cost = float(row['unit_cost'].strip())
                    quantity = int(row['quantity'].strip())
                    platform = row.get('platform', '').strip()
                    
                    # 生成external_id用于去重
                    external_id = f"{platform}_{symbol}_{action}_{date}_{i}"
                    
                    print(f"\n📈 第{i}行: {action.upper()} {quantity} {symbol} @ ${unit_cost} ({date}) [{platform}]")
                    
                    if action == 'buy':
                        transaction = service.record_buy_transaction(
                            symbol=symbol,
                            quantity=quantity,
                            price=unit_cost,
                            transaction_date=date,
                            platform=platform,
                            external_id=external_id,
                            notes=f"从{file_path}导入"
                        )
                        print(f"✅ 买入记录成功: ID={transaction.id}")
                        
                    elif action == 'sell':
                        transaction = service.record_sell_transaction(
                            symbol=symbol,
                            quantity=quantity,
                            price=unit_cost,
                            transaction_date=date,
                            cost_basis_method='FIFO',  # 默认使用FIFO
                            platform=platform,
                            external_id=external_id,
                            notes=f"从{file_path}导入"
                        )
                        print(f"✅ 卖出记录成功: ID={transaction.id}")
                        
                    else:
                        print(f"⚠️  未知操作类型: {action}")
                        error_count += 1
                        continue
                    
                    imported_count += 1
                    
                except Exception as e:
                    print(f"❌ 第{i}行导入失败: {e}")
                    print(f"   数据: {row}")
                    error_count += 1
                    continue
    
    except FileNotFoundError:
        print(f"❌ 文件未找到: {file_path}")
        return False
        
    except Exception as e:
        print(f"❌ 导入过程出错: {e}")
        return False
    
    finally:
        storage.close()
    
    # 输出导入结果
    print(f"\n{'='*60}")
    print(f"📊 导入完成!")
    print(f"✅ 成功导入: {imported_count} 条交易")
    print(f"❌ 失败: {error_count} 条")
    print(f"💾 数据库: {db_path}")
    print(f"{'='*60}")
    
    return imported_count > 0


def show_imported_summary(db_path: str = None):
    """显示导入后的数据汇总"""
    if db_path is None:
        db_path = "database/stock_data.db"
    
    storage = SQLiteStorage(db_path)
    service = LotTransactionService(storage, DEFAULT_TRADING_CONFIG)
    
    try:
        print(f"\n📋 当前持仓汇总:")
        print("-" * 40)
        
        # 获取所有活跃持仓
        active_symbols = service.get_active_symbols()
        if not active_symbols:
            print("📭 暂无活跃持仓")
            return
        
        total_value = 0
        for symbol in active_symbols:
            lots = service.get_position_lots(symbol)
            if lots:
                total_quantity = sum(lot.remaining_quantity for lot in lots)
                avg_cost = sum(lot.cost_basis * lot.remaining_quantity for lot in lots) / total_quantity
                cost_value = sum(lot.cost_basis * lot.remaining_quantity for lot in lots)
                
                # 按平台分组统计
                platform_summary = {}
                for lot in lots:
                    # 这里需要通过transaction_id查询平台信息，暂时跳过
                    platform = "unknown"  # 需要join查询transaction表获取platform
                    if platform not in platform_summary:
                        platform_summary[platform] = {'quantity': 0, 'cost': 0}
                    platform_summary[platform]['quantity'] += lot.remaining_quantity
                    platform_summary[platform]['cost'] += lot.cost_basis * lot.remaining_quantity
                
                print(f"{symbol}: {total_quantity:.4f}股, 平均成本${avg_cost:.4f}, 总成本${cost_value:.2f}")
                total_value += cost_value
        
        print(f"\n💰 总持仓成本价值: ${total_value:.2f}")
        
    finally:
        storage.close()


if __name__ == "__main__":
    # 默认文件路径
    transactions_file = "transactions.txt"
    db_file = "database/stock_data.db"
    
    # 命令行参数处理
    if len(sys.argv) > 1:
        transactions_file = sys.argv[1]
    if len(sys.argv) > 2:
        db_file = sys.argv[2]
    
    print(f"🚀 股票交易数据导入工具")
    print(f"📄 交易文件: {transactions_file}")
    print(f"💾 数据库: {db_file}")
    
    # 执行导入
    success = import_transactions_from_file(transactions_file, db_file)
    
    if success:
        # 显示导入后的汇总
        show_imported_summary(db_file)
        print(f"\n🎉 导入完成！可以使用以下命令查看数据:")
        print(f"   python -m stock_analysis.cli.trading_manager --help")
    else:
        print(f"\n💥 导入失败!")
        sys.exit(1)