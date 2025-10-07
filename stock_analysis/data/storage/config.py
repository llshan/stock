#!/usr/bin/env python3
"""
存储层配置定义
提供统一的表名、字段名和SQL模板管理
"""

from typing import Dict, List


class StorageConfig:
    """存储层配置类 - 统一管理表名、字段名和SQL模板"""
    
    # ============= 表名定义 =============
    class Tables:
        STOCKS = "stocks"
        STOCK_PRICES = "stock_prices"
        INCOME_STATEMENT = "income_statement"
        BALANCE_SHEET = "balance_sheet"
        CASH_FLOW = "cash_flow"
        DOWNLOAD_LOGS = "download_logs"
        
        # 交易相关表
        TRANSACTIONS = "transactions"
        POSITIONS = "positions"
        DAILY_PNL = "daily_pnl"
        
        # 批次级别表（新增）
        POSITION_LOTS = "position_lots"
        SALE_ALLOCATIONS = "sale_allocations"
        
        @classmethod
        def get_financial_tables(cls) -> Dict[str, str]:
            """获取财务报表表名映射"""
            return {
                'income_statement': cls.INCOME_STATEMENT,
                'balance_sheet': cls.BALANCE_SHEET,
                'cash_flow': cls.CASH_FLOW
            }
        
        @classmethod
        def get_all_required_tables(cls) -> List[str]:
            """获取所有必需的表名"""
            return [
                cls.STOCKS,
                cls.STOCK_PRICES,
                cls.INCOME_STATEMENT,
                cls.BALANCE_SHEET,
                cls.CASH_FLOW,
                cls.DOWNLOAD_LOGS,
            ]
        
        @classmethod
        def get_trading_tables(cls) -> List[str]:
            """获取交易相关表名"""
            return [
                cls.TRANSACTIONS,
                cls.POSITIONS,
                cls.DAILY_PNL,
            ]
        
        @classmethod
        def get_lot_tracking_tables(cls) -> List[str]:
            """获取批次追踪相关表名"""
            return [
                cls.POSITION_LOTS,
                cls.SALE_ALLOCATIONS,
            ]
    
    # ============= 字段名定义 =============
    class Fields:
        # 通用字段
        SYMBOL = "symbol"
        CREATED_AT = "created_at"
        UPDATED_AT = "updated_at"
        
        # 股票基本信息字段
        class Stocks:
            COMPANY_NAME = "company_name"
            SECTOR = "sector"
            INDUSTRY = "industry"
            MARKET_CAP = "market_cap"
            EMPLOYEES = "employees"
            DESCRIPTION = "description"
        
        # 价格数据字段
        class StockPrices:
            ID = "id"
            DATE = "date"
            OPEN = "open"
            HIGH = "high"
            LOW = "low"
            CLOSE = "close"
            VOLUME = "volume"
            ADJ_CLOSE = "adj_close"
        
        # 财务报表字段（通用）
        class FinancialStatement:
            ID = "id"
            PERIOD = "period"
            METRIC_NAME = "metric_name"
            METRIC_VALUE = "metric_value"
        
        # 下载日志字段
        class DownloadLogs:
            ID = "id"
            DOWNLOAD_TYPE = "download_type"
            STATUS = "status"
            DATA_POINTS = "data_points"
            ERROR_MESSAGE = "error_message"
            DETAILS = "details"
            DOWNLOAD_TIMESTAMP = "download_timestamp"
        
        # 交易记录字段
        class Transactions:
            ID = "id"
            EXTERNAL_ID = "external_id"  # 新增：外部业务ID，用于去重
            TRANSACTION_TYPE = "transaction_type"
            QUANTITY = "quantity"
            PRICE = "price"
            TRANSACTION_DATE = "transaction_date"
            PLATFORM = "platform"  # 新增：交易平台
            LOT_ID = "lot_id"  # 新增：关联批次ID
            NOTES = "notes"
        
        # 持仓记录字段
        class Positions:
            ID = "id"
            QUANTITY = "quantity"
            AVG_COST = "avg_cost"
            TOTAL_COST = "total_cost"
            FIRST_BUY_DATE = "first_buy_date"
            LAST_TRANSACTION_DATE = "last_transaction_date"
            IS_ACTIVE = "is_active"
        
        # 每日盈亏字段
        class DailyPnL:
            ID = "id"
            VALUATION_DATE = "valuation_date"
            QUANTITY = "quantity"
            AVG_COST = "avg_cost"
            MARKET_PRICE = "market_price"
            MARKET_VALUE = "market_value"
            UNREALIZED_PNL = "unrealized_pnl"
            UNREALIZED_PNL_PCT = "unrealized_pnl_pct"
            REALIZED_PNL = "realized_pnl"
            REALIZED_PNL_PCT = "realized_pnl_pct"
            TOTAL_COST = "total_cost"
            PRICE_DATE = "price_date"
            IS_STALE_PRICE = "is_stale_price"
        
        # 持仓批次字段（新增）
        class PositionLots:
            ID = "id"
            TRANSACTION_ID = "transaction_id"
            ORIGINAL_QUANTITY = "original_quantity"
            REMAINING_QUANTITY = "remaining_quantity"
            COST_BASIS = "cost_basis"
            PURCHASE_DATE = "purchase_date"
            IS_CLOSED = "is_closed"
            PORTFOLIO_ID = "portfolio_id"
        
        # 卖出分配字段（新增）
        class SaleAllocations:
            ID = "id"
            SALE_TRANSACTION_ID = "sale_transaction_id"
            LOT_ID = "lot_id"
            QUANTITY_SOLD = "quantity_sold"
            COST_BASIS = "cost_basis"
            SALE_PRICE = "sale_price"
            REALIZED_PNL = "realized_pnl"
    
    # ============= SQL模板定义 =============
    class SQLTemplates:
        """SQL模板定义"""
        
        # 基础查询模板
        SELECT_ALL = "SELECT * FROM {table}"
        SELECT_FIELDS = "SELECT {fields} FROM {table}"
        SELECT_WHERE = "SELECT {fields} FROM {table} WHERE {where}"
        SELECT_WHERE_ORDER = "SELECT {fields} FROM {table} WHERE {where} ORDER BY {order}"
        
        # 插入/更新模板
        INSERT_OR_REPLACE = "INSERT OR REPLACE INTO {table} ({fields}) VALUES ({placeholders})"
        INSERT_OR_IGNORE = "INSERT OR IGNORE INTO {table} ({fields}) VALUES ({placeholders})"
        
        # 删除模板
        DELETE_WHERE = "DELETE FROM {table} WHERE {where}"
        
        # 聚合查询模板
        COUNT_WHERE = "SELECT COUNT(*) FROM {table} WHERE {where}"
        MAX_WHERE = "SELECT MAX({field}) FROM {table} WHERE {where}"
        MIN_WHERE = "SELECT MIN({field}) FROM {table} WHERE {where}"
        
        @classmethod
        def get_stock_prices_select(cls, where_conditions: List[str] = None) -> str:
            """获取股票价格查询SQL"""
            fields = f"{StorageConfig.Fields.StockPrices.DATE}, {StorageConfig.Fields.StockPrices.OPEN}, " \
                    f"{StorageConfig.Fields.StockPrices.HIGH}, {StorageConfig.Fields.StockPrices.LOW}, " \
                    f"{StorageConfig.Fields.StockPrices.CLOSE}, {StorageConfig.Fields.StockPrices.VOLUME}, " \
                    f"{StorageConfig.Fields.StockPrices.ADJ_CLOSE}"
            
            if where_conditions:
                where_clause = " AND ".join(where_conditions)
                return cls.SELECT_WHERE_ORDER.format(
                    fields=fields,
                    table=StorageConfig.Tables.STOCK_PRICES,
                    where=where_clause,
                    order=StorageConfig.Fields.StockPrices.DATE
                )
            else:
                return cls.SELECT_FIELDS.format(
                    fields=fields,
                    table=StorageConfig.Tables.STOCK_PRICES
                ) + f" ORDER BY {StorageConfig.Fields.StockPrices.DATE}"
        
        @classmethod
        def get_financial_metrics_select(cls, statement_type: str, where_conditions: List[str] = None) -> str:
            """获取财务指标查询SQL"""
            table_map = StorageConfig.Tables.get_financial_tables()
            table_name = table_map.get(statement_type)
            
            if not table_name:
                raise ValueError(f"未知的报表类型: {statement_type}")
            
            fields = f"{StorageConfig.Fields.SYMBOL}, {StorageConfig.Fields.FinancialStatement.PERIOD}, " \
                    f"{StorageConfig.Fields.FinancialStatement.METRIC_NAME}, " \
                    f"{StorageConfig.Fields.FinancialStatement.METRIC_VALUE}, {StorageConfig.Fields.CREATED_AT}"
            
            if where_conditions:
                where_clause = " AND ".join(where_conditions)
                return cls.SELECT_WHERE_ORDER.format(
                    fields=fields,
                    table=table_name,
                    where=where_clause,
                    order=f"{StorageConfig.Fields.FinancialStatement.PERIOD} DESC, {StorageConfig.Fields.FinancialStatement.METRIC_NAME}"
                )
            else:
                return cls.SELECT_FIELDS.format(
                    fields=fields,
                    table=table_name
                ) + f" ORDER BY {StorageConfig.Fields.FinancialStatement.PERIOD} DESC, {StorageConfig.Fields.FinancialStatement.METRIC_NAME}"
    
    # ============= 索引定义 =============
    @classmethod
    def get_core_indexes(cls) -> List[str]:
        """获取核心表索引创建语句"""
        T = cls.Tables
        F = cls.Fields
        
        return [
            f"CREATE INDEX IF NOT EXISTS idx_{T.STOCK_PRICES}_symbol_date ON {T.STOCK_PRICES} ({F.SYMBOL}, {F.StockPrices.DATE})",
            f"CREATE INDEX IF NOT EXISTS idx_{T.INCOME_STATEMENT}_symbol_period ON {T.INCOME_STATEMENT} ({F.SYMBOL}, {F.FinancialStatement.PERIOD})",
            f"CREATE INDEX IF NOT EXISTS idx_{T.BALANCE_SHEET}_symbol_period ON {T.BALANCE_SHEET} ({F.SYMBOL}, {F.FinancialStatement.PERIOD})",
            f"CREATE INDEX IF NOT EXISTS idx_{T.CASH_FLOW}_symbol_period ON {T.CASH_FLOW} ({F.SYMBOL}, {F.FinancialStatement.PERIOD})",
            f"CREATE INDEX IF NOT EXISTS idx_{T.INCOME_STATEMENT}_metric_name ON {T.INCOME_STATEMENT} ({F.FinancialStatement.METRIC_NAME})",
            f"CREATE INDEX IF NOT EXISTS idx_{T.BALANCE_SHEET}_metric_name ON {T.BALANCE_SHEET} ({F.FinancialStatement.METRIC_NAME})",
            f"CREATE INDEX IF NOT EXISTS idx_{T.CASH_FLOW}_metric_name ON {T.CASH_FLOW} ({F.FinancialStatement.METRIC_NAME})",
            f"CREATE INDEX IF NOT EXISTS idx_{T.DOWNLOAD_LOGS}_symbol ON {T.DOWNLOAD_LOGS} ({F.SYMBOL})",
        ]

    @classmethod
    def get_trading_and_lot_indexes(cls) -> List[str]:
        """获取交易和批次追踪表索引创建语句"""
        T = cls.Tables
        F = cls.Fields

        return [
            f"CREATE INDEX IF NOT EXISTS idx_{T.TRANSACTIONS}_date ON {T.TRANSACTIONS} ({F.Transactions.TRANSACTION_DATE})",
            f"CREATE INDEX IF NOT EXISTS idx_{T.TRANSACTIONS}_symbol_date ON {T.TRANSACTIONS} ({F.SYMBOL}, {F.Transactions.TRANSACTION_DATE})",
            f"CREATE UNIQUE INDEX IF NOT EXISTS ux_{T.TRANSACTIONS}_external ON {T.TRANSACTIONS} ({F.Transactions.EXTERNAL_ID}) WHERE {F.Transactions.EXTERNAL_ID} IS NOT NULL",
            f"CREATE INDEX IF NOT EXISTS idx_{T.POSITIONS}_symbol ON {T.POSITIONS} ({F.SYMBOL})",
            f"CREATE INDEX IF NOT EXISTS idx_{T.DAILY_PNL}_date ON {T.DAILY_PNL} ({F.DailyPnL.VALUATION_DATE})",
            f"CREATE INDEX IF NOT EXISTS idx_{T.DAILY_PNL}_symbol ON {T.DAILY_PNL} ({F.SYMBOL})",
            f"CREATE INDEX IF NOT EXISTS idx_{T.POSITION_LOTS}_symbol ON {T.POSITION_LOTS} ({F.SYMBOL})",
            f"CREATE INDEX IF NOT EXISTS idx_{T.POSITION_LOTS}_symbol_date ON {T.POSITION_LOTS} ({F.SYMBOL}, {F.PositionLots.PURCHASE_DATE})",
            f"CREATE INDEX IF NOT EXISTS idx_{T.POSITION_LOTS}_active ON {T.POSITION_LOTS} ({F.SYMBOL}, {F.PositionLots.IS_CLOSED})",
        ]
    
    # ============= 验证方法 =============
    @classmethod
    def validate_statement_type(cls, statement_type: str) -> bool:
        """验证财务报表类型是否有效"""
        return statement_type in cls.Tables.get_financial_tables()
    
    @classmethod
    def get_table_for_statement_type(cls, statement_type: str) -> str:
        """根据报表类型获取对应的表名"""
        table_map = cls.Tables.get_financial_tables()
        table_name = table_map.get(statement_type)
        if not table_name:
            raise ValueError(f"未知的报表类型: {statement_type}")
        return table_name
    
    @classmethod
    def get_price_field_mapping(cls) -> Dict[str, str]:
        """获取价格字段映射"""
        return {
            'open': cls.Fields.StockPrices.OPEN,
            'high': cls.Fields.StockPrices.HIGH,
            'low': cls.Fields.StockPrices.LOW,
            'close': cls.Fields.StockPrices.CLOSE,
            'adj_close': cls.Fields.StockPrices.ADJ_CLOSE,
        }
    
    @classmethod
    def validate_price_field(cls, price_field: str) -> bool:
        """验证价格字段是否有效"""
        return price_field in cls.get_price_field_mapping()


# 常用查询构建器
class QueryBuilder:
    """SQL查询构建器"""
    
    def __init__(self, table: str):
        self.table = table
        self.conditions: List[str] = []
        self.params: List[str] = []
        self.order_by: List[str] = []
        self.limit_value: int = 0
    
    def where(self, condition: str, *params) -> 'QueryBuilder':
        """添加WHERE条件"""
        self.conditions.append(condition)
        self.params.extend(params)
        return self
    
    def order(self, field: str, direction: str = "ASC") -> 'QueryBuilder':
        """添加ORDER BY条件"""
        self.order_by.append(f"{field} {direction}")
        return self
    
    def limit(self, limit: int) -> 'QueryBuilder':
        """添加LIMIT条件"""
        self.limit_value = limit
        return self
    
    def build_select(self, fields: str = "*") -> tuple[str, List[str]]:
        """构建SELECT查询"""
        sql_parts = [f"SELECT {fields} FROM {self.table}"]
        
        if self.conditions:
            sql_parts.append("WHERE " + " AND ".join(self.conditions))
        
        if self.order_by:
            sql_parts.append("ORDER BY " + ", ".join(self.order_by))
        
        if self.limit_value > 0:
            sql_parts.append(f"LIMIT {self.limit_value}")
        
        return " ".join(sql_parts), self.params
    
    def build_count(self) -> tuple[str, List[str]]:
        """构建COUNT查询"""
        sql_parts = [f"SELECT COUNT(*) FROM {self.table}"]
        
        if self.conditions:
            sql_parts.append("WHERE " + " AND ".join(self.conditions))
        
        return " ".join(sql_parts), self.params
    
    def build_delete(self) -> tuple[str, List[str]]:
        """构建DELETE查询"""
        if not self.conditions:
            raise ValueError("DELETE查询必须包含WHERE条件")
        
        sql = f"DELETE FROM {self.table} WHERE " + " AND ".join(self.conditions)
        return sql, self.params