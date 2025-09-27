#!/usr/bin/env python3
"""
SQLite 表结构管理
负责数据库表的创建、验证和管理
"""

import sqlite3
import logging
from typing import List, Optional
from .config import StorageConfig


class SQLiteSchemaManager:
    """SQLite 表结构管理器"""
    
    def __init__(self, connection: sqlite3.Connection, cursor: sqlite3.Cursor):
        """
        初始化表结构管理器
        
        Args:
            connection: SQLite 数据库连接
            cursor: SQLite 游标
        """
        self.connection = connection
        self.cursor = cursor
        self.config = StorageConfig()
        self.logger = logging.getLogger(__name__)
    
    def create_tables(self) -> None:
        """创建数据库表结构"""
        self.logger.info("📊 创建/修复数据库表结构...")
        
        # 创建核心表
        for table_sql in self._get_table_definitions():
            self.cursor.execute(table_sql)
        
        # 注意：交易表和批次追踪表由connect()方法确保创建，避免重复调用
        
        # 创建索引
        for index_sql in self.config.get_core_indexes():
            self.cursor.execute(index_sql)
        
        self.connection.commit()
        self.logger.info("✅ 数据库表结构就绪")
    
    def schema_exists(self) -> bool:
        """检查核心表是否已存在"""
        try:
            required_tables = self.config.Tables.get_all_required_tables()
            placeholders = ",".join(["?"] * len(required_tables))
            sql = f"SELECT name FROM sqlite_master WHERE type='table' AND name IN ({placeholders})"
            rows = self.cursor.execute(sql, required_tables).fetchall()
            return len(rows) == len(required_tables)
        except Exception:
            return False
    
    def trading_tables_exist(self) -> bool:
        """检查交易相关表是否已存在"""
        try:
            trading_tables = self.config.Tables.get_trading_tables()
            placeholders = ",".join(["?"] * len(trading_tables))
            sql = f"SELECT name FROM sqlite_master WHERE type='table' AND name IN ({placeholders})"
            rows = self.cursor.execute(sql, trading_tables).fetchall()
            return len(rows) == len(trading_tables)
        except Exception:
            return False
    
    def lot_tracking_tables_exist(self) -> bool:
        """检查批次追踪相关表是否已存在"""
        try:
            lot_tracking_tables = self.config.Tables.get_lot_tracking_tables()
            placeholders = ",".join(["?"] * len(lot_tracking_tables))
            sql = f"SELECT name FROM sqlite_master WHERE type='table' AND name IN ({placeholders})"
            rows = self.cursor.execute(sql, lot_tracking_tables).fetchall()
            return len(rows) == len(lot_tracking_tables)
        except Exception:
            return False
    
    def ensure_lot_tracking_tables(self) -> None:
        """确保批次追踪相关表存在（幂等操作，仅创建批次追踪表及索引）"""
        T = self.config.Tables
        F = self.config.Fields

        # Lots（position_lots）
        self.cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {T.POSITION_LOTS} (
                {F.PositionLots.ID} INTEGER PRIMARY KEY AUTOINCREMENT,
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
            """
        )

        # Sale Allocations（sale_allocations）
        self.cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {T.SALE_ALLOCATIONS} (
                {F.SaleAllocations.ID} INTEGER PRIMARY KEY AUTOINCREMENT,
                {F.SaleAllocations.SALE_TRANSACTION_ID} INTEGER NOT NULL,
                {F.SaleAllocations.LOT_ID} INTEGER NOT NULL,
                {F.SaleAllocations.QUANTITY_SOLD} REAL NOT NULL,
                {F.SaleAllocations.COST_BASIS} REAL NOT NULL,
                {F.SaleAllocations.SALE_PRICE} REAL NOT NULL,
                {F.SaleAllocations.REALIZED_PNL} REAL NOT NULL,
                {F.CREATED_AT} TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY ({F.SaleAllocations.SALE_TRANSACTION_ID}) REFERENCES {T.TRANSACTIONS}({F.Transactions.ID}) ON DELETE RESTRICT,
                FOREIGN KEY ({F.SaleAllocations.LOT_ID}) REFERENCES {T.POSITION_LOTS}({F.PositionLots.ID}) ON DELETE RESTRICT
            )
            """
        )

        # 创建批次追踪相关索引（性能优化版本）
        lot_tracking_indexes = [
            # 基础查询索引
            f"CREATE INDEX IF NOT EXISTS idx_{T.POSITION_LOTS}_symbol ON {T.POSITION_LOTS} ({F.SYMBOL})",
            f"CREATE INDEX IF NOT EXISTS idx_{T.POSITION_LOTS}_symbol_date ON {T.POSITION_LOTS} ({F.SYMBOL}, {F.PositionLots.PURCHASE_DATE})",
            f"CREATE INDEX IF NOT EXISTS idx_{T.POSITION_LOTS}_transaction ON {T.POSITION_LOTS} ({F.PositionLots.TRANSACTION_ID})",
            f"CREATE INDEX IF NOT EXISTS idx_{T.POSITION_LOTS}_active ON {T.POSITION_LOTS} ({F.SYMBOL}, {F.PositionLots.IS_CLOSED})",
            
            # 性能优化索引 - 批量查询优化
            f"CREATE INDEX IF NOT EXISTS idx_{T.POSITION_LOTS}_batch_query ON {T.POSITION_LOTS} ({F.SYMBOL}, {F.PositionLots.IS_CLOSED}, {F.PositionLots.PURCHASE_DATE})",
            f"CREATE INDEX IF NOT EXISTS idx_{T.POSITION_LOTS}_closed_archive ON {T.POSITION_LOTS} ({F.PositionLots.IS_CLOSED}, {F.PositionLots.REMAINING_QUANTITY}, {F.CREATED_AT})",
            f"CREATE INDEX IF NOT EXISTS idx_{T.POSITION_LOTS}_fifo_matching ON {T.POSITION_LOTS} ({F.SYMBOL}, {F.PositionLots.IS_CLOSED}, {F.PositionLots.PURCHASE_DATE}, {F.PositionLots.ID})",
            f"CREATE INDEX IF NOT EXISTS idx_{T.POSITION_LOTS}_lifo_matching ON {T.POSITION_LOTS} ({F.SYMBOL}, {F.PositionLots.IS_CLOSED}, {F.PositionLots.PURCHASE_DATE} DESC, {F.PositionLots.ID})",
            
            # 卖出分配索引
            f"CREATE INDEX IF NOT EXISTS idx_{T.SALE_ALLOCATIONS}_transaction ON {T.SALE_ALLOCATIONS} ({F.SaleAllocations.SALE_TRANSACTION_ID})",
            f"CREATE INDEX IF NOT EXISTS idx_{T.SALE_ALLOCATIONS}_lot ON {T.SALE_ALLOCATIONS} ({F.SaleAllocations.LOT_ID})",
            
            # 税务报告和分析查询优化
            f"CREATE INDEX IF NOT EXISTS idx_{T.SALE_ALLOCATIONS}_user_date ON {T.SALE_ALLOCATIONS} (lot_id, sale_transaction_id)",
            f"CREATE INDEX IF NOT EXISTS idx_{T.SALE_ALLOCATIONS}_realized_pnl ON {T.SALE_ALLOCATIONS} ({F.SaleAllocations.REALIZED_PNL}, {F.SaleAllocations.SALE_TRANSACTION_ID})",
        ]

        for index_sql in lot_tracking_indexes:
            self.cursor.execute(index_sql)

        self.connection.commit()
        self.logger.info("✅ 批次追踪表创建完成")

    def ensure_trading_tables(self) -> None:
        """确保交易相关表存在（幂等操作，仅创建交易三表及索引）"""
        T = self.config.Tables
        F = self.config.Fields

        # 逐表创建（IF NOT EXISTS），避免复杂列表拼接出错
        self.cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {T.TRANSACTIONS} (
                {F.Transactions.ID} INTEGER PRIMARY KEY AUTOINCREMENT,
                {F.Transactions.EXTERNAL_ID} TEXT,
                {F.SYMBOL} TEXT NOT NULL,
                {F.Transactions.TRANSACTION_TYPE} TEXT NOT NULL CHECK ({F.Transactions.TRANSACTION_TYPE} IN ('BUY','SELL')),
                {F.Transactions.QUANTITY} REAL NOT NULL,
                {F.Transactions.PRICE} REAL NOT NULL,
                {F.Transactions.TRANSACTION_DATE} TEXT NOT NULL,
                {F.Transactions.PLATFORM} TEXT,
                {F.Transactions.LOT_ID} INTEGER,
                {F.Transactions.NOTES} TEXT,
                {F.CREATED_AT} TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                {F.UPDATED_AT} TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY ({F.SYMBOL}) REFERENCES {T.STOCKS}({F.SYMBOL}),
                UNIQUE({F.Transactions.EXTERNAL_ID}) -- 幂等约束
            )
            """
        )

        self.cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {T.POSITIONS} (
                {F.Positions.ID} INTEGER PRIMARY KEY AUTOINCREMENT,
                {F.SYMBOL} TEXT NOT NULL,
                {F.Positions.QUANTITY} REAL NOT NULL,
                {F.Positions.AVG_COST} REAL NOT NULL,
                {F.Positions.TOTAL_COST} REAL NOT NULL,
                {F.Positions.FIRST_BUY_DATE} TEXT,
                {F.Positions.LAST_TRANSACTION_DATE} TEXT,
                {F.Positions.IS_ACTIVE} INTEGER DEFAULT 1,
                {F.CREATED_AT} TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                {F.UPDATED_AT} TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE({F.SYMBOL})
            )
            """
        )

        self.cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {T.DAILY_PNL} (
                {F.DailyPnL.ID} INTEGER PRIMARY KEY AUTOINCREMENT,
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
                UNIQUE({F.SYMBOL}, {F.DailyPnL.VALUATION_DATE})
            )
            """
        )

        # 注意：交易相关索引由 StorageConfig.get_all_indexes() 统一创建，避免重复

        self.connection.commit()
        self.logger.info("✅ 交易表创建完成")
    
    
    
    def _get_table_definitions(self) -> List[str]:
        """获取表定义SQL"""
        T = self.config.Tables
        F = self.config.Fields
        
        return [
            f"""
            CREATE TABLE IF NOT EXISTS {T.STOCKS} (
                {F.SYMBOL} TEXT PRIMARY KEY,
                {F.Stocks.COMPANY_NAME} TEXT,
                {F.Stocks.SECTOR} TEXT,
                {F.Stocks.INDUSTRY} TEXT,
                {F.Stocks.MARKET_CAP} REAL,
                {F.Stocks.EMPLOYEES} INTEGER,
                {F.Stocks.DESCRIPTION} TEXT,
                {F.UPDATED_AT} TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            f"""
            CREATE TABLE IF NOT EXISTS {T.STOCK_PRICES} (
                {F.StockPrices.ID} INTEGER PRIMARY KEY AUTOINCREMENT,
                {F.SYMBOL} TEXT NOT NULL,
                {F.StockPrices.DATE} TEXT NOT NULL,
                {F.StockPrices.OPEN} REAL,
                {F.StockPrices.HIGH} REAL,
                {F.StockPrices.LOW} REAL,
                {F.StockPrices.CLOSE} REAL,
                {F.StockPrices.VOLUME} INTEGER,
                {F.StockPrices.ADJ_CLOSE} REAL,
                FOREIGN KEY ({F.SYMBOL}) REFERENCES {T.STOCKS}({F.SYMBOL}),
                UNIQUE({F.SYMBOL}, {F.StockPrices.DATE})
            )
            """,
            f"""
            CREATE TABLE IF NOT EXISTS {T.INCOME_STATEMENT} (
                {F.FinancialStatement.ID} INTEGER PRIMARY KEY AUTOINCREMENT,
                {F.SYMBOL} TEXT NOT NULL,
                {F.FinancialStatement.PERIOD} TEXT NOT NULL,
                {F.FinancialStatement.METRIC_NAME} TEXT NOT NULL,
                {F.FinancialStatement.METRIC_VALUE} REAL,
                {F.CREATED_AT} TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY ({F.SYMBOL}) REFERENCES {T.STOCKS}({F.SYMBOL}),
                UNIQUE({F.SYMBOL}, {F.FinancialStatement.PERIOD}, {F.FinancialStatement.METRIC_NAME})
            )
            """,
            f"""
            CREATE TABLE IF NOT EXISTS {T.BALANCE_SHEET} (
                {F.FinancialStatement.ID} INTEGER PRIMARY KEY AUTOINCREMENT,
                {F.SYMBOL} TEXT NOT NULL,
                {F.FinancialStatement.PERIOD} TEXT NOT NULL,
                {F.FinancialStatement.METRIC_NAME} TEXT NOT NULL,
                {F.FinancialStatement.METRIC_VALUE} REAL,
                {F.CREATED_AT} TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY ({F.SYMBOL}) REFERENCES {T.STOCKS}({F.SYMBOL}),
                UNIQUE({F.SYMBOL}, {F.FinancialStatement.PERIOD}, {F.FinancialStatement.METRIC_NAME})
            )
            """,
            f"""
            CREATE TABLE IF NOT EXISTS {T.CASH_FLOW} (
                {F.FinancialStatement.ID} INTEGER PRIMARY KEY AUTOINCREMENT,
                {F.SYMBOL} TEXT NOT NULL,
                {F.FinancialStatement.PERIOD} TEXT NOT NULL,
                {F.FinancialStatement.METRIC_NAME} TEXT NOT NULL,
                {F.FinancialStatement.METRIC_VALUE} REAL,
                {F.CREATED_AT} TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY ({F.SYMBOL}) REFERENCES {T.STOCKS}({F.SYMBOL}),
                UNIQUE({F.SYMBOL}, {F.FinancialStatement.PERIOD}, {F.FinancialStatement.METRIC_NAME})
            )
            """,
            f"""
            CREATE TABLE IF NOT EXISTS {T.DOWNLOAD_LOGS} (
                {F.DownloadLogs.ID} INTEGER PRIMARY KEY AUTOINCREMENT,
                {F.SYMBOL} TEXT NOT NULL,
                {F.DownloadLogs.DOWNLOAD_TYPE} TEXT NOT NULL,
                {F.DownloadLogs.STATUS} TEXT NOT NULL,
                {F.DownloadLogs.DATA_POINTS} INTEGER DEFAULT 0,
                {F.DownloadLogs.ERROR_MESSAGE} TEXT,
                {F.DownloadLogs.DETAILS} TEXT,
                {F.DownloadLogs.DOWNLOAD_TIMESTAMP} TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY ({F.SYMBOL}) REFERENCES {T.STOCKS}({F.SYMBOL})
            )
            """
        ]
