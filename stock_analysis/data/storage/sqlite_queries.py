#!/usr/bin/env python3
"""
SQLite 查询方法
负责数据库查询操作和数据检索
"""

import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd

from ..models import BasicInfo, FinancialData, FinancialStatement, PriceData, StockData
from .config import StorageConfig, QueryBuilder


class SQLiteQueryManager:
    """SQLite 查询管理器"""
    
    def __init__(self, connection: sqlite3.Connection, cursor: sqlite3.Cursor):
        """
        初始化查询管理器
        
        Args:
            connection: SQLite 数据库连接
            cursor: SQLite 游标
        """
        self.connection = connection
        self.cursor = cursor
        self.config = StorageConfig()
        self.logger = logging.getLogger(__name__)
    
    def get_stock_data(
        self, symbol: str, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> Optional[StockData]:
        """获取股票数据"""
        try:
            # 使用查询构建器构建查询
            builder = QueryBuilder(self.config.Tables.STOCK_PRICES)
            builder.where(f"{self.config.Fields.SYMBOL} = ?", symbol)
            
            if start_date:
                builder.where(f"{self.config.Fields.StockPrices.DATE} >= ?", start_date)
            
            if end_date:
                builder.where(f"{self.config.Fields.StockPrices.DATE} <= ?", end_date)
            
            builder.order(self.config.Fields.StockPrices.DATE)
            
            # 构建字段列表
            F = self.config.Fields.StockPrices
            fields = f"{F.DATE}, {F.OPEN}, {F.HIGH}, {F.LOW}, {F.CLOSE}, {F.VOLUME}, {F.ADJ_CLOSE}"
            
            sql, params = builder.build_select(fields)
            df = pd.read_sql_query(sql, self.connection, params=params)

            if df.empty:
                return None

            # 构建价格数据
            price_data = PriceData(
                dates=df[F.DATE].tolist(),
                open=df[F.OPEN].tolist(),
                high=df[F.HIGH].tolist(),
                low=df[F.LOW].tolist(),
                close=df[F.CLOSE].tolist(),
                volume=df[F.VOLUME].tolist(),
                adj_close=df[F.ADJ_CLOSE].tolist(),
            )

            # 计算统计数据
            from ..models import calculate_summary_stats
            summary_stats = calculate_summary_stats(price_data.close, price_data.volume)

            return StockData(
                symbol=symbol,
                start_date=start_date or df[F.DATE].min(),
                end_date=end_date or df[F.DATE].max(),
                data_points=len(df),
                price_data=price_data,
                summary_stats=summary_stats,
                downloaded_at=datetime.now().isoformat(),
                data_source="database",
            )

        except Exception as e:
            self.logger.error(f"❌ 获取股票数据失败 {symbol}: {e}")
            return None
    
    def get_financial_metrics(
        self, symbol: str, statement_type: str, start_period: Optional[str] = None, end_period: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """获取财务指标数据"""
        try:
            # 使用配置类构建查询
            table_name = self.config.get_table_for_statement_type(statement_type)
            F = self.config.Fields
            
            builder = QueryBuilder(table_name)
            builder.where(f"{F.SYMBOL} = ?", symbol)
            
            if start_period:
                builder.where(f"{F.FinancialStatement.PERIOD} >= ?", start_period)
            
            if end_period:
                builder.where(f"{F.FinancialStatement.PERIOD} <= ?", end_period)
            
            builder.order(f"{F.FinancialStatement.PERIOD} DESC, {F.FinancialStatement.METRIC_NAME}")
            
            # 构建字段列表
            fields = f"{F.SYMBOL}, {F.FinancialStatement.PERIOD}, {F.FinancialStatement.METRIC_NAME}, {F.FinancialStatement.METRIC_VALUE}, {F.CREATED_AT}"
            
            sql, params = builder.build_select(fields)
            df = pd.read_sql_query(sql, self.connection, params=params)
            
            return df if not df.empty else None
            
        except Exception as e:
            self.logger.error(f"❌ 获取{statement_type}指标失败 {symbol}: {e}")
            return None
    
    def get_financial_data(self, symbol: str) -> Optional[FinancialData]:
        """获取财务数据"""
        try:
            # 获取基本信息
            T = self.config.Tables
            F = self.config.Fields
            
            basic_info_sql = f"SELECT * FROM {T.STOCKS} WHERE {F.SYMBOL} = ?"
            basic_df = pd.read_sql_query(basic_info_sql, self.connection, params=[symbol])

            if basic_df.empty:
                return None

            basic_info = BasicInfo(
                company_name=basic_df.iloc[0][F.Stocks.COMPANY_NAME] or "",
                sector=basic_df.iloc[0][F.Stocks.SECTOR] or "",
                industry=basic_df.iloc[0][F.Stocks.INDUSTRY] or "",
                market_cap=basic_df.iloc[0][F.Stocks.MARKET_CAP] or 0,
                employees=basic_df.iloc[0][F.Stocks.EMPLOYEES] or 0,
                description=basic_df.iloc[0][F.Stocks.DESCRIPTION] or "",
            )

            # 从独立的财务表获取数据并构建 FinancialStatement 对象
            statements = {}
            
            # 使用配置类获取财务表映射
            statement_tables = self.config.Tables.get_financial_tables()
            
            for stmt_type, table_name in statement_tables.items():
                try:
                    # 获取该表的所有数据
                    sql = f"SELECT {F.FinancialStatement.PERIOD}, {F.FinancialStatement.METRIC_NAME}, {F.FinancialStatement.METRIC_VALUE} FROM {table_name} WHERE {F.SYMBOL} = ? ORDER BY {F.FinancialStatement.PERIOD} DESC"
                    df = pd.read_sql_query(sql, self.connection, params=[symbol])
                    
                    if not df.empty:
                        # 重构数据为 FinancialStatement 格式
                        periods = sorted(df[F.FinancialStatement.PERIOD].unique(), reverse=True)
                        items = {}
                        
                        for metric_name in df[F.FinancialStatement.METRIC_NAME].unique():
                            metric_data = df[df[F.FinancialStatement.METRIC_NAME] == metric_name]
                            values = []
                            for period in periods:
                                period_data = metric_data[metric_data[F.FinancialStatement.PERIOD] == period]
                                if not period_data.empty:
                                    values.append(period_data.iloc[0][F.FinancialStatement.METRIC_VALUE])
                                else:
                                    values.append(None)
                            items[metric_name] = values
                        
                        statements[stmt_type] = FinancialStatement(
                            statement_type=stmt_type,
                            periods=periods,
                            items=items
                        )
                        
                except Exception as e:
                    self.logger.warning(f"获取{stmt_type}数据失败: {e}")
                    continue

            return FinancialData(
                symbol=symbol,
                basic_info=basic_info,
                financial_statements=statements,
                downloaded_at=datetime.now().isoformat(),
            )

        except Exception as e:
            self.logger.error(f"❌ 获取财务数据失败 {symbol}: {e}")
            return None
    
    def get_last_update_date(self, symbol: str) -> Optional[str]:
        """获取最后更新日期"""
        try:
            sql = f"SELECT MAX({self.config.Fields.StockPrices.DATE}) FROM {self.config.Tables.STOCK_PRICES} WHERE {self.config.Fields.SYMBOL} = ?"
            result = self.cursor.execute(sql, (symbol,)).fetchone()
            return result[0] if result and result[0] else None
        except Exception as e:
            self.logger.error(f"❌ 获取最后更新日期失败 {symbol}: {e}")
            return None
    
    def get_last_financial_period(self, symbol: str) -> Optional[str]:
        """获取最近财务期间"""
        try:
            T = self.config.Tables
            F = self.config.Fields
            
            # 使用UNION查询获取所有表的最新期间
            sql = f"""
            SELECT MAX(period) as max_period FROM (
                SELECT MAX({F.FinancialStatement.PERIOD}) as period FROM {T.INCOME_STATEMENT} WHERE {F.SYMBOL} = ?
                UNION ALL
                SELECT MAX({F.FinancialStatement.PERIOD}) as period FROM {T.BALANCE_SHEET} WHERE {F.SYMBOL} = ?
                UNION ALL
                SELECT MAX({F.FinancialStatement.PERIOD}) as period FROM {T.CASH_FLOW} WHERE {F.SYMBOL} = ?
            )
            """
            result = self.cursor.execute(sql, (symbol, symbol, symbol)).fetchone()
            return result[0] if result and result[0] else None
        except Exception as e:
            self.logger.error(f"❌ 获取最近财务期间失败 {symbol}: {e}")
            return None
    
    def get_existing_symbols(self) -> List[str]:
        """获取已存储的股票代码列表"""
        try:
            sql = f"SELECT DISTINCT {self.config.Fields.SYMBOL} FROM {self.config.Tables.STOCKS} ORDER BY {self.config.Fields.SYMBOL}"
            result = self.cursor.execute(sql).fetchall()
            return [row[0] for row in result]
        except Exception as e:
            self.logger.error(f"❌ 获取股票代码列表失败: {e}")
            return []