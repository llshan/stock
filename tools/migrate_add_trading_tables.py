#!/usr/bin/env python3
"""
数据库迁移脚本：添加交易相关表
为现有数据库添加transactions、positions、daily_pnl表及相关索引
"""

import sys
import sqlite3
import argparse
import logging
from pathlib import Path

# 添加项目根目录到路径，以便导入模块
sys.path.append(str(Path(__file__).parent.parent))

from stock_analysis.data.storage.config import StorageConfig
from stock_analysis.utils.logging_utils import setup_logging


def check_trading_tables_exist(cursor: sqlite3.Cursor) -> dict:
    """检查交易相关表是否已存在"""
    trading_tables = StorageConfig.Tables.get_trading_tables()
    lot_tables = StorageConfig.Tables.get_lot_tracking_tables()
    all_tables = trading_tables + lot_tables
    
    existing_tables = {}
    
    for table in all_tables:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
        exists = cursor.fetchone() is not None
        existing_tables[table] = exists
    
    return existing_tables


def create_trading_table_definitions() -> list:
    """获取交易相关表的创建SQL"""
    T = StorageConfig.Tables
    F = StorageConfig.Fields
    
    return [
        f"""
        CREATE TABLE IF NOT EXISTS {T.TRANSACTIONS} (
            {F.Transactions.ID} INTEGER PRIMARY KEY AUTOINCREMENT,
            {F.Transactions.USER_ID} TEXT NOT NULL,
            {F.Transactions.EXTERNAL_ID} TEXT,
            {F.SYMBOL} TEXT NOT NULL,
            {F.Transactions.TRANSACTION_TYPE} TEXT NOT NULL CHECK ({F.Transactions.TRANSACTION_TYPE} IN ('BUY','SELL')),
            {F.Transactions.QUANTITY} REAL NOT NULL,
            {F.Transactions.PRICE} REAL NOT NULL,
            {F.Transactions.COMMISSION} REAL DEFAULT 0,
            {F.Transactions.TRANSACTION_DATE} TEXT NOT NULL,
            {F.Transactions.LOT_ID} INTEGER,
            {F.Transactions.NOTES} TEXT,
            {F.CREATED_AT} TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            {F.UPDATED_AT} TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY ({F.SYMBOL}) REFERENCES {T.STOCKS}({F.SYMBOL}) ON DELETE RESTRICT
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {T.POSITIONS} (
            {F.Positions.ID} INTEGER PRIMARY KEY AUTOINCREMENT,
            {F.Positions.USER_ID} TEXT NOT NULL,
            {F.SYMBOL} TEXT NOT NULL,
            {F.Positions.QUANTITY} REAL NOT NULL,
            {F.Positions.AVG_COST} REAL NOT NULL,
            {F.Positions.TOTAL_COST} REAL NOT NULL,
            {F.Positions.FIRST_BUY_DATE} TEXT,
            {F.Positions.LAST_TRANSACTION_DATE} TEXT,
            {F.Positions.IS_ACTIVE} INTEGER DEFAULT 1,
            {F.CREATED_AT} TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            {F.UPDATED_AT} TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE({F.Positions.USER_ID}, {F.SYMBOL})
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {T.DAILY_PNL} (
            {F.DailyPnL.ID} INTEGER PRIMARY KEY AUTOINCREMENT,
            {F.DailyPnL.USER_ID} TEXT NOT NULL,
            {F.SYMBOL} TEXT NOT NULL,
            {F.DailyPnL.VALUATION_DATE} TEXT NOT NULL,
            {F.DailyPnL.QUANTITY} REAL NOT NULL,
            {F.DailyPnL.AVG_COST} REAL NOT NULL,
            {F.DailyPnL.MARKET_PRICE} REAL NOT NULL,
            {F.DailyPnL.MARKET_VALUE} REAL NOT NULL,
            {F.DailyPnL.UNREALIZED_PNL} REAL NOT NULL,
            {F.DailyPnL.UNREALIZED_PNL_PCT} REAL NOT NULL,
            {F.DailyPnL.REALIZED_PNL} REAL DEFAULT 0,
            {F.DailyPnL.REALIZED_PNL_PCT} REAL DEFAULT 0,
            {F.DailyPnL.TOTAL_COST} REAL NOT NULL,
            {F.DailyPnL.PRICE_DATE} TEXT,
            {F.DailyPnL.IS_STALE_PRICE} INTEGER DEFAULT 0,
            {F.CREATED_AT} TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE({F.DailyPnL.USER_ID}, {F.SYMBOL}, {F.DailyPnL.VALUATION_DATE})
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {T.POSITION_LOTS} (
            {F.PositionLots.ID} INTEGER PRIMARY KEY AUTOINCREMENT,
            {F.PositionLots.USER_ID} TEXT NOT NULL,
            {F.SYMBOL} TEXT NOT NULL,
            {F.PositionLots.TRANSACTION_ID} INTEGER NOT NULL,
            {F.PositionLots.ORIGINAL_QUANTITY} REAL NOT NULL,
            {F.PositionLots.REMAINING_QUANTITY} REAL NOT NULL,
            {F.PositionLots.COST_BASIS} REAL NOT NULL,
            {F.PositionLots.PURCHASE_DATE} TEXT NOT NULL,
            {F.PositionLots.IS_CLOSED} INTEGER DEFAULT 0,
            {F.CREATED_AT} TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            {F.UPDATED_AT} TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY ({F.PositionLots.TRANSACTION_ID}) REFERENCES {T.TRANSACTIONS}({F.Transactions.ID}) ON DELETE RESTRICT,
            FOREIGN KEY ({F.SYMBOL}) REFERENCES {T.STOCKS}({F.SYMBOL}) ON DELETE RESTRICT
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {T.SALE_ALLOCATIONS} (
            {F.SaleAllocations.ID} INTEGER PRIMARY KEY AUTOINCREMENT,
            {F.SaleAllocations.SALE_TRANSACTION_ID} INTEGER NOT NULL,
            {F.SaleAllocations.LOT_ID} INTEGER NOT NULL,
            {F.SaleAllocations.QUANTITY_SOLD} REAL NOT NULL,
            {F.SaleAllocations.COST_BASIS} REAL NOT NULL,
            {F.SaleAllocations.SALE_PRICE} REAL NOT NULL,
            {F.SaleAllocations.REALIZED_PNL} REAL NOT NULL,
            {F.SaleAllocations.COMMISSION_ALLOCATED} REAL DEFAULT 0,
            {F.CREATED_AT} TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY ({F.SaleAllocations.SALE_TRANSACTION_ID}) REFERENCES {T.TRANSACTIONS}({F.Transactions.ID}) ON DELETE RESTRICT,
            FOREIGN KEY ({F.SaleAllocations.LOT_ID}) REFERENCES {T.POSITION_LOTS}({F.PositionLots.ID}) ON DELETE RESTRICT
        )
        """
    ]


def create_trading_indexes() -> list:
    """获取交易相关索引的创建SQL"""
    T = StorageConfig.Tables
    F = StorageConfig.Fields
    
    return [
        f"CREATE INDEX IF NOT EXISTS idx_{T.TRANSACTIONS}_user_date ON {T.TRANSACTIONS} ({F.Transactions.USER_ID}, {F.Transactions.TRANSACTION_DATE})",
        f"CREATE INDEX IF NOT EXISTS idx_{T.TRANSACTIONS}_user_symbol_date ON {T.TRANSACTIONS} ({F.Transactions.USER_ID}, {F.SYMBOL}, {F.Transactions.TRANSACTION_DATE})",
        f"CREATE UNIQUE INDEX IF NOT EXISTS ux_{T.TRANSACTIONS}_user_external ON {T.TRANSACTIONS} ({F.Transactions.USER_ID}, {F.Transactions.EXTERNAL_ID}) WHERE {F.Transactions.EXTERNAL_ID} IS NOT NULL",
        f"CREATE INDEX IF NOT EXISTS idx_{T.POSITIONS}_user ON {T.POSITIONS} ({F.Positions.USER_ID})",
        f"CREATE INDEX IF NOT EXISTS idx_{T.DAILY_PNL}_user_date ON {T.DAILY_PNL} ({F.DailyPnL.USER_ID}, {F.DailyPnL.VALUATION_DATE})",
        f"CREATE INDEX IF NOT EXISTS idx_{T.DAILY_PNL}_user_symbol ON {T.DAILY_PNL} ({F.DailyPnL.USER_ID}, {F.SYMBOL})",
        # 批次追踪索引
        f"CREATE INDEX IF NOT EXISTS idx_{T.POSITION_LOTS}_user_symbol ON {T.POSITION_LOTS} ({F.PositionLots.USER_ID}, {F.SYMBOL})",
        f"CREATE INDEX IF NOT EXISTS idx_{T.POSITION_LOTS}_user_symbol_date ON {T.POSITION_LOTS} ({F.PositionLots.USER_ID}, {F.SYMBOL}, {F.PositionLots.PURCHASE_DATE})",
        f"CREATE INDEX IF NOT EXISTS idx_{T.POSITION_LOTS}_transaction ON {T.POSITION_LOTS} ({F.PositionLots.TRANSACTION_ID})",
        f"CREATE INDEX IF NOT EXISTS idx_{T.POSITION_LOTS}_active ON {T.POSITION_LOTS} ({F.PositionLots.USER_ID}, {F.SYMBOL}, {F.PositionLots.IS_CLOSED})",
        f"CREATE INDEX IF NOT EXISTS idx_{T.SALE_ALLOCATIONS}_transaction ON {T.SALE_ALLOCATIONS} ({F.SaleAllocations.SALE_TRANSACTION_ID})",
        f"CREATE INDEX IF NOT EXISTS idx_{T.SALE_ALLOCATIONS}_lot ON {T.SALE_ALLOCATIONS} ({F.SaleAllocations.LOT_ID})",
    ]

def table_has_column(cursor: sqlite3.Cursor, table: str, column: str) -> bool:
    """检查指定表是否存在指定列"""
    cursor.execute(f"PRAGMA table_info({table})")
    cols = [row[1] for row in cursor.fetchall()]
    return column in cols

def ensure_daily_pnl_columns(conn: sqlite3.Connection, cursor: sqlite3.Cursor) -> None:
    """确保 daily_pnl 表包含新增列（price_date, is_stale_price）"""
    T = StorageConfig.Tables
    F = StorageConfig.Fields

    # 若表不存在，交由 create_trading_table_definitions 创建
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (T.DAILY_PNL,))
    if cursor.fetchone() is None:
        return

    # price_date 列
    if not table_has_column(cursor, T.DAILY_PNL, F.DailyPnL.PRICE_DATE):
        cursor.execute(f"ALTER TABLE {T.DAILY_PNL} ADD COLUMN {F.DailyPnL.PRICE_DATE} TEXT")

    # is_stale_price 列
    if not table_has_column(cursor, T.DAILY_PNL, F.DailyPnL.IS_STALE_PRICE):
        cursor.execute(
            f"ALTER TABLE {T.DAILY_PNL} ADD COLUMN {F.DailyPnL.IS_STALE_PRICE} INTEGER DEFAULT 0"
        )


def migrate_lots_from_history(conn: sqlite3.Connection, cursor: sqlite3.Cursor) -> None:
    """从历史BUY交易迁移数据到 position_lots 表"""
    logger = logging.getLogger(__name__)
    T = StorageConfig.Tables
    F = StorageConfig.Fields

    try:
        # 检查 position_lots 是否为空
        cursor.execute(f"SELECT COUNT(*) FROM {T.POSITION_LOTS}")
        if cursor.fetchone()[0] > 0:
            logger.info(f"✅ {T.POSITION_LOTS} 表已包含数据，跳过历史迁移")
            return

        logger.info(f"🚀 开始从历史BUY交易迁移到 {T.POSITION_LOTS}...")

        # 选择所有BUY交易
        buy_txns_sql = f"""
            SELECT
                {F.Transactions.ID},
                {F.Transactions.USER_ID},
                {F.SYMBOL},
                {F.Transactions.QUANTITY},
                {F.Transactions.PRICE},
                {F.Transactions.COMMISSION},
                {F.Transactions.TRANSACTION_DATE}
            FROM {T.TRANSACTIONS}
            WHERE {F.Transactions.TRANSACTION_TYPE} = 'BUY'
        """
        cursor.execute(buy_txns_sql)
        buy_transactions = cursor.fetchall()

        lots_to_insert = []
        for txn in buy_transactions:
            (
                txn_id,
                user_id,
                symbol,
                quantity,
                price,
                commission,
                purchase_date,
            ) = txn
            
            # 成本基础 = (价格 * 数量 + 佣金) / 数量
            cost_basis = (price * quantity + commission) / quantity if quantity > 0 else price

            lots_to_insert.append(
                (
                    user_id,
                    symbol,
                    txn_id,
                    quantity,
                    quantity,  # 初始时，剩余数量=原始数量
                    cost_basis,
                    purchase_date,
                    0,  # is_closed = False
                )
            )

        if not lots_to_insert:
            logger.info("✅ 没有找到需要迁移的BUY交易")
            return

        # 批量插入
        insert_sql = f"""
            INSERT INTO {T.POSITION_LOTS} (
                {F.PositionLots.USER_ID},
                {F.SYMBOL},
                {F.PositionLots.TRANSACTION_ID},
                {F.PositionLots.ORIGINAL_QUANTITY},
                {F.PositionLots.REMAINING_QUANTITY},
                {F.PositionLots.COST_BASIS},
                {F.PositionLots.PURCHASE_DATE},
                {F.PositionLots.IS_CLOSED}
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        cursor.executemany(insert_sql, lots_to_insert)
        conn.commit()
        logger.info(f"🎉 成功迁移 {len(lots_to_insert)} 条BUY交易到 {T.POSITION_LOTS}")

    except Exception as e:
        logger.error(f"❌ 在迁移历史BUY交易时发生错误: {e}")
        conn.rollback()
        raise


def migrate_database(db_path: str, dry_run: bool = False) -> bool:
    """
    执行数据库迁移
    
    Args:
        db_path: 数据库文件路径
        dry_run: 是否为试运行模式
        
    Returns:
        bool: 迁移是否成功
    """
    logger = logging.getLogger(__name__)
    
    try:
        # 检查数据库文件是否存在
        if not Path(db_path).exists():
            logger.error(f"❌ 数据库文件不存在: {db_path}")
            return False
        
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        logger.info(f"📊 开始检查数据库: {db_path}")
        
        # 检查交易表是否已存在
        existing_tables = check_trading_tables_exist(cursor)
        
        logger.info("📋 交易表存在情况:")
        for table, exists in existing_tables.items():
            status = "✅ 已存在" if exists else "❌ 不存在"
            logger.info(f"  - {table}: {status}")
        
        # 如果所有表都已存在，无需迁移
        if all(existing_tables.values()):
            logger.info("✅ 所有交易表已存在，无需迁移")
            return True
        
        if dry_run:
            logger.info("🔍 试运行模式，将执行以下操作:")
            
            # 显示将要创建的表
            missing_tables = [table for table, exists in existing_tables.items() if not exists]
            if missing_tables:
                logger.info(f"📝 将创建以下表: {', '.join(missing_tables)}")
                for sql in create_trading_table_definitions():
                    logger.info(f"SQL: {sql.strip()}")
                    
                logger.info("📝 将创建以下索引:")
                for sql in create_trading_indexes():
                    logger.info(f"SQL: {sql.strip()}")
            
            logger.info("⏳ (试运行) 将从历史BUY交易迁移数据到 position_lots")
            return True
        
        # 执行实际迁移
        logger.info("🚀 开始执行数据库迁移...")
        
        # 创建交易相关表
        for table_sql in create_trading_table_definitions():
            cursor.execute(table_sql)
        logger.info(f"✅ 表创建/验证完成")

        # 创建交易相关索引
        for index_sql in create_trading_indexes():
            cursor.execute(index_sql)
        logger.info(f"✅ 索引创建完成")
        
        # 确保 daily_pnl 新增列（兼容已有表）
        ensure_daily_pnl_columns(conn, cursor)

        # 从历史BUY交易迁移数据到 position_lots
        migrate_lots_from_history(conn, cursor)

        # 提交事务
        conn.commit()
        
        # 验证迁移结果
        final_tables = check_trading_tables_exist(cursor)
        success = all(final_tables.values())
        
        if success:
            logger.info("🎉 数据库迁移成功完成!")
            logger.info("📋 最终交易表状态:")
            for table, exists in final_tables.items():
                logger.info(f"  - {table}: ✅ 已存在")
        else:
            logger.error("❌ 数据库迁移失败")
            for table, exists in final_tables.items():
                status = "✅ 已存在" if exists else "❌ 缺失"
                logger.error(f"  - {table}: {status}")
        
        return success
        
    except Exception as e:
        logger.error(f"❌ 数据库迁移过程中发生错误: {e}")
        return False
        
    finally:
        if 'conn' in locals():
            conn.close()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="为现有数据库添加交易相关表")
    parser.add_argument(
        "--db-path",
        type=str,
        default="database/stock_data.db",
        help="数据库文件路径 (默认: database/stock_data.db)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="试运行模式，只检查不执行实际迁移"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="详细输出"
    )
    
    args = parser.parse_args()
    
    # 设置日志
    log_level = "DEBUG" if args.verbose else "INFO"
    setup_logging(level=log_level)
    logger = logging.getLogger(__name__)
    
    logger.info("🔧 股票交易表迁移工具")
    logger.info(f"📁 数据库路径: {args.db_path}")
    
    if args.dry_run:
        logger.info("🔍 运行模式: 试运行 (不会修改数据库)")
    else:
        logger.info("🚀 运行模式: 实际迁移")
    
    # 执行迁移
    success = migrate_database(args.db_path, args.dry_run)
    
    if success:
        if args.dry_run:
            logger.info("✅ 试运行完成")
        else:
            logger.info("✅ 迁移完成")
        sys.exit(0)
    else:
        logger.error("❌ 迁移失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
