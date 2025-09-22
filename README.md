# 🎯 Stock Analysis System

一个现代化的股票数据获取、存储和技术分析系统，采用标准Python包架构设计。

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Code Style](https://img.shields.io/badge/Code%20Style-Black-black.svg)](https://black.readthedocs.io)

## ✨ 核心特性

### 📊 数据管理
- **混合下载策略**: 智能选择 Stooq(批量) 和 Finnhub(增量) 数据源
- **100天阈值机制**: 自动判断使用增量更新还是批量下载
- **规范化财务数据**: 分离式存储损益表、资产负债表、现金流量表
- **数据质量评估**: 自动检测和报告数据完整性
- **SQLite存储**: 高效的本地数据存储和管理

### 📈 技术分析
- **技术指标**: RSI、移动平均线、布林带等
- **可插拔算子**: 模块化的分析操作器系统
- **趋势分析**: 自动识别股票趋势和信号
- **风险提醒**: 股价异常波动预警

### 💹 批次级别交易追踪（v2.0新增）
- **批次追踪**: 每次买入创建独立批次，支持精确成本基础计算
- **多种成本基础方法**: FIFO、LIFO、SpecificLot、AverageCost四种方法
- **卖出分配**: 详细记录每笔卖出对应的批次分配和已实现盈亏
- **税务报告**: 生成符合税务申报要求的成本基础明细
- **成本基础模拟**: 比较不同方法的税负影响，助力投资决策
- **高性能查询**: 批量查询、分页支持、优化索引
- **数据一致性**: 完整的验证机制确保批次与交易记录一致
- **向后兼容**: 保持与传统平均成本法的兼容性

### 🔧 现代化架构
- **标准Python包**: 可pip安装，无路径依赖
- **命令行工具**: 专业的CLI界面
- **模块化设计**: 清晰的层次结构和职责分离
- **可扩展性**: 支持自定义分析器和数据源

## 🚀 快速开始

### 安装

```bash
# 克隆项目
git clone https://github.com/llshan/stock.git
cd stock

# 安装依赖并以开发模式安装
pip install -e .
```

### 基本使用

#### 1. 数据下载
```bash
# 下载单只股票
stock-data download -s AAPL

# 下载多只股票
stock-data download -s AAPL GOOG MSFT

# 下载并包含财务数据
stock-data download -s AAPL --comprehensive

# 仅下载财务数据
stock-data download -s AAPL --financial-only
```

#### 2. 数据查询
```bash
# 查看股票数据
stock-data query -s AAPL

# 指定时间范围
stock-data query -s AAPL --start-date 2023-01-01 --end-date 2024-01-01

# 限制显示行数
stock-data query -s AAPL --limit 10
```

#### 3. 技术分析
```bash
# 分析单只股票（1年期）
stock-analyze -s AAPL --period 1y

# 分析多只股票（6个月期）
stock-analyze -s AAPL GOOG --period 6mo

# 自定义分析算子
stock-analyze -s AAPL --operators ma,rsi,drop_alert
```

#### 4. 数据库管理
```bash
# 查看数据库表
stock-db list

# 查看表结构
stock-db schema -t stocks

# 查看表数据
stock-db print -t stocks --limit 10
```

#### 5. 批次级别交易管理（v2.0）
```bash
# 基础交易记录
stock-trading buy  --user-id u1 -s AAPL -q 100 -p 150.50 -d 2024-01-15 --commission 9.95
stock-trading sell --user-id u1 -s AAPL -q  20 -p 160.00 -d 2024-02-01

# 批次级别卖出（支持多种成本基础方法）
stock-trading sell --user-id u1 -s AAPL -q 30 -p 160.0 -d 2024-02-01 --basis fifo
stock-trading sell --user-id u1 -s AAPL -q 30 -p 160.0 -d 2024-02-01 --basis lifo
stock-trading sell --user-id u1 -s AAPL -q 30 -p 160.0 -d 2024-02-01 --basis specific --specific-lots "lot=1:20,lot=2:10"

# 查看持仓和批次详情
stock-trading positions --user-id u1                    # 持仓汇总
stock-trading lots --user-id u1 -s AAPL                # 查看AAPL的所有批次
stock-trading sales --user-id u1 -s AAPL               # 查看AAPL的卖出分配历史

# 盈亏计算
stock-trading calculate-pnl --user-id u1 --date 2024-02-20
stock-trading batch-calculate --user-id u1 --start-date 2024-01-01 --end-date 2024-02-29
stock-trading daily --user-id u1                       # 今日盈亏（适合cron定时）

# 高级分析功能
stock-trading portfolio --user-id u1 --as-of-date 2024-02-29                    # 投资组合摘要
stock-trading tax-report --user-id u1 --start-date 2024-01-01 --end-date 2024-12-31  # 税务报告
stock-trading rebalance-simulate --user-id u1 -s AAPL -q 50 -p 180.0           # 成本基础模拟
```

**成本基础方法说明：**
- `fifo`: 先进先出（默认，税务常用）
- `lifo`: 后进先出（税务优化）
- `specific`: 指定批次（最大灵活性）
- `average`: 平均成本法（向后兼容）

**批次级别特性：**
- 每次买入自动创建独立批次，支持精确成本基础计算
- 卖出时详细记录批次分配，提供完整的已实现盈亏审计轨迹
- 支持税务申报所需的成本基础明细报告
- 数据一致性验证确保批次与交易记录完全匹配

### 系统升级与迁移
#### 数据库迁移（已有数据库升级到批次级别）
```bash
# 1. 备份现有数据库
cp database/stock_data.db database/stock_data_backup_$(date +%Y%m%d).db

# 2. 执行表结构升级
python tools/migrate_add_trading_tables.py --db-path database/stock_data.db

# 3. 迁移到批次级别系统（可选）
python tools/migrate_to_lot_tracking.py --db-path database/stock_data.db --dry-run  # 预览
python tools/migrate_to_lot_tracking.py --db-path database/stock_data.db            # 执行

# 4. 验证迁移结果
python tools/post_migration_validation.py --db-path database/stock_data.db
```

详细迁移指南请参阅：[docs/migration_guide.md](docs/migration_guide.md)

#### 批次级别配置
```python
# stock_analysis/trading/config.py
TRADING_CONFIG = {
    # 批次追踪设置
    'enable_lot_tracking': True,
    'default_cost_basis_method': 'FIFO',  # FIFO/LIFO/SpecificLot/AverageCost
    
    # 精度设置  
    'decimal_precision': 4,
    'enable_precise_calculations': True,
    
    # 性能设置
    'batch_query_size': 1000,
    'pagination_size': 100,
    
    # 安全设置
    'max_user_id_length': 50,
    'max_calculation_days': 3650,  # 10年
    'enable_external_id_validation': True
}
```

#### 常用CLI选项
- `--db-path`: 指定数据库路径（默认 `database/stock_data.db`）
- `--price-source adj_close|close`: 估值价源（默认 `adj_close`）
- `--only-trading-days`: 批量计算时仅按交易日计算
- `--basis fifo|lifo|specific|average`: 成本基础方法
- `--specific-lots "lot=1:20,lot=2:10"`: 指定批次卖出
- `--external-id`: 外部业务ID（用于去重）

## 📦 项目结构

```
stock_analysis/
├── __init__.py              # 包入口
├── data/                    # 数据层
│   ├── downloaders/        # 数据下载器
│   ├── storage/            # 数据存储
│   ├── models/             # 数据模型
│   └── config.py           # 配置管理
├── analysis/               # 分析层
│   ├── operators/          # 分析算子
│   ├── pipeline/           # 分析流水线
│   └── config.py          # 分析配置
├── cli/                    # 命令行工具
│   ├── data_manager.py     # 数据管理CLI
│   ├── data_analyzer.py    # 分析CLI
│   └── db_print.py         # 数据库CLI
└── utils/                  # 工具函数
    └── logging_utils.py    # 日志工具
```

## 🛠️ 作为Python库使用

### 基础用法

```python
from stock_analysis import DataService, AnalysisService

# 初始化服务
data_service = DataService()
analysis_service = AnalysisService()

# 下载股票数据
result = data_service.download_and_store_stock_data('AAPL')
print(f"Downloaded {result.data_points} data points")

# 技术分析
analysis_result = analysis_service.run_analysis(['AAPL'], period='1y')
print(analysis_result['AAPL']['summary'])
```

### 自定义数据源

```python
from stock_analysis.data.storage import create_storage
from stock_analysis.data.downloaders import StooqDataDownloader

# 使用特定数据源
storage = create_storage('sqlite', db_path='my_data.db')
downloader = StooqDataDownloader()

# 下载数据
data = downloader.download_stock_data('AAPL', '2023-01-01')
storage.store_stock_data('AAPL', data)
```

### 自定义分析算子

```python
from stock_analysis.analysis.operators.base import Operator
import pandas as pd

class MyCustomOperator(Operator):
    def execute(self, data: pd.DataFrame) -> dict:
        # 自定义分析逻辑
        return {
            'signal': 'buy' if data['close'].iloc[-1] > data['close'].mean() else 'sell',
            'confidence': 0.85
        }
```

## ⚙️ 配置

### 环境变量

```bash
# 设置默认数据库路径
export DATA_SERVICE_DB_PATH="path/to/your/database.db"

# 设置Finnhub API密钥
export FINNHUB_API_KEY="your_finnhub_api_key"

# 设置股票增量更新阈值（天）
export DATA_SERVICE_STOCK_INCREMENTAL_THRESHOLD_DAYS="100"

# 设置默认关注股票列表
export WATCHLIST="AAPL,GOOG,MSFT,TSLA"

# 设置日志级别
export DATA_SERVICE_LOG_LEVEL="INFO"
```

### 配置文件

创建 `config.yml`：

```yaml
database:
  path: "database/stock_data.db"
  
downloader:
  stock_incremental_threshold_days: 100
  financial_refresh_days: 90
  max_retries: 3
  base_delay: 30

analysis:
  default_period: "1y"
  operators: ["ma", "rsi", "fin_ratios", "fin_health", "drop_alert"]
```

### 交易模块配置

交易模块提供灵活的配置选项，支持不同的使用场景：

```python
from stock_analysis.trading import TransactionService, PnLCalculator
from stock_analysis.trading.config import TradingConfig, CostBasisMethod

# 基础配置（推荐生产环境）
config = TradingConfig(
    cost_basis_method=CostBasisMethod.AVERAGE_COST,  # 平均成本法
    only_trading_days=True,                          # 仅交易日计算，减少回填
    max_user_id_length=100,                         # 用户ID长度限制
    max_quantity_per_transaction=10_000_000         # 单笔交易量限制
)

# 在服务中使用配置
transaction_service = TransactionService(config=config)
pnl_calculator = PnLCalculator(config=config)
```

#### 核心配置项

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `cost_basis_method` | `AVERAGE_COST` | 成本计算方法（当前支持平均成本法） |
| `only_trading_days` | `False` | 是否仅在交易日计算盈亏 |
| `price_source` | `ADJ_CLOSE` | 价格来源（复权收盘价） |
| `missing_price_strategy` | `BACKFILL` | 缺失价格处理策略 |
| `max_user_id_length` | `100` | 用户ID最大长度 |
| `max_quantity_per_transaction` | `10,000,000` | 单笔交易最大数量 |
| `max_calculation_days` | `3,650` | 最大计算时间跨度（10年） |

#### 实践建议

**生产环境配置**:
```python
production_config = TradingConfig(
    only_trading_days=True,        # 减少回填，提高性能
    max_calculation_days=1825,     # 限制为5年，控制计算量
    price_precision=4,             # 适当精度
    amount_precision=2             # 标准货币精度
)
```

**开发测试配置**:
```python
dev_config = TradingConfig(
    only_trading_days=False,       # 包含周末便于测试
    max_user_id_length=50,         # 严格限制发现问题
    max_quantity_per_transaction=1_000_000  # 较低限制
)
```

详细配置指南请参考：[交易配置指南](docs/trading_config_guide.md)

## 📊 支持的技术指标

### 当前指标
- **移动平均线** (MA): 5日、10日、20日、50日均线
- **相对强弱指数** (RSI): 14周期RSI，支持超买超卖信号
- **财务比率** (fin_ratios): 净利润率、ROE、负债率、PE比率
- **财务健康** (fin_health): 基于多指标的健康评分 (A-F等级)
- **趋势分析**: 基于均线的趋势判断
- **跌幅警报**: 异常波动监测 (1日和7日)

### 计划指标
- MACD (移动平均收敛散度)
- 布林带 (Bollinger Bands)  
- KDJ 随机指标
- 成交量指标

## 🗃️ 数据源

### 支持的数据源
- **Finnhub**: 财务报表和指标
- **Stooq**: 历史价格数据，数据质量高
- **混合策略**: 自动选择最优数据源

### 数据质量
- 自动数据验证和清洗
- 缺失数据检测和报告
- 数据完整性评分 (A-F等级)

## 🧪 开发和测试

### 开发环境搭建

```bash
# 克隆项目
git clone https://github.com/llshan/stock.git
cd stock

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\\Scripts\\activate  # Windows

# 安装开发依赖
pip install -e ".[dev]"

# 运行交易模块测试
pytest -q tests/trading
```

### 代码风格

项目使用以下工具维护代码质量：

```bash
# 代码格式化
black stock_analysis/

# 代码检查
flake8 stock_analysis/

# 类型检查
mypy stock_analysis/

# 导入排序
isort stock_analysis/
```

## 📈 使用示例

### 完整分析流程

```python
from stock_analysis import DataService, AnalysisService
import json

# 1. 下载数据
data_service = DataService()
symbols = ['AAPL', 'GOOG', 'MSFT']

for symbol in symbols:
    result = data_service.download_and_store_comprehensive_data(symbol)
    print(f"{symbol}: {'✅' if result['success'] else '❌'}")

# 2. 技术分析
analysis_service = AnalysisService()
results = analysis_service.run_analysis(symbols, period='6mo')

# 3. 结果展示
for symbol, data in results.items():
    summary = data['summary']
    print(f"""
    {symbol} 分析结果:
    - 趋势: {summary['trend']}
    - RSI信号: {summary['rsi_signal']}
    - 风险警报: {'是' if summary['drop_alert'] else '否'}
    """)
```

### 批量数据管理

```bash
# 批量下载热门股票
stock-data download -s AAPL GOOG MSFT TSLA NVDA --comprehensive -v

# 批量分析
stock-analyze -s AAPL GOOG MSFT TSLA NVDA --period 1y --output results.json

# 查看结果
cat results.json | jq '.[] | {symbol: .symbol, trend: .summary.trend}'
```

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 🔗 相关链接

- [项目首页](https://github.com/llshan/stock)
- [问题报告](https://github.com/llshan/stock/issues)
- [贡献指南](CONTRIBUTING.md)
- [更新日志](CHANGELOG.md)

## 💡 常见问题

### Q: 如何解决API限制错误？
A: 系统会自动在Finnhub和Stooq之间进行回退。如遇到速率限制，请等待或配置API密钥。

### Q: 数据不完整怎么办？
A: 使用 `stock-data query -s SYMBOL` 检查数据范围，然后重新下载：`stock-data download -s SYMBOL --start-date 2020-01-01`

### Q: 如何添加新的技术指标？
A: 继承 `Operator` 基类创建新算子，参考 `analysis/operators/` 目录下的示例。

---

**Stock Analysis System** - 让股票分析变得简单高效 🚀
