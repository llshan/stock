#!/usr/bin/env python3
"""
SQLite 存储实现
使用模块化设计，将复杂逻辑分离到专门的模块中
"""

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ..models import (
    BasicInfo,
    DataQuality,
    FinancialData,
    FinancialStatement,
    PriceData,
    StockData,
)
from .base import BaseStorage, StorageError
from .config import StorageConfig
from .sqlite_schema import SQLiteSchemaManager
from .sqlite_queries import SQLiteQueryManager


class SQLiteStorage(BaseStorage):
    """SQLite 存储实现"""

    def __init__(self, db_path: str = "database/stock_data.db"):
        """
        初始化 SQLite 存储

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self.connection: Optional[sqlite3.Connection] = None
        self.cursor: Optional[sqlite3.Cursor] = None
        self.logger = logging.getLogger(__name__)
        self.config = StorageConfig()
        
        # 初始化管理器
        self.schema_manager: Optional[SQLiteSchemaManager] = None
        self.query_manager: Optional[SQLiteQueryManager] = None
        # 事务深度：用于区分用户级事务与内部隐式事务
        self._txn_depth: int = 0
        
        self.connect()

    def connect(self) -> None:
        """建立数据库连接"""
        try:
            # 确保数据库目录存在
            dbp = Path(self.db_path)
            if dbp.parent:
                dbp.parent.mkdir(parents=True, exist_ok=True)

            # 建立连接
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.execute("PRAGMA foreign_keys = ON")
            self.cursor = self.connection.cursor()
            
            # 初始化管理器
            self.schema_manager = SQLiteSchemaManager(self.connection, self.cursor)
            self.query_manager = SQLiteQueryManager(self.connection, self.cursor)

            # 初始化表结构
            if not self.schema_manager.schema_exists():
                self.schema_manager.create_tables()
            
            # 确保交易相关表存在（幂等操作）
            self.schema_manager.ensure_trading_tables()
            
            # 确保批次追踪表存在（幂等操作）
            self.schema_manager.ensure_lot_tracking_tables()

            # 创建交易和批次追踪相关索引
            for index_sql in self.config.get_trading_and_lot_indexes():
                self.cursor.execute(index_sql)

            self.logger.info(f"📁 SQLite 数据库连接成功: {self.db_path}")

        except Exception as e:
            self.logger.error(f"❌ SQLite 数据库连接失败: {e}")
            raise StorageError(f"Failed to connect to SQLite database: {e}", "connect")

    def disconnect(self) -> None:
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            self.logger.info("📴 SQLite 数据库连接已关闭")

    def close(self) -> None:
        """关闭存储连接"""
        self.disconnect()

    def _check_connection(self, operation_name: str = "operation") -> None:
        """检查数据库连接是否可用"""
        if self.cursor is None or self.connection is None:
            raise StorageError(
                f"Database connection not available for {operation_name}", operation_name
            )
    
    def _maybe_commit(self) -> None:
        """
        智能提交：仅在不处于事务中时才提交
        防止在 with transaction() 上下文中提前提交破坏原子性
        """
        # 仅当不处于用户级事务中，才提交内部写入
        if self.connection and self._txn_depth == 0:
            self.connection.commit()

    # =================== 数据存储方法 ===================
    
    def store_stock_data(self, symbol: str, stock_data: Union[StockData, Dict]) -> bool:
        """存储股票数据"""
        self._check_connection("store_stock_data")
        try:
            if isinstance(stock_data, StockData):
                # 确保股票记录存在
                basic_info = getattr(stock_data, 'basic_info', None)
                if basic_info:
                    self._store_basic_info(symbol, basic_info)
                else:
                    self.ensure_stock_exists(symbol)

                # 存储价格数据
                self._store_price_data_batch(symbol, stock_data.price_data)

            elif isinstance(stock_data, dict):
                # 从字典存储
                if 'basic_info' in stock_data:
                    self._store_basic_info(symbol, stock_data['basic_info'])
                else:
                    self.ensure_stock_exists(symbol)

                if 'price_data' in stock_data:
                    price_data = PriceData.from_dict(stock_data['price_data'])
                    self._store_price_data_batch(symbol, price_data)

            # 记录下载日志
            self._log_download(
                symbol,
                "stock",
                "success",
                (
                    getattr(stock_data, 'data_points', 0)
                    if hasattr(stock_data, 'data_points')
                    else (stock_data.get('data_points', 0) if isinstance(stock_data, dict) else 0)
                ),
            )

            return True

        except Exception as e:
            self.logger.error(f"❌ 存储股票数据失败 {symbol}: {e}")
            self._log_download(symbol, "stock", "failed", 0, str(e))
            return False

    def store_financial_data(self, symbol: str, financial_data: Union[FinancialData, Dict]) -> bool:
        """存储财务数据"""
        self._check_connection("store_financial_data")
        try:
            if isinstance(financial_data, FinancialData):
                # 存储基本信息
                self._store_basic_info(symbol, financial_data.basic_info)

                # 存储财务报表
                for stmt_type, statement in financial_data.financial_statements.items():
                    self._store_financial_statement(symbol, stmt_type, statement)

            elif isinstance(financial_data, dict):
                if 'basic_info' in financial_data:
                    self._store_basic_info(symbol, financial_data['basic_info'])

                if 'financial_statements' in financial_data:
                    for stmt_type, stmt_data in financial_data['financial_statements'].items():
                        if 'error' not in stmt_data:
                            statement = FinancialStatement.from_dict(stmt_data)
                            self._store_financial_statement(symbol, stmt_type, statement)

            # 记录下载日志
            stmt_count = (
                len(getattr(financial_data, 'financial_statements', {}))
                if hasattr(financial_data, 'financial_statements')
                else len(financial_data.get('financial_statements', {}))
            )
            self._log_download(symbol, "financial", "success", stmt_count)

            return True

        except Exception as e:
            self.logger.error(f"❌ 存储财务数据失败 {symbol}: {e}")
            self._log_download(symbol, "financial", "failed", 0, str(e))
            return False

    def store_data_quality(self, symbol: str, quality_data: Union[DataQuality, Dict]) -> bool:
        """将数据质量评估作为下载日志的一部分进行记录"""
        try:
            if isinstance(quality_data, DataQuality):
                details = quality_data.to_dict()
            else:
                details = quality_data

            self._log_download(
                symbol=symbol,
                download_type="quality",
                status="success",
                data_points=0,
                error_message=None,
                details=details,
            )
            return True
        except Exception as e:
            self.logger.error(f"❌ 记录数据质量评估失败 {symbol}: {e}")
            try:
                self._log_download(symbol, "quality", "failed", 0, str(e))
            except Exception:
                pass
            return False

    # =================== 数据获取方法 ===================

    def get_stock_data(
        self, symbol: str, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> Optional[StockData]:
        """获取股票数据"""
        if not self.query_manager:
            return None
        return self.query_manager.get_stock_data(symbol, start_date, end_date)

    def get_financial_data(self, symbol: str) -> Optional[FinancialData]:
        """获取财务数据"""
        if not self.query_manager:
            return None
        return self.query_manager.get_financial_data(symbol)

    def get_financial_metrics(
        self, symbol: str, statement_type: str, start_period: Optional[str] = None, end_period: Optional[str] = None
    ) -> Optional:
        """获取财务指标数据"""
        if not self.query_manager:
            return None
        return self.query_manager.get_financial_metrics(symbol, statement_type, start_period, end_period)

    def get_last_update_date(self, symbol: str) -> Optional[str]:
        """获取最后更新日期"""
        if not self.query_manager:
            return None
        return self.query_manager.get_last_update_date(symbol)

    def get_last_financial_period(self, symbol: str) -> Optional[str]:
        """获取最近财务期间"""
        if not self.query_manager:
            return None
        return self.query_manager.get_last_financial_period(symbol)

    def get_existing_symbols(self) -> List[str]:
        """获取已存储的股票代码列表"""
        if not self.query_manager:
            return []
        return self.query_manager.get_existing_symbols()

    # =================== 私有辅助方法 ===================

    def _store_basic_info(self, symbol: str, basic_info: Union[BasicInfo, Dict]) -> None:
        """存储股票基本信息"""
        self._check_connection("_store_basic_info")
        if isinstance(basic_info, BasicInfo):
            data = basic_info.to_dict()
        else:
            data = basic_info

        T = self.config.Tables.STOCKS
        F = self.config.Fields
        
        fields = f"{F.SYMBOL}, {F.Stocks.COMPANY_NAME}, {F.Stocks.SECTOR}, {F.Stocks.INDUSTRY}, {F.Stocks.MARKET_CAP}, {F.Stocks.EMPLOYEES}, {F.Stocks.DESCRIPTION}, {F.UPDATED_AT}"
        placeholders = "?, ?, ?, ?, ?, ?, ?, ?"
        
        sql = self.config.SQLTemplates.INSERT_OR_REPLACE.format(
            table=T,
            fields=fields,
            placeholders=placeholders
        )

        self.cursor.execute(
            sql,
            (
                symbol,
                data.get('company_name', ''),
                data.get('sector', ''),
                data.get('industry', ''),
                data.get('market_cap', 0),
                data.get('employees', 0),
                data.get('description', ''),
                datetime.now().isoformat(),
            ),
        )
        self._maybe_commit()


    def _store_price_data_batch(self, symbol: str, price_data: PriceData) -> None:
        """批量存储价格数据"""
        self._check_connection("_store_price_data_batch")
        
        T = self.config.Tables.STOCK_PRICES
        F = self.config.Fields
        
        fields = f"{F.SYMBOL}, {F.StockPrices.DATE}, {F.StockPrices.OPEN}, {F.StockPrices.HIGH}, {F.StockPrices.LOW}, {F.StockPrices.CLOSE}, {F.StockPrices.VOLUME}, {F.StockPrices.ADJ_CLOSE}"
        placeholders = "?, ?, ?, ?, ?, ?, ?, ?"
        
        sql = self.config.SQLTemplates.INSERT_OR_REPLACE.format(
            table=T,
            fields=fields,
            placeholders=placeholders
        )
        
        # 准备批量数据
        data = [
            (symbol, price_data.dates[i], price_data.open[i], price_data.high[i],
             price_data.low[i], price_data.close[i], price_data.volume[i], price_data.adj_close[i])
            for i in range(len(price_data.dates))
        ]
        
        # 批量插入
        self.cursor.executemany(sql, data)
        self._maybe_commit()

    def _store_financial_statement(
        self, symbol: str, stmt_type: str, statement: FinancialStatement
    ) -> None:
        """存储财务报表"""
        self._check_connection("_store_financial_statement")
        for period in statement.periods:
            # 获取该期间的数据
            period_data = {}
            for item_name, values in statement.items.items():
                try:
                    period_index = statement.periods.index(period)
                    if period_index < len(values):
                        period_data[item_name] = values[period_index]
                except (ValueError, IndexError):
                    period_data[item_name] = None

            # 存储到独立的报表表
            self._store_to_statement_table(stmt_type, symbol, period, period_data)

        self._maybe_commit()

    def _store_to_statement_table(
        self, stmt_type: str, symbol: str, period: str, metrics: Dict[str, Optional[float]]
    ) -> None:
        """存储财务指标到对应的独立报表表中"""
        self._check_connection("_store_to_statement_table")
        
        # 使用配置类获取表名
        table_name = self.config.get_table_for_statement_type(stmt_type)
        F = self.config.Fields
        
        fields = f"{F.SYMBOL}, {F.FinancialStatement.PERIOD}, {F.FinancialStatement.METRIC_NAME}, {F.FinancialStatement.METRIC_VALUE}, {F.CREATED_AT}"
        placeholders = "?, ?, ?, ?, ?"
        
        sql = self.config.SQLTemplates.INSERT_OR_REPLACE.format(
            table=table_name,
            fields=fields,
            placeholders=placeholders
        )

        for metric_name, metric_value in metrics.items():
            if metric_value is not None:
                self.cursor.execute(
                    sql,
                    (symbol, period, metric_name, metric_value, datetime.now().isoformat()),
                )

    def _log_download(
        self,
        symbol: str,
        download_type: str,
        status: str,
        data_points: int = 0,
        error_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """记录下载日志"""
        self._check_connection("_log_download")
        
        T = self.config.Tables.DOWNLOAD_LOGS
        F = self.config.Fields
        
        fields = f"{F.SYMBOL}, {F.DownloadLogs.DOWNLOAD_TYPE}, {F.DownloadLogs.STATUS}, {F.DownloadLogs.DATA_POINTS}, {F.DownloadLogs.ERROR_MESSAGE}, {F.DownloadLogs.DETAILS}"
        placeholders = "?, ?, ?, ?, ?, ?"
        
        sql = self.config.SQLTemplates.INSERT_OR_REPLACE.format(
            table=T,
            fields=fields,
            placeholders=placeholders
        )
        
        details_json = json.dumps(details, ensure_ascii=False) if details else None
        
        self.cursor.execute(
            sql,
            (symbol, download_type, status, data_points, error_message, details_json),
        )
        self._maybe_commit()

    # ============= 事务管理 =============
    
    @contextmanager
    def transaction(self):
        """事务上下文管理器，支持嵌套（基于 SAVEPOINT）"""
        self._check_connection("transaction")
        nested = self._txn_depth > 0
        sp_name = f"sp_txn_{self._txn_depth+1}"
        try:
            if nested:
                # 嵌套事务使用保存点
                self.connection.execute(f"SAVEPOINT {sp_name}")
            else:
                # 顶层事务
                self.connection.execute("BEGIN")
            self._txn_depth += 1
            yield
            # 提交
            if nested:
                self.connection.execute(f"RELEASE SAVEPOINT {sp_name}")
            else:
                self.connection.commit()
        except Exception as e:
            # 回滚
            if nested:
                self.connection.execute(f"ROLLBACK TO SAVEPOINT {sp_name}")
                self.connection.execute(f"RELEASE SAVEPOINT {sp_name}")
            else:
                self.connection.rollback()
            self.logger.error(f"事务回滚: {e}")
            raise
        finally:
            # 事务深度计数还原
            if self._txn_depth > 0:
                self._txn_depth -= 1
    
    def ensure_stock_exists(self, symbol: str) -> None:
        """确保stocks表中存在指定的股票记录，避免外键约束失败"""
        self._check_connection("ensure_stock_exists")
        
        T = self.config.Tables.STOCKS
        F = self.config.Fields
        
        # 使用 INSERT OR IGNORE 直接创建记录（如果不存在）
        # 插入所有字段以确保完整性，与 _ensure_stock_exists 保持一致
        fields = f"{F.SYMBOL}, {F.Stocks.COMPANY_NAME}, {F.Stocks.SECTOR}, {F.Stocks.INDUSTRY}, {F.Stocks.MARKET_CAP}, {F.Stocks.EMPLOYEES}, {F.Stocks.DESCRIPTION}, {F.UPDATED_AT}"
        placeholders = "?, ?, ?, ?, ?, ?, ?, ?"
        
        sql = self.config.SQLTemplates.INSERT_OR_IGNORE.format(
            table=T,
            fields=fields,
            placeholders=placeholders
        )
        
        self.cursor.execute(sql, (symbol, '', '', '', 0, 0, '', datetime.now().isoformat()))
        self._maybe_commit()

    # ============= 交易相关方法 =============
    
    def upsert_transaction(self, transaction_data: Dict[str, Any]) -> int:
        """
        插入交易记录（支持幂等性）
        
        Args:
            transaction_data: 交易数据，可包含external_id用于去重
            
        Returns:
            交易记录ID
            
        Raises:
            sqlite3.IntegrityError: 当external_id重复时（幂等保护）
        """
        self._check_connection("upsert_transaction")
        
        # 确保股票记录存在，避免外键约束失败
        self.ensure_stock_exists(transaction_data['symbol'])
        
        T = self.config.Tables.TRANSACTIONS
        F = self.config.Fields
        
        external_id = transaction_data.get('external_id')
        
        # 如果提供了external_id，先检查是否已存在（幂等性检查）
        if external_id:
            existing_id = self._get_transaction_by_external_id(
                external_id
            )
            if existing_id:
                self.logger.debug(f"交易 {external_id} 已存在，返回现有ID: {existing_id}")
                return existing_id
        
        # 构建字段和值
        if external_id:
            fields = f"{F.Transactions.EXTERNAL_ID}, {F.SYMBOL}, "                     f"{F.Transactions.TRANSACTION_TYPE}, {F.Transactions.QUANTITY}, "                     f"{F.Transactions.PRICE}, "                     f"{F.Transactions.TRANSACTION_DATE}, {F.Transactions.PLATFORM}, {F.Transactions.NOTES}, {F.UPDATED_AT}"
            placeholders = "?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP"
            values = (
                external_id,
                transaction_data['symbol'],
                transaction_data['transaction_type'],
                float(transaction_data['quantity']),
                float(transaction_data['price']),
                transaction_data['transaction_date'],
                transaction_data.get('platform'),
                transaction_data.get('notes'),
            )
        else:
            fields = f"{F.SYMBOL}, {F.Transactions.TRANSACTION_TYPE}, "                     f"{F.Transactions.QUANTITY}, {F.Transactions.PRICE}, "                     f"{F.Transactions.TRANSACTION_DATE}, {F.Transactions.PLATFORM}, {F.Transactions.NOTES}, {F.UPDATED_AT}"
            placeholders = "?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP"
            values = (
                transaction_data['symbol'],
                transaction_data['transaction_type'],
                float(transaction_data['quantity']),
                float(transaction_data['price']),
                transaction_data['transaction_date'],
                transaction_data.get('platform'),
                transaction_data.get('notes'),
            )
        
        sql = f"INSERT INTO {T} ({fields}) VALUES ({placeholders})"
        
        try:
            self.cursor.execute(sql, values)
            self._maybe_commit()
            return self.cursor.lastrowid
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e) and external_id:
                # 唯一约束冲突，重新查询返回已存在的ID
                existing_id = self._get_transaction_by_external_id(
                    external_id
                )
                if existing_id:
                    self.logger.debug(f"交易 {external_id} 并发插入，返回现有ID: {existing_id}")
                    return existing_id
            raise
    
    def _get_transaction_by_external_id(self, external_id: str) -> Optional[int]:
        """根据external_id查询已存在的交易记录ID"""
        T = self.config.Tables.TRANSACTIONS
        F = self.config.Fields
        
        sql = f"""
            SELECT {F.Transactions.ID} FROM {T} 
            WHERE {F.Transactions.EXTERNAL_ID} = ?
        """
        
        self.cursor.execute(sql, (external_id,))
        row = self.cursor.fetchone()
        return row[0] if row else None

    def get_transactions(self, symbol: str = None, 
                        start_date: str = None, end_date: str = None, 
                        transaction_type: str = None) -> List[Dict[str, Any]]:
        """获取交易记录"""
        self._check_connection("get_transactions")
        
        T = self.config.Tables.TRANSACTIONS
        F = self.config.Fields
        
        conditions = []
        params = []
        
        if symbol:
            conditions.append(f"{F.SYMBOL} = ?")
            params.append(symbol)
        
        if start_date:
            conditions.append(f"{F.Transactions.TRANSACTION_DATE} >= ?")
            params.append(start_date)
            
        if end_date:
            conditions.append(f"{F.Transactions.TRANSACTION_DATE} <= ?")
            params.append(end_date)

        if transaction_type:
            conditions.append(f"{F.Transactions.TRANSACTION_TYPE} = ?")
            params.append(transaction_type)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        sql = f"SELECT * FROM {T} WHERE {where_clause} ORDER BY {F.Transactions.TRANSACTION_DATE}, {F.Transactions.ID}"
        
        self.cursor.execute(sql, params)
        rows = self.cursor.fetchall()
        
        columns = [description[0] for description in self.cursor.description]
        return [dict(zip(columns, row)) for row in rows]

    def upsert_position(self, position_data: Dict[str, Any]) -> int:
        """插入或更新持仓记录"""
        self._check_connection("upsert_position")
        
        T = self.config.Tables.POSITIONS
        F = self.config.Fields
        
        fields = f"{F.SYMBOL}, {F.Positions.QUANTITY}, " \
                f"{F.Positions.AVG_COST}, {F.Positions.TOTAL_COST}, {F.Positions.FIRST_BUY_DATE}, " \
                f"{F.Positions.LAST_TRANSACTION_DATE}, {F.Positions.IS_ACTIVE}, {F.UPDATED_AT}"
        placeholders = "?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP"
        
        # 使用 INSERT ... ON CONFLICT(symbol) DO UPDATE 以避免 REPLACE 的副作用
        sql = (
            f"INSERT INTO {T} ({fields}) VALUES ({placeholders}) "
            f"ON CONFLICT({F.SYMBOL}) DO UPDATE SET "
            f"{F.Positions.QUANTITY}=excluded.{F.Positions.QUANTITY}, "
            f"{F.Positions.AVG_COST}=excluded.{F.Positions.AVG_COST}, "
            f"{F.Positions.TOTAL_COST}=excluded.{F.Positions.TOTAL_COST}, "
            f"{F.Positions.FIRST_BUY_DATE}=excluded.{F.Positions.FIRST_BUY_DATE}, "
            f"{F.Positions.LAST_TRANSACTION_DATE}=excluded.{F.Positions.LAST_TRANSACTION_DATE}, "
            f"{F.Positions.IS_ACTIVE}=excluded.{F.Positions.IS_ACTIVE}, "
            f"{F.UPDATED_AT}=CURRENT_TIMESTAMP"
        )

        self.cursor.execute(
            sql,
            (
                position_data['symbol'],
                position_data['quantity'],
                position_data['avg_cost'],
                position_data['total_cost'],
                position_data.get('first_buy_date'),
                position_data.get('last_transaction_date'),
                position_data.get('is_active', True),
            ),
        )
        
        self._maybe_commit()
        return self.cursor.lastrowid

    

    def get_positions(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """获取所有持仓记录"""
        self._check_connection("get_positions")
        
        T = self.config.Tables.POSITIONS
        F = self.config.Fields
        
        conditions = []
        params = []
        
        if active_only:
            conditions.append(f"{F.Positions.IS_ACTIVE} = 1")
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        sql = f"SELECT * FROM {T} WHERE {where_clause} ORDER BY {F.SYMBOL}"
        
        self.cursor.execute(sql, params)
        rows = self.cursor.fetchall()
        
        columns = [description[0] for description in self.cursor.description]
        return [dict(zip(columns, row)) for row in rows]

    def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取特定股票的持仓记录"""
        self._check_connection("get_position")
        
        T = self.config.Tables.POSITIONS
        F = self.config.Fields
        
        sql = f"SELECT * FROM {T} WHERE {F.SYMBOL} = ?"
        
        self.cursor.execute(sql, (symbol,))
        row = self.cursor.fetchone()
        
        if row:
            columns = [description[0] for description in self.cursor.description]
            return dict(zip(columns, row))
        
        return None

    def upsert_daily_pnl(self, pnl_data: Dict[str, Any]) -> int:
        """插入或更新每日盈亏记录"""
        self._check_connection("upsert_daily_pnl")
        
        T = self.config.Tables.DAILY_PNL
        F = self.config.Fields
        
        # 使用ON CONFLICT进行精确更新，避免REPLACE的副作用
        sql = f"""
        INSERT INTO {T} (
            {F.SYMBOL}, {F.DailyPnL.VALUATION_DATE},
            {F.DailyPnL.QUANTITY}, {F.DailyPnL.AVG_COST}, {F.DailyPnL.MARKET_PRICE},
            {F.DailyPnL.MARKET_VALUE}, {F.DailyPnL.UNREALIZED_PNL}, {F.DailyPnL.UNREALIZED_PNL_PCT},
            {F.DailyPnL.REALIZED_PNL}, {F.DailyPnL.REALIZED_PNL_PCT}, {F.DailyPnL.TOTAL_COST},
            {F.DailyPnL.PRICE_DATE}, {F.DailyPnL.IS_STALE_PRICE}
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT({F.SYMBOL}, {F.DailyPnL.VALUATION_DATE}) 
        DO UPDATE SET
            {F.DailyPnL.QUANTITY} = excluded.{F.DailyPnL.QUANTITY},
            {F.DailyPnL.AVG_COST} = excluded.{F.DailyPnL.AVG_COST},
            {F.DailyPnL.MARKET_PRICE} = excluded.{F.DailyPnL.MARKET_PRICE},
            {F.DailyPnL.MARKET_VALUE} = excluded.{F.DailyPnL.MARKET_VALUE},
            {F.DailyPnL.UNREALIZED_PNL} = excluded.{F.DailyPnL.UNREALIZED_PNL},
            {F.DailyPnL.UNREALIZED_PNL_PCT} = excluded.{F.DailyPnL.UNREALIZED_PNL_PCT},
            {F.DailyPnL.REALIZED_PNL} = excluded.{F.DailyPnL.REALIZED_PNL},
            {F.DailyPnL.REALIZED_PNL_PCT} = excluded.{F.DailyPnL.REALIZED_PNL_PCT},
            {F.DailyPnL.TOTAL_COST} = excluded.{F.DailyPnL.TOTAL_COST},
            {F.DailyPnL.PRICE_DATE} = excluded.{F.DailyPnL.PRICE_DATE},
            {F.DailyPnL.IS_STALE_PRICE} = excluded.{F.DailyPnL.IS_STALE_PRICE}
        """
        
        self.cursor.execute(sql, (
            pnl_data['symbol'],
            pnl_data['valuation_date'],
            float(pnl_data['quantity']),
            float(pnl_data['avg_cost']),
            float(pnl_data['market_price']) if pnl_data['market_price'] is not None else None,
            float(pnl_data['market_value']) if pnl_data['market_value'] is not None else None,
            float(pnl_data['unrealized_pnl']) if pnl_data['unrealized_pnl'] is not None else None,
            float(pnl_data['unrealized_pnl_pct']) if pnl_data['unrealized_pnl_pct'] is not None else None,
            float(pnl_data.get('realized_pnl', 0.0)),
            float(pnl_data.get('realized_pnl_pct', 0.0)),
            float(pnl_data['total_cost']) if pnl_data['total_cost'] is not None else None,
            pnl_data.get('price_date'),
            pnl_data.get('is_stale_price', 0),
        ))
        
        self._maybe_commit()
        return self.cursor.lastrowid

    def get_daily_pnl(self, symbol: str = None, 
                      start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
        """获取每日盈亏记录"""
        self._check_connection("get_daily_pnl")
        
        T = self.config.Tables.DAILY_PNL
        F = self.config.Fields
        
        conditions = []
        params = []
        
        if symbol:
            conditions.append(f"{F.SYMBOL} = ?")
            params.append(symbol)
        
        if start_date:
            conditions.append(f"{F.DailyPnL.VALUATION_DATE} >= ?")
            params.append(start_date)
            
        if end_date:
            conditions.append(f"{F.DailyPnL.VALUATION_DATE} <= ?")
            params.append(end_date)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        sql = f"SELECT * FROM {T} WHERE {where_clause} ORDER BY {F.DailyPnL.VALUATION_DATE} DESC, {F.SYMBOL}"
        
        self.cursor.execute(sql, params)
        rows = self.cursor.fetchall()
        
        columns = [description[0] for description in self.cursor.description]
        return [dict(zip(columns, row)) for row in rows]

    def delete_position(self, symbol: str) -> bool:
        """删除持仓记录"""
        self._check_connection("delete_position")
        
        T = self.config.Tables.POSITIONS
        F = self.config.Fields
        
        sql = f"DELETE FROM {T} WHERE {F.SYMBOL} = ?"
        
        self.cursor.execute(sql, (symbol,))
        self._maybe_commit()
        
        return self.cursor.rowcount > 0

    def get_stock_price_for_date(self, symbol: str, date: str, 
                                price_field: str = 'adj_close') -> Optional[float]:
        """获取指定日期的股票价格"""
        self._check_connection("get_stock_price_for_date")
        
        T = self.config.Tables.STOCK_PRICES
        F = self.config.Fields
        
        # 验证价格字段
        if not self.config.validate_price_field(price_field):
            raise ValueError(f"无效的价格字段: {price_field}")
        
        # 获取字段映射
        field_map = self.config.get_price_field_mapping()
        
        sql = f"SELECT {field_map[price_field]} FROM {T} WHERE {F.SYMBOL} = ? AND {F.StockPrices.DATE} = ?"
        
        self.cursor.execute(sql, (symbol, date))
        row = self.cursor.fetchone()
        
        return row[0] if row and row[0] is not None else None

    def get_latest_stock_price(self, symbol: str, before_date: str = None,
                              price_field: str = 'adj_close') -> Optional[tuple]:
        """获取最新的股票价格（可指定截止日期）"""
        self._check_connection("get_latest_stock_price")
        
        T = self.config.Tables.STOCK_PRICES
        F = self.config.Fields
        
        # 验证价格字段
        if not self.config.validate_price_field(price_field):
            raise ValueError(f"无效的价格字段: {price_field}")
        
        # 获取字段映射
        field_map = self.config.get_price_field_mapping()
        
        if before_date:
            sql = f"SELECT {F.StockPrices.DATE}, {field_map[price_field]} FROM {T} " \
                  f"WHERE {F.SYMBOL} = ? AND {F.StockPrices.DATE} <= ? " \
                  f"ORDER BY {F.StockPrices.DATE} DESC LIMIT 1"
            self.cursor.execute(sql, (symbol, before_date))
        else:
            sql = f"SELECT {F.StockPrices.DATE}, {field_map[price_field]} FROM {T} " \
                  f"WHERE {F.SYMBOL} = ? ORDER BY {F.StockPrices.DATE} DESC LIMIT 1"
            self.cursor.execute(sql, (symbol,))
        
        row = self.cursor.fetchone()
        
        return (row[0], row[1]) if row and row[1] is not None else None

    # ============= 批次追踪相关方法 =============
    
    def create_position_lot(self, lot_data: Dict[str, Any]) -> int:
        """创建持仓批次记录"""
        self._check_connection("create_position_lot")
        
        T = self.config.Tables.POSITION_LOTS
        F = self.config.Fields
        
        fields = f"{F.SYMBOL}, {F.PositionLots.TRANSACTION_ID}, " \
                f"{F.PositionLots.ORIGINAL_QUANTITY}, {F.PositionLots.REMAINING_QUANTITY}, " \
                f"{F.PositionLots.COST_BASIS}, {F.PositionLots.PURCHASE_DATE}, " \
                f"{F.PositionLots.IS_CLOSED}, {F.PositionLots.PORTFOLIO_ID}, {F.CREATED_AT}, {F.UPDATED_AT}"

        placeholders = "?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP"
        
        sql = f"INSERT INTO {T} ({fields}) VALUES ({placeholders})"
        
        self.cursor.execute(
            sql,
            (
                lot_data['symbol'],
                lot_data['transaction_id'],
                float(lot_data['original_quantity']),
                float(lot_data['remaining_quantity']),
                float(lot_data['cost_basis']),
                lot_data['purchase_date'],
                lot_data.get('is_closed', False),
                lot_data.get('portfolio_id', 1),  # 默认为1 (Merrill Edge)
            ),
        )
        
        self._maybe_commit()
        return self.cursor.lastrowid

    def update_lot_remaining_quantity(self, lot_id: int, remaining_quantity: float, 
                                    is_closed: bool = None) -> None:
        """更新批次剩余数量"""
        self._check_connection("update_lot_remaining_quantity")
        
        T = self.config.Tables.POSITION_LOTS
        F = self.config.Fields
        
        if is_closed is not None:
            sql = f"UPDATE {T} SET {F.PositionLots.REMAINING_QUANTITY} = ?, " \
                  f"{F.PositionLots.IS_CLOSED} = ?, {F.UPDATED_AT} = CURRENT_TIMESTAMP " \
                  f"WHERE {F.PositionLots.ID} = ?"
            params = (float(remaining_quantity), is_closed, lot_id)
        else:
            sql = f"UPDATE {T} SET {F.PositionLots.REMAINING_QUANTITY} = ?, " \
                  f"{F.UPDATED_AT} = CURRENT_TIMESTAMP WHERE {F.PositionLots.ID} = ?"
            params = (float(remaining_quantity), lot_id)
        
        self.cursor.execute(sql, params)
        self._maybe_commit()

    def get_position_lots(self, symbol: str = None, 
                         active_only: bool = True) -> List[Dict[str, Any]]:
        """获取持仓批次"""
        self._check_connection("get_position_lots")
        
        T = self.config.Tables.POSITION_LOTS
        F = self.config.Fields
        
        conditions = []
        params = []
        
        if symbol:
            conditions.append(f"{F.SYMBOL} = ?")
            params.append(symbol)
        
        if active_only:
            conditions.append(f"{F.PositionLots.IS_CLOSED} = 0")
        
        where_clause = " AND ".join(conditions)
        sql = f"SELECT * FROM {T} WHERE {where_clause} " \
              f"ORDER BY {F.SYMBOL}, {F.PositionLots.PURCHASE_DATE}, {F.PositionLots.ID}"
        
        self.cursor.execute(sql, params)
        rows = self.cursor.fetchall()
        
        columns = [description[0] for description in self.cursor.description]
        return [dict(zip(columns, row)) for row in rows]

    def get_position_lot_by_id(self, lot_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取特定批次"""
        self._check_connection("get_position_lot_by_id")
        
        T = self.config.Tables.POSITION_LOTS
        F = self.config.Fields
        
        sql = f"SELECT * FROM {T} WHERE {F.PositionLots.ID} = ?"
        
        self.cursor.execute(sql, (lot_id,))
        row = self.cursor.fetchone()
        
        if row:
            columns = [description[0] for description in self.cursor.description]
            return dict(zip(columns, row))
        return None

    def create_sale_allocation(self, allocation_data: Dict[str, Any]) -> int:
        """创建卖出分配记录"""
        self._check_connection("create_sale_allocation")
        
        T = self.config.Tables.SALE_ALLOCATIONS
        F = self.config.Fields
        
        fields = f"{F.SaleAllocations.SALE_TRANSACTION_ID}, {F.SaleAllocations.LOT_ID}, "                 f"{F.SaleAllocations.QUANTITY_SOLD}, {F.SaleAllocations.COST_BASIS}, "                 f"{F.SaleAllocations.SALE_PRICE}, {F.SaleAllocations.REALIZED_PNL}, {F.CREATED_AT}"
        
        placeholders = "?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP"
        
        sql = f"INSERT INTO {T} ({fields}) VALUES ({placeholders})"
        
        self.cursor.execute(
            sql,
            (
                allocation_data['sale_transaction_id'],
                allocation_data['lot_id'],
                float(allocation_data['quantity_sold']),
                float(allocation_data['cost_basis']),
                float(allocation_data['sale_price']),
                float(allocation_data['realized_pnl']),
            ),
        )
        
        self._maybe_commit()
        return self.cursor.lastrowid

    def get_sale_allocations(self, symbol: str = None,
                           sale_transaction_id: int = None) -> List[Dict[str, Any]]:
        """获取卖出分配记录"""
        self._check_connection("get_sale_allocations")
        
        T_SALE = self.config.Tables.SALE_ALLOCATIONS
        T_LOT = self.config.Tables.POSITION_LOTS
        T_TXN = self.config.Tables.TRANSACTIONS
        F = self.config.Fields
        
        # 联接查询获取完整信息
        sql = f"""
            SELECT sa.*, pl.{F.SYMBOL}, 
                   pl.{F.PositionLots.PURCHASE_DATE}, t.{F.Transactions.TRANSACTION_DATE}
            FROM {T_SALE} sa
            JOIN {T_LOT} pl ON sa.{F.SaleAllocations.LOT_ID} = pl.{F.PositionLots.ID}
            JOIN {T_TXN} t ON sa.{F.SaleAllocations.SALE_TRANSACTION_ID} = t.{F.Transactions.ID}
        """
        
        conditions = []
        params = []
        
        if symbol:
            conditions.append(f"pl.{F.SYMBOL} = ?")
            params.append(symbol)
        
        if sale_transaction_id:
            conditions.append(f"sa.{F.SaleAllocations.SALE_TRANSACTION_ID} = ?")
            params.append(sale_transaction_id)
        
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        
        sql += f" ORDER BY t.{F.Transactions.TRANSACTION_DATE} DESC, sa.{F.SaleAllocations.ID} DESC"
        
        self.cursor.execute(sql, params)
        rows = self.cursor.fetchall()
        
        columns = [description[0] for description in self.cursor.description]
        return [dict(zip(columns, row)) for row in rows]

    def get_daily_realized_pnl(self, symbol: str, date: str) -> float:
        """获取指定日期的已实现盈亏总额"""
        self._check_connection("get_daily_realized_pnl")
        
        T_SALE = self.config.Tables.SALE_ALLOCATIONS
        T_LOT = self.config.Tables.POSITION_LOTS
        T_TXN = self.config.Tables.TRANSACTIONS
        F = self.config.Fields
        
        sql = f"""
            SELECT SUM(sa.{F.SaleAllocations.REALIZED_PNL})
            FROM {T_SALE} sa
            JOIN {T_LOT} pl ON sa.{F.SaleAllocations.LOT_ID} = pl.{F.PositionLots.ID}
            JOIN {T_TXN} t ON sa.{F.SaleAllocations.SALE_TRANSACTION_ID} = t.{F.Transactions.ID}
            WHERE pl.{F.SYMBOL} = ? 
            AND t.{F.Transactions.TRANSACTION_DATE} = ?
        """
        
        self.cursor.execute(sql, (symbol, date))
        result = self.cursor.fetchone()
        
        return result[0] if result and result[0] is not None else 0.0

    def get_active_symbols_for_user(self) -> List[str]:
        """获取所有活跃持仓的股票代码列表"""
        self._check_connection("get_active_symbols_for_user")
        
        T = self.config.Tables.POSITION_LOTS
        F = self.config.Fields
        
        sql = f"""
            SELECT DISTINCT {F.SYMBOL}
            FROM {T}
            WHERE {F.PositionLots.IS_CLOSED} = 0
        """
        
        self.cursor.execute(sql)
        rows = self.cursor.fetchall()
        
        return [row[0] for row in rows]

    def get_position_lots_batch(self, symbols: List[str], 
                               active_only: bool = True, page_size: int = 1000, 
                               page_offset: int = 0) -> Dict[str, List[Dict[str, Any]]]:
        """
        批量获取多个股票的批次数据
        
        Args:
            symbols: 股票代码列表
            active_only: 是否只返回活跃批次
            page_size: 每页大小
            page_offset: 页偏移量
            
        Returns:
            Dict[str, List[Dict]]: {symbol: [lot_data...]}
        """
        self._check_connection("get_position_lots_batch")
        
        if not symbols:
            return {}
        
        T = self.config.Tables.POSITION_LOTS
        F = self.config.Fields
        
        # 构建IN子句的占位符
        symbol_placeholders = ','.join(['?' for _ in symbols])
        
        # 构建SQL查询
        conditions = [
            f"{F.SYMBOL} IN ({symbol_placeholders})"
        ]
        
        params = symbols
        
        if active_only:
            conditions.append(f"{F.PositionLots.IS_CLOSED} = 0")
        
        where_clause = " AND ".join(conditions)
        sql = f"""
            SELECT * FROM {T} 
            WHERE {where_clause}
            ORDER BY {F.SYMBOL}, {F.PositionLots.PURCHASE_DATE}
            LIMIT ? OFFSET ?
        """
        
        params.extend([page_size, page_offset])
        
        self.cursor.execute(sql, params)
        rows = self.cursor.fetchall()
        columns = [description[0] for description in self.cursor.description]
        lots_data = [dict(zip(columns, row)) for row in rows]
        
        # 按symbol分组
        result = {}
        for lot_data in lots_data:
            key = lot_data[F.SYMBOL]
            if key not in result:
                result[key] = []
            result[key].append(lot_data)
        
        return result

    def get_position_lots_paginated(self, symbol: str = None, 
                                   active_only: bool = True, page_size: int = 100, 
                                   page_offset: int = 0) -> tuple:
        """
        分页获取持仓批次
        
        Returns:
            tuple: (lots_data, total_count, has_more)
        """
        self._check_connection("get_position_lots_paginated")
        
        T = self.config.Tables.POSITION_LOTS
        F = self.config.Fields
        
        # 构建条件
        conditions = []
        params = []
        
        if symbol:
            conditions.append(f"{F.SYMBOL} = ?")
            params.append(symbol)
        
        if active_only:
            conditions.append(f"{F.PositionLots.IS_CLOSED} = 0")
        
        where_clause = " AND ".join(conditions)
        
        # 获取总数
        count_sql = f"SELECT COUNT(*) FROM {T} WHERE {where_clause}"
        self.cursor.execute(count_sql, params)
        total_count = self.cursor.fetchone()[0]
        
        # 获取分页数据
        data_sql = f"""
            SELECT * FROM {T} 
            WHERE {where_clause}
            ORDER BY {F.PositionLots.PURCHASE_DATE} DESC, {F.PositionLots.ID} DESC
            LIMIT ? OFFSET ?
        """
        
        params.extend([page_size, page_offset])
        self.cursor.execute(data_sql, params)
        rows = self.cursor.fetchall()
        columns = [description[0] for description in self.cursor.description]
        lots_data = [dict(zip(columns, row)) for row in rows]
        
        has_more = (page_offset + page_size) < total_count
        
        return lots_data, total_count, has_more

    def archive_closed_lots(self, older_than_days: int = 365) -> int:
        """
        归档老旧的已关闭批次
        
        Args:
            older_than_days: 归档超过多少天的已关闭批次
            
        Returns:
            int: 归档的批次数量
        """
        self._check_connection("archive_closed_lots")
        
        # 这里可以实现将老旧的已关闭批次移动到归档表
        # 为了简单起见，我们暂时只是标记它们
        T = self.config.Tables.POSITION_LOTS
        F = self.config.Fields
        
        cutoff_date = f"datetime('now', '-{older_than_days} days')"
        
        # 查找需要归档的批次
        select_sql = f"""
            SELECT COUNT(*) FROM {T}
            WHERE {F.PositionLots.IS_CLOSED} = 1 
            AND {F.PositionLots.REMAINING_QUANTITY} = 0
            AND {F.CREATED_AT} < {cutoff_date}
        """
        
        self.cursor.execute(select_sql)
        count = self.cursor.fetchone()[0]
        
        # 注意：在生产环境中，这里应该实际移动数据到归档表
        # 目前我们只是返回可归档的数量
        return count

    def get_active_symbols(self) -> List[str]:
        """获取所有活跃持仓的股票代码列表（别名方法）"""
        return self.get_active_symbols_for_user()
