#!/usr/bin/env python3
"""
股票数据库模块
使用SQLite/PostgreSQL存储股票价格数据和财务报表
"""

import sqlite3
import pandas as pd
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging
import os

class StockDatabase:
    def __init__(self, db_path: str = "stock_data.db", db_type: str = "sqlite"):
        """
        初始化股票数据库
        
        Args:
            db_path: 数据库路径或连接字符串
            db_type: 数据库类型 ('sqlite' 或 'postgresql')
        """
        self.db_path = db_path
        self.db_type = db_type
        self.logger = logging.getLogger(__name__)
        
        if db_type == "sqlite":
            self.connection = sqlite3.connect(db_path, check_same_thread=False)
            self.connection.execute("PRAGMA foreign_keys = ON")
        else:
            # PostgreSQL 支持 (需要安装 psycopg2)
            try:
                import psycopg2
                self.connection = psycopg2.connect(db_path)
            except ImportError:
                raise ImportError("需要安装 psycopg2 来使用 PostgreSQL")
        
        self.cursor = self.connection.cursor()
        self._create_tables()
    
    def _create_tables(self):
        """创建数据库表结构"""
        self.logger.info("📊 创建数据库表结构...")
        
        # 股票基本信息表
        stocks_table = """
        CREATE TABLE IF NOT EXISTS stocks (
            symbol TEXT PRIMARY KEY,
            company_name TEXT,
            sector TEXT,
            industry TEXT,
            market_cap INTEGER,
            employees INTEGER,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        # 股票价格数据表
        stock_prices_table = """
        CREATE TABLE IF NOT EXISTS stock_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            date DATE,
            open_price REAL,
            high_price REAL,
            low_price REAL,
            close_price REAL,
            adj_close REAL,
            volume INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(symbol, date)
        )
        """
        
        # 财务报表数据表
        financial_statements_table = """
        CREATE TABLE IF NOT EXISTS financial_statements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            statement_type TEXT,
            period_date DATE,
            item_name TEXT,
            value REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(symbol, statement_type, period_date, item_name)
        )
        """
        
        # 数据下载日志表
        download_logs_table = """
        CREATE TABLE IF NOT EXISTS download_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            download_type TEXT,
            status TEXT,
            data_points INTEGER,
            error_message TEXT,
            download_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        # 数据质量评估表
        data_quality_table = """
        CREATE TABLE IF NOT EXISTS data_quality (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            stock_data_available BOOLEAN,
            financial_data_available BOOLEAN,
            data_completeness REAL,
            quality_grade TEXT,
            issues TEXT,
            assessment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        tables = [
            stocks_table,
            stock_prices_table, 
            financial_statements_table,
            download_logs_table,
            data_quality_table
        ]
        
        for table in tables:
            self.cursor.execute(table)
        
        # 创建索引提高查询性能
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_stock_prices_symbol_date ON stock_prices (symbol, date)",
            "CREATE INDEX IF NOT EXISTS idx_financial_symbol_type ON financial_statements (symbol, statement_type)",
            "CREATE INDEX IF NOT EXISTS idx_download_logs_symbol ON download_logs (symbol)",
        ]
        
        for index in indexes:
            self.cursor.execute(index)
        
        self.connection.commit()
        self.logger.info("✅ 数据库表结构创建完成")
    
    def store_stock_basic_info(self, symbol: str, basic_info: Dict):
        """存储股票基本信息"""
        try:
            sql = """
            INSERT OR REPLACE INTO stocks 
            (symbol, company_name, sector, industry, market_cap, employees, description, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            values = (
                symbol,
                basic_info.get('company_name', ''),
                basic_info.get('sector', ''),
                basic_info.get('industry', ''),
                basic_info.get('market_cap', 0),
                basic_info.get('employees', 0),
                basic_info.get('description', ''),
                datetime.now()
            )
            
            self.cursor.execute(sql, values)
            self.connection.commit()
            self.logger.info(f"✅ {symbol} 基本信息存储完成")
            
        except Exception as e:
            self.logger.error(f"存储 {symbol} 基本信息失败: {str(e)}")
            raise
    
    def store_stock_prices(self, symbol: str, price_data: Dict, incremental: bool = True):
        """存储股票价格数据"""
        try:
            if not incremental:
                # 全量更新：清除已存在的数据
                self.cursor.execute("DELETE FROM stock_prices WHERE symbol = ?", (symbol,))
            
            # 插入新数据（使用 INSERT OR REPLACE 支持增量更新）
            sql = """
            INSERT OR REPLACE INTO stock_prices 
            (symbol, date, open_price, high_price, low_price, close_price, adj_close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            dates = price_data['dates']
            opens = price_data['open']
            highs = price_data['high']
            lows = price_data['low']
            closes = price_data['close']
            adj_closes = price_data['adj_close']
            volumes = price_data['volume']
            
            data_to_insert = []
            for i in range(len(dates)):
                data_to_insert.append((
                    symbol,
                    dates[i],
                    opens[i],
                    highs[i], 
                    lows[i],
                    closes[i],
                    adj_closes[i],
                    volumes[i]
                ))
            
            self.cursor.executemany(sql, data_to_insert)
            self.connection.commit()
            
            update_type = "增量更新" if incremental else "全量更新"
            self.logger.info(f"✅ {symbol} 价格数据{update_type}完成: {len(data_to_insert)} 条记录")
            
        except Exception as e:
            self.logger.error(f"存储 {symbol} 价格数据失败: {str(e)}")
            raise
    
    def store_financial_statements(self, symbol: str, financial_data: Dict):
        """存储财务报表数据"""
        try:
            # 清除已存在的财务数据
            self.cursor.execute("DELETE FROM financial_statements WHERE symbol = ?", (symbol,))
            
            statements = financial_data.get('financial_statements', {})
            
            sql = """
            INSERT INTO financial_statements 
            (symbol, statement_type, period_date, item_name, value)
            VALUES (?, ?, ?, ?, ?)
            """
            
            data_to_insert = []
            
            for statement_type, statement_data in statements.items():
                if 'error' not in statement_data:
                    periods = statement_data.get('periods', [])
                    items = statement_data.get('items', {})
                    
                    for item_name, values in items.items():
                        for i, period in enumerate(periods):
                            if i < len(values) and values[i] is not None:
                                data_to_insert.append((
                                    symbol,
                                    statement_type,
                                    period,
                                    item_name,
                                    values[i]
                                ))
            
            if data_to_insert:
                self.cursor.executemany(sql, data_to_insert)
                self.connection.commit()
                self.logger.info(f"✅ {symbol} 财务数据存储完成: {len(data_to_insert)} 条记录")
            else:
                self.logger.warning(f"⚠️ {symbol} 没有有效的财务数据可存储")
                
        except Exception as e:
            self.logger.error(f"存储 {symbol} 财务数据失败: {str(e)}")
            raise
    
    def store_download_log(self, symbol: str, download_type: str, status: str, 
                          data_points: int = 0, error_message: str = None):
        """记录数据下载日志"""
        try:
            sql = """
            INSERT INTO download_logs 
            (symbol, download_type, status, data_points, error_message)
            VALUES (?, ?, ?, ?, ?)
            """
            
            self.cursor.execute(sql, (symbol, download_type, status, data_points, error_message))
            self.connection.commit()
            
        except Exception as e:
            self.logger.error(f"记录 {symbol} 下载日志失败: {str(e)}")
    
    def store_data_quality(self, symbol: str, quality_data: Dict):
        """存储数据质量评估"""
        try:
            # 删除旧的质量评估记录
            self.cursor.execute("DELETE FROM data_quality WHERE symbol = ?", (symbol,))
            
            sql = """
            INSERT INTO data_quality 
            (symbol, stock_data_available, financial_data_available, data_completeness, 
             quality_grade, issues)
            VALUES (?, ?, ?, ?, ?, ?)
            """
            
            issues_json = json.dumps(quality_data.get('issues', []), ensure_ascii=False)
            
            values = (
                symbol,
                quality_data.get('stock_data_available', False),
                quality_data.get('financial_data_available', False),
                quality_data.get('data_completeness', 0.0),
                quality_data.get('quality_grade', ''),
                issues_json
            )
            
            self.cursor.execute(sql, values)
            self.connection.commit()
            self.logger.info(f"✅ {symbol} 数据质量评估存储完成")
            
        except Exception as e:
            self.logger.error(f"存储 {symbol} 数据质量评估失败: {str(e)}")
            raise
    
    def store_comprehensive_data(self, symbol: str, data: Dict):
        """存储综合数据（股票+财务）"""
        try:
            is_incremental = data.get('stock_data', {}).get('incremental_update', False)
            self.logger.info(f"💾 开始存储 {symbol} 的综合数据 ({'增量模式' if is_incremental else '全量模式'})")
            
            # 确保股票基本信息存在（避免外键约束问题）
            self.store_stock_basic_info(symbol, {
                'company_name': f'{symbol} Inc.',
                'sector': 'Unknown',
                'industry': 'Unknown',
                'market_cap': 0,
                'employees': 0,
                'description': ''
            })
            
            # 存储股票基本信息（如果有财务数据）
            if 'financial_data' in data and 'error' not in data['financial_data']:
                basic_info = data['financial_data'].get('basic_info', {})
                if basic_info:
                    self.store_stock_basic_info(symbol, basic_info)
            
            # 存储股票价格数据
            if 'stock_data' in data and 'error' not in data['stock_data']:
                price_data = data['stock_data'].get('price_data', {})
                # 检查是否有新数据需要存储
                if price_data and data['stock_data'].get('data_points', 0) > 0:
                    self.store_stock_prices(symbol, price_data, incremental=is_incremental)
                    
                    # 记录价格数据下载日志
                    self.store_download_log(
                        symbol, 'stock_prices', 'success', 
                        data['stock_data'].get('data_points', 0)
                    )
                elif data['stock_data'].get('no_new_data'):
                    self.logger.info(f"📊 {symbol} 无新数据需要更新")
            else:
                # 记录失败日志
                error_msg = data.get('stock_data', {}).get('error', '未知错误')
                self.store_download_log(symbol, 'stock_prices', 'failed', 0, error_msg)
            
            # 存储财务数据
            if 'financial_data' in data and 'error' not in data['financial_data']:
                self.store_financial_statements(symbol, data['financial_data'])
                
                # 记录财务数据下载日志
                statements_count = len(data['financial_data'].get('financial_statements', {}))
                self.store_download_log(symbol, 'financial_data', 'success', statements_count)
            else:
                # 记录失败日志，但仅在有stock基本信息时
                if 'financial_data' in data:
                    error_msg = data.get('financial_data', {}).get('error', '未知错误')
                    self.store_download_log(symbol, 'financial_data', 'failed', 0, error_msg)
            
            # 存储数据质量评估
            if 'data_quality' in data:
                self.store_data_quality(symbol, data['data_quality'])
            
            self.logger.info(f"✅ {symbol} 综合数据存储完成")
            
        except Exception as e:
            self.logger.error(f"存储 {symbol} 综合数据失败: {str(e)}")
            raise
    
    def get_stock_prices(self, symbol: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """获取股票价格数据"""
        sql = "SELECT * FROM stock_prices WHERE symbol = ?"
        params = [symbol]
        
        if start_date:
            sql += " AND date >= ?"
            params.append(start_date)
        
        if end_date:
            sql += " AND date <= ?"
            params.append(end_date)
        
        sql += " ORDER BY date"
        
        return pd.read_sql_query(sql, self.connection, params=params)
    
    def get_financial_data(self, symbol: str, statement_type: str = None) -> pd.DataFrame:
        """获取财务数据"""
        sql = "SELECT * FROM financial_statements WHERE symbol = ?"
        params = [symbol]
        
        if statement_type:
            sql += " AND statement_type = ?"
            params.append(statement_type)
        
        sql += " ORDER BY period_date DESC, item_name"
        
        return pd.read_sql_query(sql, self.connection, params=params)
    
    def get_data_quality_report(self) -> pd.DataFrame:
        """获取数据质量报告"""
        sql = """
        SELECT s.symbol, s.company_name, s.sector,
               dq.quality_grade, dq.data_completeness,
               dq.stock_data_available, dq.financial_data_available,
               dq.assessment_date
        FROM stocks s
        LEFT JOIN data_quality dq ON s.symbol = dq.symbol
        ORDER BY dq.data_completeness DESC
        """
        
        return pd.read_sql_query(sql, self.connection)
    
    def get_download_summary(self) -> pd.DataFrame:
        """获取下载摘要统计"""
        sql = """
        SELECT 
            symbol,
            COUNT(*) as total_downloads,
            SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful_downloads,
            SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_downloads,
            MAX(download_timestamp) as last_download
        FROM download_logs
        GROUP BY symbol
        ORDER BY last_download DESC
        """
        
        return pd.read_sql_query(sql, self.connection)
    
    def get_existing_symbols(self) -> List[str]:
        """获取数据库中已存在的股票代码列表"""
        try:
            sql = "SELECT DISTINCT symbol FROM stock_prices ORDER BY symbol"
            result = self.cursor.execute(sql).fetchall()
            return [row[0] for row in result]
        except Exception as e:
            self.logger.error(f"获取已存在股票列表失败: {str(e)}")
            return []
    
    def get_last_update_date(self, symbol: str) -> Optional[str]:
        """获取指定股票的最后更新日期"""
        try:
            sql = "SELECT MAX(date) FROM stock_prices WHERE symbol = ?"
            result = self.cursor.execute(sql, (symbol,)).fetchone()
            
            if result and result[0]:
                return result[0]
            return None
        except Exception as e:
            self.logger.error(f"获取 {symbol} 最后更新日期失败: {str(e)}")
            return None
    
    def backup_database(self, backup_path: str):
        """备份数据库"""
        if self.db_type == "sqlite":
            import shutil
            shutil.copy2(self.db_path, backup_path)
            self.logger.info(f"✅ 数据库备份到: {backup_path}")
        else:
            self.logger.warning("PostgreSQL 备份需要使用 pg_dump 工具")
    
    def close(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            self.logger.info("📊 数据库连接已关闭")

if __name__ == "__main__":
    # 测试数据库功能
    logging.basicConfig(level=logging.INFO)
    
    print("🗄️ 股票数据库测试")
    print("=" * 40)
    
    # 创建数据库
    db = StockDatabase("test_stock.db")
    
    # 测试数据
    test_symbol = "AAPL"
    test_basic_info = {
        'company_name': 'Apple Inc.',
        'sector': 'Technology',
        'industry': 'Consumer Electronics',
        'market_cap': 3000000000000,
        'employees': 164000
    }
    
    # 存储测试数据
    db.store_stock_basic_info(test_symbol, test_basic_info)
    
    print("✅ 数据库测试完成")
    
    # 关闭数据库
    db.close()