#!/usr/bin/env python3
"""
批次追踪迁移脚本
从现有的交易记录生成批次级别的追踪数据

核心逻辑：
1. 扫描所有历史BUY交易，每笔创建一个PositionLot
2. 扫描所有历史SELL交易，按FIFO原则匹配批次，创建SaleAllocation记录
3. 验证迁移后的数据一致性
"""

import argparse
import logging
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from stock_analysis.data.storage import create_storage
from stock_analysis.data.storage.config import StorageConfig
from stock_analysis.data.storage.sqlite_schema import SQLiteSchemaManager


class LotTrackingMigrator:
    """批次追踪迁移器"""
    
    def __init__(self, db_path: str, dry_run: bool = False, skip_historical_sells: bool = False):
        self.db_path = db_path
        self.dry_run = dry_run
        self.skip_historical_sells = skip_historical_sells
        self.logger = logging.getLogger(__name__)
        self.storage = None
        self.config = StorageConfig()
        
        # 统计信息
        self.stats = {
            'buy_transactions': 0,
            'sell_transactions': 0,
            'lots_created': 0,
            'allocations_created': 0,
            'errors': []
        }
    
    def run_migration(self) -> bool:
        """执行迁移"""
        try:
            self.logger.info(f"🔄 开始批次追踪迁移 (db: {self.db_path}, dry_run: {self.dry_run})")
            
            # 创建存储连接
            self.storage = create_storage("sqlite", db_path=self.db_path)
            
            # 检查前置条件
            if not self._check_prerequisites():
                return False
            
            # 创建批次追踪表
            if not self.dry_run:
                self._ensure_lot_tracking_tables()
            
            # 获取所有交易记录
            transactions = self._get_all_transactions()
            self.logger.info(f"📊 发现 {len(transactions)} 条交易记录")
            
            # 按用户和股票分组处理
            user_symbol_txns = self._group_transactions_by_user_symbol(transactions)
            
            for (user_id, symbol), txns in user_symbol_txns.items():
                self.logger.info(f"📈 处理用户 {user_id} 的 {symbol} 交易")
                if not self._process_user_symbol_transactions(user_id, symbol, txns):
                    self.stats['errors'].append(f"处理 {user_id}/{symbol} 失败")
            
            # 验证迁移结果
            if not self.dry_run:
                self._validate_migration()
            
            self._print_summary()
            return len(self.stats['errors']) == 0
            
        except Exception as e:
            self.logger.error(f"❌ 迁移失败: {e}")
            return False
        
        finally:
            if self.storage:
                self.storage.close()
    
    def _check_prerequisites(self) -> bool:
        """检查迁移前置条件"""
        # 检查原始交易表是否存在
        if not self.storage.schema_manager.trading_tables_exist():
            self.logger.error("❌ 原始交易表不存在，无法迁移")
            return False
        
        # 检查是否已经迁移过
        if self.storage.schema_manager.lot_tracking_tables_exist():
            self.logger.warning("⚠️  批次追踪表已存在")
            
            # 检查是否有数据
            lot_count = self._count_existing_lots()
            if lot_count > 0:
                self.logger.error(f"❌ 已存在 {lot_count} 条批次记录，请先清理或使用强制模式")
                return False
        
        return True
    
    def _ensure_lot_tracking_tables(self):
        """确保批次追踪表存在"""
        self.logger.info("📋 创建批次追踪表...")
        self.storage.schema_manager.ensure_lot_tracking_tables()
    
    def _get_all_transactions(self) -> List[Dict]:
        """获取所有交易记录"""
        T = self.config.Tables.TRANSACTIONS
        F = self.config.Fields
        
        sql = f"""
            SELECT * FROM {T} 
            ORDER BY {F.Transactions.USER_ID}, {F.SYMBOL}, 
                     {F.Transactions.TRANSACTION_DATE}, {F.Transactions.ID}
        """
        
        self.storage.cursor.execute(sql)
        rows = self.storage.cursor.fetchall()
        
        columns = [description[0] for description in self.storage.cursor.description]
        return [dict(zip(columns, row)) for row in rows]
    
    def _group_transactions_by_user_symbol(self, transactions: List[Dict]) -> Dict[Tuple[str, str], List[Dict]]:
        """按用户和股票分组交易记录"""
        groups = {}
        for txn in transactions:
            key = (txn['user_id'], txn['symbol'])
            if key not in groups:
                groups[key] = []
            groups[key].append(txn)
        return groups
    
    def _process_user_symbol_transactions(self, user_id: str, symbol: str, transactions: List[Dict]) -> bool:
        """处理单个用户单只股票的所有交易"""
        try:
            # 分离买入和卖出交易
            buy_txns = [txn for txn in transactions if txn['transaction_type'] == 'BUY']
            sell_txns = [txn for txn in transactions if txn['transaction_type'] == 'SELL']
            
            self.stats['buy_transactions'] += len(buy_txns)
            
            if self.skip_historical_sells:
                self.logger.info(f"  💰 {len(buy_txns)} 笔买入，{len(sell_txns)} 笔卖出（跳过历史卖出）")
                # 仅统计，不处理历史卖出交易
                self.stats['sell_transactions'] += len(sell_txns)
            else:
                self.stats['sell_transactions'] += len(sell_txns)
                self.logger.info(f"  💰 {len(buy_txns)} 笔买入，{len(sell_txns)} 笔卖出")
            
            # 1. 处理所有买入交易，创建批次
            lots = []
            for buy_txn in buy_txns:
                lot = self._create_lot_from_buy_transaction(buy_txn)
                if lot:
                    lots.append(lot)
            
            # 2. 处理历史卖出交易（可选）
            if not self.skip_historical_sells:
                # 按FIFO匹配批次处理历史卖出
                for sell_txn in sell_txns:
                    if not self._process_sell_transaction(sell_txn, lots):
                        self.logger.warning(f"⚠️  卖出交易 {sell_txn['id']} 处理失败")
                        return False
            else:
                self.logger.info(f"  ⏭️  跳过 {len(sell_txns)} 笔历史卖出交易的批次分配")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 处理 {user_id}/{symbol} 时出错: {e}")
            return False
    
    def _create_lot_from_buy_transaction(self, buy_txn: Dict) -> Dict:
        """从买入交易创建批次记录"""
        try:
            # 计算成本基础（含佣金分摊）
            total_cost = buy_txn['quantity'] * buy_txn['price'] + buy_txn['commission']
            cost_basis = total_cost / buy_txn['quantity']
            
            lot_data = {
                'user_id': buy_txn['user_id'],
                'symbol': buy_txn['symbol'],
                'transaction_id': buy_txn['id'],
                'original_quantity': buy_txn['quantity'],
                'remaining_quantity': buy_txn['quantity'],  # 初始时剩余=原始
                'cost_basis': cost_basis,
                'purchase_date': buy_txn['transaction_date'],
                'is_closed': False
            }
            
            if not self.dry_run:
                lot_id = self.storage.create_position_lot(lot_data)
                lot_data['id'] = lot_id
                self.stats['lots_created'] += 1
            else:
                lot_data['id'] = f"dry_run_{len(self.stats)} "  # 模拟ID
                self.stats['lots_created'] += 1
            
            self.logger.debug(f"    📦 创建批次: {lot_data['id']} ({lot_data['original_quantity']}@{lot_data['cost_basis']:.4f})")
            return lot_data
            
        except Exception as e:
            self.logger.error(f"❌ 创建批次失败: {e}")
            return None
    
    def _process_sell_transaction(self, sell_txn: Dict, lots: List[Dict]) -> bool:
        """处理卖出交易，按FIFO匹配批次"""
        try:
            remaining_to_sell = sell_txn['quantity']
            
            # 按购买日期和ID排序（FIFO）
            available_lots = sorted(
                [lot for lot in lots if lot['remaining_quantity'] > 0],
                key=lambda x: (x['purchase_date'], x.get('id', 0))
            )
            
            # 分配卖出数量到各批次
            allocations = []
            total_sale_amount = sell_txn['quantity'] * sell_txn['price']
            
            for lot in available_lots:
                if remaining_to_sell <= 0:
                    break
                
                # 计算从此批次卖出的数量
                quantity_from_lot = min(remaining_to_sell, lot['remaining_quantity'])
                
                # 计算佣金分摊（按销售金额比例）
                allocation_sale_amount = quantity_from_lot * sell_txn['price']
                commission_allocated = (allocation_sale_amount / total_sale_amount) * sell_txn['commission']
                
                # 计算已实现盈亏
                gross_pnl = (sell_txn['price'] - lot['cost_basis']) * quantity_from_lot
                
                # 创建分配记录
                allocation_data = {
                    'sale_transaction_id': sell_txn['id'],
                    'lot_id': lot['id'],
                    'quantity_sold': quantity_from_lot,
                    'cost_basis': lot['cost_basis'],
                    'sale_price': sell_txn['price'],
                    'realized_pnl': gross_pnl,
                    'commission_allocated': commission_allocated
                }
                
                if not self.dry_run:
                    allocation_id = self.storage.create_sale_allocation(allocation_data)
                    self.stats['allocations_created'] += 1
                    
                    # 更新批次剩余数量
                    new_remaining = lot['remaining_quantity'] - quantity_from_lot
                    is_closed = new_remaining <= 0.0001
                    self.storage.update_lot_remaining_quantity(lot['id'], new_remaining, is_closed)
                    
                    # 更新本地批次数据
                    lot['remaining_quantity'] = new_remaining
                    lot['is_closed'] = is_closed
                else:
                    self.stats['allocations_created'] += 1
                    # 模拟更新
                    lot['remaining_quantity'] -= quantity_from_lot
                
                allocations.append(allocation_data)
                remaining_to_sell -= quantity_from_lot
                
                self.logger.debug(f"    🔄 分配: 批次{lot['id']} 卖出{quantity_from_lot}, 盈亏{gross_pnl:.2f}")
            
            # 验证是否完全分配
            if remaining_to_sell > 0.0001:
                self.logger.error(f"❌ 卖出交易 {sell_txn['id']} 无法完全匹配: 剩余 {remaining_to_sell}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 处理卖出交易 {sell_txn['id']} 失败: {e}")
            return False
    
    def _count_existing_lots(self) -> int:
        """统计现有批次数量"""
        try:
            T = self.config.Tables.POSITION_LOTS
            sql = f"SELECT COUNT(*) FROM {T}"
            self.storage.cursor.execute(sql)
            return self.storage.cursor.fetchone()[0]
        except:
            return 0
    
    def _validate_migration(self) -> bool:
        """验证迁移结果"""
        self.logger.info("🔍 验证迁移结果...")
        
        # TODO: 添加验证逻辑
        # 1. 验证批次总成本 = 买入交易总成本
        # 2. 验证已实现盈亏 = 卖出交易计算盈亏
        # 3. 验证批次剩余数量 = 当前持仓数量
        
        return True
    
    def _print_summary(self):
        """打印迁移摘要"""
        self.logger.info("\n" + "="*50)
        self.logger.info("📊 迁移摘要")
        self.logger.info("="*50)
        self.logger.info(f"模式: {'DRY RUN' if self.dry_run else 'ACTUAL RUN'}")
        self.logger.info(f"买入交易: {self.stats['buy_transactions']}")
        self.logger.info(f"卖出交易: {self.stats['sell_transactions']}")
        self.logger.info(f"创建批次: {self.stats['lots_created']}")
        self.logger.info(f"创建分配: {self.stats['allocations_created']}")
        
        if self.stats['errors']:
            self.logger.info(f"错误数量: {len(self.stats['errors'])}")
            for error in self.stats['errors']:
                self.logger.error(f"  - {error}")
        else:
            self.logger.info("✅ 无错误")
        
        self.logger.info("="*50)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="批次追踪迁移脚本")
    parser.add_argument("--db-path", default="database/stock_data.db", help="数据库路径")
    parser.add_argument("--dry-run", action="store_true", help="仅模拟，不实际修改数据")
    parser.add_argument("--skip-historical-sells", action="store_true", 
                       help="跳过历史卖出交易的批次分配，仅从买入创建批次")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    
    args = parser.parse_args()
    
    # 配置日志
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # 检查数据库文件
    if not Path(args.db_path).exists():
        print(f"❌ 数据库文件不存在: {args.db_path}")
        return 1
    
    # 执行迁移
    migrator = LotTrackingMigrator(args.db_path, args.dry_run, args.skip_historical_sells)
    success = migrator.run_migration()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())