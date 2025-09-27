# 股票交易追踪模块设计文档（修订版）

## 1. 概述

### 1.1 目标（更新：批次/lot 精确核算）
设计一个与现有项目架构一致的股票交易追踪模块，实现以下核心功能：
1. 每一次买入都单独记录为一个“批次（Lot）”，不能只记录平均成本；
2. 计算 Gain/Loss 时，将每一只股票所有“剩余批次”的未实现盈亏全部计入；
3. 选择卖出时，支持从哪一次或哪几次买入的批次进行卖出（Specific Lot），也支持 FIFO/LIFO 自动分配；
4. 支持每日自动计算并保存日度盈亏（含已实现与未实现）。

### 1.2 设计原则
- 遵循现有项目架构（数据层、模型层、存储层分离）
- 复用现有的 SQLite 存储与价格数据能力
- 与现有存储命名/类型/Schema 管理保持一致（StorageConfig + SQLiteSchemaManager）
- 保持模块化与可扩展性（可插拔成本法、可扩展企业行为）
- 确保数据一致性、准确性与可重算性（UPSERT、事务、幂等）

## 2. 系统架构

### 2.1 模块组织（方案A：单一存储层）
```
stock_analysis/
├── trading/                    # 交易模块（新增）
│   ├── __init__.py
│   ├── models/                 # 交易数据模型
│   │   ├── __init__.py
│   │   ├── transaction.py      # 交易记录模型
│   │   └── portfolio.py        # 投资组合/持仓模型
│   ├── services/               # 交易与持仓服务
│   │   ├── __init__.py
│   │   ├── transaction_service.py
│   │   └── portfolio_service.py
│   ├── calculators/            # 计算器
│   │   ├── __init__.py
│   │   └── pnl_calculator.py   # 盈亏计算器
└── cli/
    └── trading_manager.py      # 交易管理CLI（新增）
tools/
└── migrate_add_trading_tables.py  # 迁移脚本（为现有DB添加交易相关表）
```

- 存储整合：不再单独新增 trading/storage；直接在 `stock_analysis/data/storage/sqlite_storage.py` 内扩展交易相关 API 与事务，复用同一连接与 Schema 管理。

### 2.2 数据流
```
用户输入 → TransactionService → 存储交易记录
         ↓
股票价格数据 → PnLCalculator → 计算每日盈亏 → 存储盈亏记录
         ↓
每日调度器 → 批量计算 → 更新所有持仓盈亏
```

### 2.3 配置（TradingConfig）

**支持的成本基础计算方法：**
- **FIFO（先进先出，默认）**：按时间顺序匹配卖出和买入批次
- **LIFO（后进先出）**：按时间倒序匹配卖出和买入批次  
- **SpecificLot（指定批次）**：用户手动指定卖出特定买入批次
- **AverageCost（平均成本）**：传统的加权平均成本法（作为备选项保留）

**批次追踪原则：**
- 每次买入都作为独立的持仓批次（lot）记录
- 卖出时根据成本基础方法自动匹配或手动指定批次
- 已实现盈亏 = Σ[(卖出价格 - 批次成本价格) × 该批次卖出数量]

**其他配置：**
- 允许做空：默认否
- 小数股支持：默认否（可配置）
- 估值价格来源：adj_close（默认）/ close
- 缺价回填策略：最近交易日回填并标记 / 严格失败模式
- 重算窗口：最近 N 天（默认 7）
- 交易日模式：自然日（默认）/ 仅交易日

### 2.4 存储整合策略（选定：方案A）
- 在 `StorageConfig.Tables/Fields/SQLTemplates/get_all_indexes` 中新增交易相关定义与索引
- 在 `SQLiteSchemaManager._get_table_definitions()` 中追加交易表的建表 SQL
- 在 `sqlite_storage.py` 中新增交易写读 API（如 `upsert_transaction`、`get_position`、`upsert_daily_pnl` 等），与现有数据 API 共用事务与连接

## 3. 数据模型设计

说明：为与现有 SQLite 存储风格对齐，日期统一使用 ISO 文本（YYYY-MM-DD 的 TEXT），金额与价格默认使用 REAL。若需要金融级精度，可在后续扩展中采用“整数分单位”（INTEGER，分/厘）并在服务层做 Decimal 转换。

### 3.1 交易记录模型 (Transaction)
```python
@dataclass
class Transaction:
    id: Optional[int] = None
    symbol: str                     # 股票代码
    transaction_type: str           # 交易类型: 'BUY', 'SELL'
    quantity: float                 # 交易数量（支持小数股）
    price: float                    # 交易价格（REAL）
    transaction_date: str           # 交易日期（YYYY-MM-DD, TEXT）
    lot_id: Optional[int] = None    # （可选）卖出时指定的主要批次ID（便于追踪），批次分配以 SaleAllocation 为准
    notes: Optional[str] = None     # 备注
    created_at: datetime            # 创建时间
    updated_at: datetime            # 更新时间
```

### 3.2 持仓批次模型 (PositionLot)
```python
@dataclass  
class PositionLot:
    id: Optional[int] = None
    symbol: str                     # 股票代码
    transaction_id: int             # 关联的买入交易ID
    original_quantity: float        # 原始买入数量
    remaining_quantity: float       # 剩余数量
    cost_basis: float              # 成本基础（每股成本）
    purchase_date: str             # 买入日期（YYYY-MM-DD, TEXT）
    is_closed: bool = False        # 是否已完全卖出
    created_at: datetime
    updated_at: datetime

    @property
    def total_cost(self) -> float:
        """总成本 = 剩余数量 × 成本基础"""
        return self.remaining_quantity * self.cost_basis
```

### 3.3 持仓汇总模型 (PositionSummary)
```python
@dataclass
class PositionSummary:
    """某股票的持仓汇总（从所有批次计算得出）"""
    symbol: str
    total_quantity: float           # 总持仓数量
    total_cost: float              # 总成本（所有批次成本之和）
    avg_cost: float                # 加权平均成本
    first_buy_date: str            # 最早买入日期
    last_transaction_date: str     # 最后交易日期
    lot_count: int                 # 持仓批次数量
```

### 3.4 卖出匹配记录模型 (SaleAllocation)
```python
@dataclass
class SaleAllocation:
    """卖出交易与买入批次的匹配记录"""
    id: Optional[int] = None
    sale_transaction_id: int        # 卖出交易ID
    lot_id: int                    # 匹配的买入批次ID
    quantity_sold: float           # 从该批次卖出的数量
    cost_basis: float              # 该批次的成本基础
    realized_pnl: float            # 该笔匹配的已实现盈亏
    created_at: datetime

    @property
    def proceeds(self) -> float:
        """该笔匹配的销售收入"""
        # 需要从sale_transaction中获取价格
        pass
```

### 3.5 每日盈亏记录模型 (DailyPnL)
```python
@dataclass
class DailyPnL:
    id: Optional[int] = None
    symbol: str                     # 股票代码
    valuation_date: str             # 估值日期（YYYY-MM-DD, TEXT）
    quantity: float                 # 持仓数量
    avg_cost: float                 # 加权平均成本（REAL）
    market_price: float             # 市场价格（收盘价, REAL）
    market_value: float             # 市场价值（REAL）
    unrealized_pnl: float           # 未实现盈亏（REAL）
    unrealized_pnl_pct: float       # 未实现盈亏百分比（REAL）
    realized_pnl: float = 0.0       # 当日已实现盈亏（聚合, REAL）
    realized_pnl_pct: float = 0.0   # 当日已实现盈亏百分比（REAL）
    total_cost: float               # 总成本（所有批次成本之和, REAL）
    created_at: datetime
```

## 4. 核心功能设计

### 4.1 交易记录服务 (TransactionService)

#### 4.1.1 主要方法
```python
class TransactionService:
    def record_buy_transaction(self, symbol: str, 
                             quantity: float, price: float, 
                             transaction_date: str) -> Transaction
    
    def record_sell_transaction(self, symbol: str,
                               quantity: float, price: float,
                               transaction_date: str,
                               cost_basis_method: str = 'FIFO',
                               specific_lots: List[Dict] = None) -> Transaction
    
    def get_user_transactions(self, symbol: str | None = None) -> List[Transaction]
    
    def get_position_lots(self, symbol: str = None) -> List[PositionLot]
    
    def get_position_summary(self, symbol: str = None) -> List[PositionSummary]
    
    def get_sale_allocations(self, symbol: str = None) -> List[SaleAllocation]
```

#### 4.1.2 业务逻辑

**买入处理：**
1. 创建买入交易记录
2. 创建新的持仓批次（PositionLot）
3. 每个买入都是独立批次，保持完整的成本追踪

**卖出处理：**
1. 创建卖出交易记录
2. 根据成本基础方法选择匹配的批次：
   - **FIFO**: 按购买日期从早到晚匹配
   - **LIFO**: 按购买日期从晚到早匹配
   - **SpecificLot**: 用户指定特定批次ID和数量
3. 创建SaleAllocation记录，记录每个批次的匹配明细
4. 更新相应批次的剩余数量，完全卖出的批次标记为关闭
5. 计算已实现盈亏：Σ[(卖出价格 - 批次成本基础) × 批次卖出数量]

**约束和验证：**
- 卖出数量不得超过当前总持仓
- SpecificLot模式下，指定批次必须有足够剩余数量
- 默认不允许做空（可配置）

### 4.2 盈亏计算器 (PnLCalculator)

#### 4.2.1 主要功能
- **未实现盈亏计算**：基于所有持仓批次的市值与成本差值
- **已实现盈亏聚合**：按日期聚合当日所有卖出交易的已实现盈亏
- **加权平均成本计算**：根据所有有效批次计算整体平均成本

#### 4.2.2 计算逻辑
```python
class PnLCalculator:
    def calculate_daily_pnl(self, symbol: str, 
                          calculation_date: str, 
                          price_source: str = 'adj_close') -> DailyPnL
    
    def calculate_unrealized_pnl(self, lots: List[PositionLot], 
                                market_price: float) -> float
    
    def aggregate_realized_pnl(self, symbol: str, 
                             date: str) -> float
    
    def get_weighted_avg_cost(self, lots: List[PositionLot]) -> float
```

#### 4.2.3 处理特性
- **批次级别计算**：逐个批次计算未实现盈亏，然后汇总
- **缺价处理**：使用最近交易日价格回填并标记数据源
- **重算窗口**：支持仅重算最近 N 天以提升性能
- **事务一致性**：保证盈亏计算与持仓更新的原子性

## 5. 数据库设计（与现有存储对齐）

实现上通过扩展 `stock_analysis/data/storage/config.py` 的 `StorageConfig` 与 `sqlite_schema.py` 的 `SQLiteSchemaManager` 管理表名、字段与建表/索引 SQL，避免零散 SQL。以下为与之对齐的 SQLite 示例定义（示意）。

### 5.1 交易记录表（transactions）
```
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('BUY','SELL')),
    quantity REAL NOT NULL,
    price REAL NOT NULL,
    transaction_date TEXT NOT NULL,
    lot_id INTEGER,  -- 卖出时关联的主要批次ID（可为空）
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (symbol) REFERENCES stocks(symbol)
);

CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(transaction_date);
CREATE INDEX IF NOT EXISTS idx_transactions_symbol_date ON transactions(symbol, transaction_date);
CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(transaction_type);
```

### 5.2 持仓批次表（position_lots）
```
CREATE TABLE IF NOT EXISTS position_lots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    transaction_id INTEGER NOT NULL,  -- 关联的买入交易ID
    original_quantity REAL NOT NULL,  -- 原始买入数量
    remaining_quantity REAL NOT NULL, -- 剩余数量
    cost_basis REAL NOT NULL,         -- 每股成本基础
    purchase_date TEXT NOT NULL,      -- 买入日期
    is_closed INTEGER DEFAULT 0,      -- 是否已完全卖出
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (transaction_id) REFERENCES transactions(id),
    FOREIGN KEY (symbol) REFERENCES stocks(symbol)
);

CREATE INDEX IF NOT EXISTS idx_position_lots_symbol ON position_lots(symbol);
CREATE INDEX IF NOT EXISTS idx_position_lots_symbol_date ON position_lots(symbol, purchase_date);
CREATE INDEX IF NOT EXISTS idx_position_lots_transaction ON position_lots(transaction_id);
CREATE INDEX IF NOT EXISTS idx_position_lots_active ON position_lots(symbol, is_closed);
```

### 5.3 卖出匹配表（sale_allocations）
```
CREATE TABLE IF NOT EXISTS sale_allocations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_transaction_id INTEGER NOT NULL,  -- 卖出交易ID
    lot_id INTEGER NOT NULL,               -- 匹配的批次ID
    quantity_sold REAL NOT NULL,           -- 从该批次卖出的数量
    cost_basis REAL NOT NULL,              -- 该批次的成本基础
    sale_price REAL NOT NULL,              -- 卖出价格
    realized_pnl REAL NOT NULL,            -- 该笔匹配的已实现盈亏
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sale_transaction_id) REFERENCES transactions(id),
    FOREIGN KEY (lot_id) REFERENCES position_lots(id)
);

CREATE INDEX IF NOT EXISTS idx_sale_allocations_transaction ON sale_allocations(sale_transaction_id);
CREATE INDEX IF NOT EXISTS idx_sale_allocations_lot ON sale_allocations(lot_id);
```

### 5.4 每日盈亏表（daily_pnl）
```
CREATE TABLE IF NOT EXISTS daily_pnl (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    valuation_date TEXT NOT NULL,
    quantity REAL NOT NULL,
    avg_cost REAL NOT NULL,
    market_price REAL NOT NULL,
    market_value REAL NOT NULL,
    unrealized_pnl REAL NOT NULL,
    unrealized_pnl_pct REAL NOT NULL,
    realized_pnl REAL DEFAULT 0,
    realized_pnl_pct REAL DEFAULT 0,
    total_cost REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, valuation_date)
);

CREATE INDEX IF NOT EXISTS idx_daily_pnl_date ON daily_pnl(valuation_date);
CREATE INDEX IF NOT EXISTS idx_daily_pnl_symbol ON daily_pnl(symbol);
```

（企业行为与分红表可在后续扩展中加入，如 `corporate_actions`、`dividends`。）

## 6. API设计

### 6.1 CLI命令
```bash
# 记录买入交易
stock-trading buy -s AAPL -q 100 -p 150.50 -d 2024-01-15

# 记录卖出交易（FIFO方式）
stock-trading sell -s AAPL -q 50 -p 160.25 -d 2024-02-15

# 记录卖出交易（指定成本基础方法）
stock-trading sell -s AAPL -q 30 -p 165.00 -d 2024-02-20 --basis LIFO

# 记录卖出交易（指定特定批次）
stock-trading sell -s AAPL -q 20 -p 170.00 -d 2024-02-25 --specific-lots "lot_id:123,quantity:15;lot_id:124,quantity:5"

# 查看持仓批次明细
stock-trading lots -s AAPL

# 查看持仓汇总
stock-trading positions

# 查看卖出匹配历史
stock-trading sales -s AAPL

# 计算指定日期盈亏
stock-trading calculate-pnl --date 2024-02-20

# 批量计算历史盈亏
stock-trading batch-calculate --start-date 2024-01-01 --end-date 2024-02-29

# 查看投资组合摘要
stock-trading portfolio

# 通用参数
#   --db-path database/stock_data.db
#   -v/--verbose
#   --basis fifo|lifo|average|specific  # 默认成本基础方法
#   --price-source adj_close|close
#   --recompute-window 7
```

### 6.2 Python API
```python
from stock_analysis.trading import TransactionService, PnLCalculator

transaction_service = TransactionService()

# 记录买入
buy_transaction = transaction_service.record_buy_transaction(
    symbol="AAPL", 
    quantity=100,
    price=150.50,
    transaction_date="2024-01-15",
)

# 记录卖出（FIFO方式）
sell_transaction = transaction_service.record_sell_transaction(
    symbol="AAPL",
    quantity=50,
    price=160.25,
    transaction_date="2024-02-15",
    cost_basis_method="FIFO"
)

# 记录卖出（指定特定批次）
specific_lots = [
    {"lot_id": 123, "quantity": 30},
    {"lot_id": 124, "quantity": 20}
]
sell_transaction = transaction_service.record_sell_transaction(
    symbol="AAPL",
    quantity=50,
    price=165.00,
    transaction_date="2024-02-20",
    cost_basis_method="SpecificLot",
    specific_lots=specific_lots
)

# 查看持仓批次
lots = transaction_service.get_position_lots("AAPL")

# 查看持仓汇总
summary = transaction_service.get_position_summary("AAPL")

# 计算盈亏
pnl_calculator = PnLCalculator()
daily_pnl = pnl_calculator.calculate_daily_pnl(
    symbol="AAPL",
    calculation_date="2024-02-20",
)
```

## 7. 与现有系统集成

### 7.1 复用现有组件
- 数据存储：扩展现有的 SQLiteStorage（在 sqlite_storage.py 中新增交易相关 API）与 SQLiteSchemaManager（追加交易表）
- 股票价格：复用现有价格数据（优先 adj_close）
- 配置管理：新增 TradingConfig，与 DataServiceConfig 风格一致
- 日志系统：复用 utils.logging_utils.setup_logging
- Schema/索引：在 StorageConfig 集中新增表名/字段/索引，并由 SQLiteSchemaManager.create_tables() 创建

### 7.2 扩展点
- 多用户支持：可在应用层实现用户隔离
- 多币种支持：预留 currency 字段
- 分红处理：预留 dividends 相关表
- 股票分割：预留 split 调整机制（成本基与股数换算）

### 7.3 迁移
- 在 tools/migrate_add_trading_tables.py 提供迁移脚本，为已有数据库添加交易相关表与索引：
  - 新建表：position_lots、sale_allocations 及其索引
  - 从历史 BUY 交易初始化 Lots（original=quantity，remaining=quantity，cost_basis=price，purchase_date=transaction_date）
- 与 tools/validate_schema.py 一致，校验必备表是否存在

## 8. 实施计划（适配批次级别追踪）

### 8.1 阶段1：批次数据模型与存储基础
**目标**：建立批次级别数据结构，为精确成本追踪奠定基础

1. **数据模型设计**
   - 创建PositionLot模型（核心：每次买入为一个批次）
   - 创建SaleAllocation模型（记录卖出与批次的匹配关系）
   - 修改Transaction模型（添加lot_id字段用于快速关联）
   - 保留DailyPnL模型（支持批次汇总计算）

2. **数据库Schema扩展**
   - 扩展StorageConfig：新增`position_lots`和`sale_allocations`表定义
   - 更新SQLiteSchemaManager：添加批次表建表SQL与索引
   - 设计关键索引：`(symbol, purchase_date)`、`(symbol, is_closed)`等

3. **迁移策略**
   - 编写`migrate_to_lot_tracking.py`：从现有transactions生成PositionLot记录
   - 对于历史BUY交易：每笔买入创建一个Lot（original_quantity=quantity，remaining_quantity=quantity）
   - 对于历史SELL交易：按FIFO原则匹配生成SaleAllocation记录并更新Lot剩余数量

4. **基础CRUD操作**
   - 在SQLiteStorage中新增：`create_position_lot`、`update_lot_remaining`、`create_sale_allocation`
   - 新增查询接口：`get_user_lots`、`get_active_lots_by_symbol`、`get_sale_allocations`

### 8.2 阶段2：批次根据买入功能
**目标**：实现单一批次的买入逻辑，确保每次购买都有完整的成本记录

1. **买入交易处理**
   - 实现`TransactionService.record_buy_transaction()`
     - 创建买入交易记录
     - 计算成本基础：`cost_basis = price`
     - 创建对应PositionLot（original_quantity=quantity, remaining_quantity=quantity）
   
2. **批次查询功能**
   - `get_position_lots(symbol=None)`：获取所有有效批次
   - `get_position_summary(symbol=None)`：汇总计算总持仓、平均成本等

3. **输入校验**
   - 数量、价格的合法性校验
   - 股票代码存在性校验（复用现有`ensure_stock_exists`）

### 8.3 阶段3：批次匹配卖出功能
**目标**：实现FIFO/LIFO/SpecificLot三种成本基础方法的卖出匹配

1. **成本基础方法实现**
   - `CostBasisMatcher`抽象基类
     - `FIFOMatcher`：按purchase_date正序排列匹配
     - `LIFOMatcher`：按purchase_date倒序排列匹配
     - `SpecificLotMatcher`：按用户指定的lot_id和数量匹配

2. **卖出交易处理**
   - `TransactionService.record_sell_transaction()`
     - 验证卖出数量不超过总持仓
     - 根据cost_basis_method选择匹配器
     - 按批次分配卖出数量，创建SaleAllocation记录
     - 更新各批次的remaining_quantity，标记完全卖出的批次为is_closed
     - 计算已实现盈亏：按批次汇总`(sale_price - cost_basis) * allocated_quantity`


### 8.4 阶段4：批次级别盈亏计算
**目标**：基于批次数据计算精确的每日盈亏

1. **未实现盈亏计算**
   - `PnLCalculator.calculate_unrealized_pnl_by_lots()`
     - 逐个批次计算：`(market_price - cost_basis) * remaining_quantity`
     - 汇总所有有效批次的未实现盈亏

2. **已实现盈亏聚合**
   - `aggregate_daily_realized_pnl(symbol, date)`
     - 从当日所有SaleAllocation记录中汇总已实现盈亏
     - 支持跨多次卖出交易的聚合

3. **加权平均成本计算**
   - `calculate_weighted_avg_cost(lots)`
     - 根据所有有效批次计算：`Σ(cost_basis * remaining_quantity) / Σ(remaining_quantity)`

4. **日度盈亏记录**
   - 更新DailyPnL表：使用批次级别计算结果替换原平均成本逻辑

### 8.5 阶段5：批次CLI命令与高级功能
**目标**：提供完整的批次管理命令行接口

1. **批次管理CLI**
   - `stock-trading buy`：记录买入（自动创建批次）
   - `stock-trading sell`：支持`--basis FIFO|LIFO|SpecificLot`和`--specific-lots`参数
   - `stock-trading lots`：显示用户所有批次明细（有效/已关闭）
   - `stock-trading sales`：显示卖出匹配历史
   - `stock-trading positions`：显示汇总持仓（从批次计算得出）

2. **高级分析功能**
   - `stock-trading tax-report`：生成税务申报所需的成本基础明细
   - `stock-trading portfolio --as-of-date`：按指定日期计算投资组合数据
   - `stock-trading rebalance-simulate`：模拟不同成本基础方法的税负影响

3. **每日自动计算**
   - `stock-trading daily --user-id`：计算今日所有持仓的盈亏（适合cron定时）
   - 支持批量用户处理

### 8.6 阶段6：性能优化与复杂场景测试
**目标**：确保批次级别系统的稳定性和性能

1. **性能优化**
   - 批量查询优化：`get_lots_batch()`一次获取多个用户/股票的批次
   - 索引优化：为高频查询场景添加复合索引
   - 分页查询：对于批次数量很多的用户支持分页返回
   - 数据归档：老旧已关闭批次的归档策略

2. **复杂场景测试**
   - **跨批次卖出故障测试**：模拟在创建SaleAllocation过程中的中断情况
   - **并发交易测试**：多用户同时进行同一股票的买卖
   - **数据一致性验证**：确保批次数据与交易记录的一致性
   - **大数据量测试**：模拟数千批次的查询和计算性能

3. **单元测试覆盖**
   - 批次匹配逻辑测试（FIFO/LIFO/SpecificLot的各种边界情况）
   - 盈亏计算精度测试（对比批次级别与传统平均成本法）
   - 迁移脚本测试（从现有数据生成批次记录）

### 8.7 阶段7：文档与部署
**目标**：完善批次级别系统的文档和部署指南

1. **用户文档**
   - 更新README：批次级别交易追踪的特性介绍
   - 创建`docs/lot_tracking_guide.md`：详细的批次管理指南
   - 成本基础方法选择指南：不同方法的税务影响对比

2. **迁移指南**
   - 从传统平均成本系统升级到批次级别系统的步骤
   - 数据备份与恢复策略
   - 升级前后的数据一致性验证

3. **部署清单**
   - 生产环境配置推荐（批次查询性能优化）
   - 监控和报警设置（批次数据不一致报警）
   - 定期数据一致性检查脚本

## 9. 批次级别系统特别注意事项

### 9.0 设计核心原则
- **一次买入一个批次**：每笔买入交易都必须创建独立的PositionLot记录
- **卖出必须匹配批次**：不允许“残屾”卖出，每笔卖出都必须明确来源于哪些批次
- **完整的匹配记录**：每个SaleAllocation记录必须包含精确的成本、数量和盈亏
- **事务原子性**：卖出操作必须确保交易记录、批次更新、匹配记录的一致性

## 10. 通用注意事项

### 10.1 数据准确性
- 默认采用 REAL 存储金额/价格以对齐现有实现；如需提升精度，可在后续采用“整数分单位”方案
- 实现事务处理确保数据一致性
- 添加数据验证规则（数量>0、非负价格、日期合法）

### 10.2 性能考虑
- 批量计算时使用批处理优化
- 对高频查询字段添加索引
- 考虑历史数据归档策略

### 10.3 扩展性
- 预留字段支持未来功能扩展
- 模块化设计支持不同计算策略
- 支持插件化的盈亏计算器

### 10.4 业务规则细化

**成本基础方法：**
- **FIFO（默认）**：先进先出，按购买日期从早到晚匹配
- **LIFO**：后进先出，按购买日期从晚到早匹配
- **SpecificLot**：用户指定特定批次，提供最大灵活性
- **AverageCost**：传统平均成本法（备选）

**批次管理规则：**
- 每次买入创建独立批次，保持完整的成本基础追踪
- 卖出时按选定方法匹配批次，支持部分卖出
- 批次完全卖出时标记为关闭，但保留历史记录
- 支持跨批次卖出，自动创建多条匹配记录


**其他规则：**
- 估值价格：默认使用 adj_close，可切换为 close
- 缺价处理：使用最近交易日价格回填并标记 stale
- 卖空：默认不允许，可配置支持

### 10.5 错误处理
- 处理股票价格数据缺失情况
- 处理卖出数量超过持仓的情况
- 处理节假日和停牌的情况
