#!/usr/bin/env python3
"""
SQLite 存储实现
基于原有 database.py 的 SQLite 实现重构
"""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd

from ..models import (
    BasicInfo,
    DataQuality,
    FinancialData,
    FinancialStatement,
    PriceData,
    StockData,
)
from .base import BaseStorage, StorageError


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
        self.connect()

    def connect(self) -> None:
        """建立数据库连接"""
        try:
            # 确保数据库目录存在（统一使用 pathlib）
            dbp = Path(self.db_path)
            if dbp.parent:
                dbp.parent.mkdir(parents=True, exist_ok=True)
            self.connection = sqlite3.connect(str(dbp), check_same_thread=False)
            if self.connection is None:
                raise Exception("Failed to create database connection")
            self.connection.execute("PRAGMA foreign_keys = ON")
            self.cursor = self.connection.cursor()
            if not self._schema_exists():
                self._create_tables()
            self.logger.info(f"✅ SQLite 数据库连接成功: {self.db_path}")
        except Exception as e:
            self.connection = None
            self.cursor = None
            raise StorageError(f"SQLite 连接失败: {e}", "connect")

    def close(self) -> None:
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            self.logger.info("📴 SQLite 数据库连接已关闭")

    def _check_connection(self, operation_name: str = "operation") -> None:
        """检查数据库连接是否可用"""
        if self.cursor is None or self.connection is None:
            raise StorageError(
                f"Database connection not available for {operation_name}", operation_name
            )

    def _create_tables(self) -> None:
        """创建或修复数据库表结构（仅在缺失时执行）"""
        self._check_connection("create_tables")
        self.logger.info("📊 创建/修复数据库表结构...")

        # 股票基本信息表
        stocks_table = """
        CREATE TABLE IF NOT EXISTS stocks (
            symbol TEXT PRIMARY KEY,
            company_name TEXT,
            sector TEXT,
            industry TEXT,
            market_cap REAL,
            employees INTEGER,
            description TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """

        # 股票价格数据表
        stock_prices_table = """
        CREATE TABLE IF NOT EXISTS stock_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            date TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            adj_close REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (symbol) REFERENCES stocks (symbol),
            UNIQUE(symbol, date)
        )
        """

        # 财务报表数据表
        financial_statements_table = """
        CREATE TABLE IF NOT EXISTS financial_statements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            statement_type TEXT,
            period TEXT,
            data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (symbol) REFERENCES stocks (symbol),
            UNIQUE(symbol, statement_type, period)
        )
        """

        # 下载日志表
        download_logs_table = """
        CREATE TABLE IF NOT EXISTS download_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            download_type TEXT,
            status TEXT,
            data_points INTEGER,
            error_message TEXT,
            details TEXT,
            download_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """

        tables = [
            stocks_table,
            stock_prices_table,
            financial_statements_table,
            download_logs_table,
        ]

        for table in tables:
            self.cursor.execute(table)  # type: ignore

        # 创建索引提高查询性能
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_stock_prices_symbol_date ON stock_prices (symbol, date)",
            "CREATE INDEX IF NOT EXISTS idx_financial_symbol_type ON financial_statements (symbol, statement_type)",
            "CREATE INDEX IF NOT EXISTS idx_download_logs_symbol ON download_logs (symbol)",
        ]

        for index in indexes:
            self.cursor.execute(index)  # type: ignore

        # 迁移：如旧表缺少 details 列，补充之
        try:
            self.cursor.execute("PRAGMA table_info(download_logs)")  # type: ignore
            cols = [row[1] for row in self.cursor.fetchall()]  # type: ignore
            if 'details' not in cols:
                self.cursor.execute("ALTER TABLE download_logs ADD COLUMN details TEXT")  # type: ignore
        except Exception:
            pass

        # 视图：提供与规范化命名一致的价格视图（兼容查询）
        try:
            self.cursor.execute(  # type: ignore
                "CREATE VIEW IF NOT EXISTS price_bars AS "
                "SELECT symbol, date, open, high, low, close, adj_close, volume, created_at "
                "FROM stock_prices"
            )
        except Exception:
            pass

        self.connection.commit()  # type: ignore
        self.logger.info("✅ 数据库表结构就绪")

    def _schema_exists(self) -> bool:
        """检查核心表是否已存在，全部存在则认为已初始化"""
        try:
            if self.cursor is None or self.connection is None:
                return False
            required = [
                'stocks',
                'stock_prices',
                'financial_statements',
                'download_logs',
            ]
            placeholders = ",".join(["?"] * len(required))
            sql = f"SELECT name FROM sqlite_master WHERE type='table' AND name IN ({placeholders})"
            rows = self.cursor.execute(sql, required).fetchall()
            return len(rows) == len(required)
        except Exception:
            return False

    def store_stock_data(self, symbol: str, stock_data: Union[StockData, Dict]) -> bool:
        """存储股票数据"""
        self._check_connection("store_stock_data")
        try:
            if isinstance(stock_data, StockData):
                # 确保股票记录存在（必须先于价格数据）
                basic_info = getattr(stock_data, 'basic_info', None)
                if basic_info:
                    self._store_basic_info(symbol, basic_info)
                else:
                    # 如果没有基本信息，创建一个空的记录以满足外键约束
                    self._ensure_stock_exists(symbol)

                # 存储价格数据
                self._store_price_data(symbol, stock_data.price_data)

            elif isinstance(stock_data, dict):
                # 从字典存储
                if 'basic_info' in stock_data:
                    self._store_basic_info(symbol, stock_data['basic_info'])
                else:
                    # 确保股票记录存在
                    self._ensure_stock_exists(symbol)

                if 'price_data' in stock_data:
                    price_data = PriceData.from_dict(stock_data['price_data'])
                    self._store_price_data(symbol, price_data)

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
                for (
                    stmt_type,
                    statement,
                ) in financial_data.financial_statements.items():
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
        """将数据质量评估作为下载日志的一部分进行记录（details JSON）。"""
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
            # 降级为写失败日志
            try:
                self._log_download(symbol, "quality", "failed", 0, str(e))
            except Exception:
                pass
            return False

    def get_stock_data(
        self, symbol: str, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> Optional[StockData]:
        """获取股票数据"""
        self._check_connection("get_stock_data")
        try:
            # 构建查询条件
            where_conditions = ["symbol = ?"]
            params = [symbol]

            if start_date:
                where_conditions.append("date >= ?")
                params.append(start_date)

            if end_date:
                where_conditions.append("date <= ?")
                params.append(end_date)

            sql = f"""
            SELECT date, open, high, low, close, volume, adj_close
            FROM stock_prices
            WHERE {' AND '.join(where_conditions)}
            ORDER BY date
            """

            df = pd.read_sql_query(sql, self.connection, params=params)

            if df.empty:
                return None

            # 构建价格数据
            price_data = PriceData(
                dates=df['date'].tolist(),
                open=df['open'].tolist(),
                high=df['high'].tolist(),
                low=df['low'].tolist(),
                close=df['close'].tolist(),
                volume=df['volume'].tolist(),
                adj_close=df['adj_close'].tolist(),
            )

            # 计算统计数据
            from ..models import calculate_summary_stats

            summary_stats = calculate_summary_stats(price_data.close, price_data.volume)

            return StockData(
                symbol=symbol,
                start_date=start_date or df['date'].min(),
                end_date=end_date or df['date'].max(),
                data_points=len(df),
                price_data=price_data,
                summary_stats=summary_stats,
                downloaded_at=datetime.now().isoformat(),
                data_source="database",
            )

        except Exception as e:
            self.logger.error(f"❌ 获取股票数据失败 {symbol}: {e}")
            return None

    def get_financial_data(self, symbol: str) -> Optional[FinancialData]:
        """获取财务数据"""
        self._check_connection("get_financial_data")
        try:
            # 获取基本信息
            basic_info_sql = "SELECT * FROM stocks WHERE symbol = ?"
            basic_df = pd.read_sql_query(basic_info_sql, self.connection, params=[symbol])

            if basic_df.empty:
                return None

            basic_info = BasicInfo(
                company_name=basic_df.iloc[0]['company_name'] or "",
                sector=basic_df.iloc[0]['sector'] or "",
                industry=basic_df.iloc[0]['industry'] or "",
                market_cap=basic_df.iloc[0]['market_cap'] or 0,
                employees=basic_df.iloc[0]['employees'] or 0,
                description=basic_df.iloc[0]['description'] or "",
            )

            # 获取财务报表
            financial_sql = (
                "SELECT statement_type, period, data FROM financial_statements WHERE symbol = ?"
            )
            financial_df = pd.read_sql_query(financial_sql, self.connection, params=[symbol])

            statements = {}
            for _, row in financial_df.iterrows():
                stmt_data = json.loads(row['data'])
                statements[row['statement_type']] = FinancialStatement.from_dict(stmt_data)

            return FinancialData(
                symbol=symbol,
                basic_info=basic_info,
                financial_statements=statements,
                downloaded_at=datetime.now().isoformat(),
            )

        except Exception as e:
            self.logger.error(f"❌ 获取财务数据失败 {symbol}: {e}")
            return None

    def get_existing_symbols(self) -> List[str]:
        """获取已存储的股票代码列表"""
        try:
            self._check_connection("get_existing_symbols")
            sql = "SELECT DISTINCT symbol FROM stocks ORDER BY symbol"
            result = self.cursor.execute(sql).fetchall()  # type: ignore
            return [row[0] for row in result]
        except Exception as e:
            self.logger.error(f"❌ 获取股票代码列表失败: {e}")
            return []

    def get_last_update_date(self, symbol: str) -> Optional[str]:
        """获取最后更新日期"""
        self._check_connection("get_last_update_date")
        try:
            sql = "SELECT MAX(date) FROM stock_prices WHERE symbol = ?"
            result = self.cursor.execute(sql, (symbol,)).fetchone()  # type: ignore
            return result[0] if result and result[0] else None
        except Exception as e:
            self.logger.error(f"❌ 获取最后更新日期失败 {symbol}: {e}")
            return None

    def get_last_financial_period(self, symbol: str) -> Optional[str]:
        """获取该股票财务报表的最近期间（period）"""
        self._check_connection("get_last_financial_period")
        try:
            sql = "SELECT MAX(period) FROM financial_statements WHERE symbol = ?"
            result = self.cursor.execute(sql, (symbol,)).fetchone()  # type: ignore
            return result[0] if result and result[0] else None
        except Exception as e:
            self.logger.error(f"❌ 获取最近财务期间失败 {symbol}: {e}")
            return None

    def _store_basic_info(self, symbol: str, basic_info: Union[BasicInfo, Dict]) -> None:
        """存储股票基本信息"""
        self._check_connection("_store_basic_info")
        if isinstance(basic_info, BasicInfo):
            data = basic_info.to_dict()
        else:
            data = basic_info

        sql = """
        INSERT OR REPLACE INTO stocks
        (symbol, company_name, sector, industry, market_cap, employees, description, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """

        self.cursor.execute(  # type: ignore
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
        self.connection.commit()  # type: ignore

    def _ensure_stock_exists(self, symbol: str) -> None:
        """确保股票记录存在（用空值创建）"""
        self._check_connection("_ensure_stock_exists")
        sql = """
        INSERT OR IGNORE INTO stocks
        (symbol, company_name, sector, industry, market_cap, employees, description, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """

        self.cursor.execute(sql, (symbol, '', '', '', 0, 0, '', datetime.now().isoformat()))  # type: ignore
        self.connection.commit()  # type: ignore

    def _store_price_data(self, symbol: str, price_data: PriceData) -> None:
        """存储价格数据"""
        self._check_connection("_store_price_data")
        for i, date in enumerate(price_data.dates):
            sql = """
            INSERT OR REPLACE INTO stock_prices
            (symbol, date, open, high, low, close, volume, adj_close)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """

            self.cursor.execute(  # type: ignore
                sql,
                (
                    symbol,
                    date,
                    price_data.open[i],
                    price_data.high[i],
                    price_data.low[i],
                    price_data.close[i],
                    price_data.volume[i],
                    price_data.adj_close[i],
                ),
            )

        self.connection.commit()  # type: ignore

    def _store_financial_statement(
        self, symbol: str, stmt_type: str, statement: FinancialStatement
    ) -> None:
        """存储财务报表"""
        self._check_connection("_store_financial_statement")
        for period in statement.periods:
            sql = """
            INSERT OR REPLACE INTO financial_statements
            (symbol, statement_type, period, data)
            VALUES (?, ?, ?, ?)
            """

            # 获取该期间的数据
            period_data = {}
            for item_name, values in statement.items.items():
                try:
                    period_index = statement.periods.index(period)
                    if period_index < len(values):
                        period_data[item_name] = values[period_index]
                except (ValueError, IndexError):
                    period_data[item_name] = None

            stmt_data = {
                'statement_type': stmt_type,
                'periods': [period],
                'items': {k: [v] for k, v in period_data.items()},
            }

            self.cursor.execute(sql, (symbol, stmt_type, period, json.dumps(stmt_data)))  # type: ignore

        self.connection.commit()  # type: ignore

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
        sql = """
        INSERT INTO download_logs
        (symbol, download_type, status, data_points, error_message, details)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        details_json = json.dumps(details, ensure_ascii=False) if details else None
        self.cursor.execute(  # type: ignore
            sql,
            (
                symbol,
                download_type,
                status,
                data_points,
                error_message,
                details_json,
            ),
        )
        self.connection.commit()  # type: ignore
