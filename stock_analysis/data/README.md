# 📊 数据服务层 (Data Service Layer)

数据服务层是股票分析系统的核心数据管理模块，负责数据获取、存储、处理和服务协调。

## 🚀 快速开始

### 推荐使用方式 - DataService
```python
from stock_analysis.data import DataService
from stock_analysis.data.config import DataServiceConfig

# 创建数据服务（使用混合下载策略）
config = DataServiceConfig.from_env()  # 从环境变量加载配置
service = DataService(config=config)

# 智能下载并入库（自动选择最佳策略）
result = service.download_and_store_stock_data("AAPL")
print(f"使用策略: {result.used_strategy}")
print(f"数据点数: {result.data_points}")

# 下载财务数据
financial_result = service.download_and_store_financial_data("AAPL")

# 批量下载
symbols = ['AAPL', 'GOOG', 'MSFT']
results = service.batch_download_and_store(symbols, include_financial=True)
```

## 📁 模块结构

```
stock_analysis/data/
├── __init__.py                      # 📦 包初始化和便捷API
├── data_service.py                  # 🏢 核心数据服务类
├── config.py                        # ⚙️ 配置管理
├── models/                          # 📋 数据模型定义
│   ├── __init__.py
│   ├── base_models.py               # 基础模型
│   ├── price_models.py              # 价格数据模型  
│   ├── financial_models.py          # 财务数据模型
│   └── quality_models.py            # 质量评估模型
├── downloaders/                     # 📥 下载器模块
│   ├── __init__.py                  
│   ├── base.py                      # 🏗️ 下载器抽象基类
│   ├── finnhub.py                   # 📈 Finnhub API下载器
│   └── stooq.py                     # 📊 Stooq数据下载器
├── storage/                         # 💾 存储层
│   ├── __init__.py
│   ├── base.py                      # 存储抽象基类
│   └── sqlite_storage.py            # SQLite存储实现
```
```

## 🧩 核心组件功能

### 🏢 `data_service.py` - 核心数据服务
**混合下载策略的中央协调服务**
- 智能选择数据源：100天阈值判断增量 vs 批量
- 统一的错误处理和日志记录

**混合下载策略:**
```
股票数据策略:
├── 首次下载 → Stooq批量历史数据
├── ≤100天 → Finnhub增量更新 (失败时回退Stooq)
└── >100天 → Stooq批量重新下载

财务数据策略:
└── 全部使用Finnhub (带90天刷新阈值)
```

### 📈 `downloaders/finnhub.py` - Finnhub API下载器
**专业级财务和价格数据下载器**
- 支持股票价格数据 (`/stock/candle`)
- 财务报表数据 (`/stock/financials-reported`, `/stock/profile2`)
- 自动重试和错误处理
- API密钥认证

**主要功能:**
- 日线价格数据下载
- 综合财务报表 (损益表、资产负债表、现金流)
- 公司基本信息
- 多期财务数据处理

### 📊 `downloaders/stooq.py` - Stooq数据下载器  
**专用于历史价格数据下载**
- 免费且稳定的历史数据源
- 适合大批量历史数据下载
- 长期价格趋势数据获取
- CSV格式数据处理

### 💾 `storage/sqlite_storage.py` - SQLite存储层
**规范化的数据存储实现**
- 分离式财务数据存储 (三张独立表)
- 完整的CRUD操作支持
- 事务管理和数据完整性
- 查询优化和索引

**数据库表结构:**
```sql
-- 股票基本信息
stocks (symbol, company_name, sector, ...)

-- 价格数据
stock_prices (symbol, date, open, high, low, close, volume, ...)

-- 财务数据 (分离存储)
income_statement (symbol, period, revenue, net_income, ...)
balance_sheet (symbol, period, total_assets, equity, ...)  
cash_flow (symbol, period, operating_cf, free_cf, ...)
```

### ⚙️ `config.py` - 配置管理
**集中化的配置管理**
- 环境变量支持
- 下载器参数配置
- 阈值和策略配置

**主要配置项:**
```python
# 关键配置参数
stock_incremental_threshold_days: int = 100  # 增量更新阈值
financial_refresh_days: int = 90             # 财务数据刷新阈值
max_retries: int = 3                         # 最大重试次数
base_delay: int = 30                         # 基础延迟时间
```

## 🔧 环境变量配置

```bash
# 必需配置
export FINNHUB_API_KEY="your_finnhub_api_key"

# 可选配置
export DATA_SERVICE_DB_PATH="database/stock_data.db"
export DATA_SERVICE_STOCK_INCREMENTAL_THRESHOLD_DAYS="100"
export DATA_SERVICE_FINANCIAL_REFRESH_DAYS="90"
export DATA_SERVICE_MAX_RETRIES="3"
export DATA_SERVICE_LOG_LEVEL="INFO"
```

## 📋 API 参考

### 基础使用
```python
from stock_analysis.data import DataService
from stock_analysis.data.config import DataServiceConfig

# 1. 基本初始化
service = DataService()

# 2. 带配置初始化
config = DataServiceConfig.from_env()
service = DataService(config=config)

# 3. 自定义配置
config = DataServiceConfig(
    downloader=DownloaderConfig(
        stock_incremental_threshold_days=50,
        financial_refresh_days=60
    )
)
service = DataService(config=config)
```

### 数据下载
```python
# 下载股票价格数据
result = service.download_and_store_stock_data('AAPL')
print(f"策略: {result.used_strategy}")
print(f"数据点: {result.data_points}")

# 下载财务数据  
financial_result = service.download_and_store_financial_data('AAPL')

# 批量下载 (推荐)
symbols = ['AAPL', 'GOOG', 'MSFT']
batch = service.batch_download_and_store(
    symbols, 
    include_financial=True,
    start_date='2020-01-01'
)

# 检查批量结果
print(f"成功: {batch.successful}/{batch.total}")
for symbol, res in batch.results.items():
    if res.success:
        print(f"✅ {symbol}: {res.used_strategy or 'N/A'}")
    else:
        print(f"❌ {symbol}: {res.error_message or 'Unknown error'}")
```

### 数据查询
```python
# 获取已有股票列表
symbols = service.get_existing_symbols()

# 获取最后更新日期  
last_date = service.get_last_update_date('AAPL')

 # 其他查询参见 storage 接口
```

## 🎯 混合下载策略详解

### 策略决策流程
```python
def determine_download_strategy(symbol, last_update_date):
    if last_update_date is None:
        return "Stooq批量历史数据"  # 首次下载
    
    days_since_last = calculate_days(last_update_date)
    threshold = config.stock_incremental_threshold_days  # 默认100天
    
    if days_since_last <= threshold:
        return "Finnhub增量更新"     # 近期数据，增量更新
    else:
        return "Stooq批量重新下载"   # 数据过旧，批量更新
```



## 🏗️ 扩展开发

### 添加新数据源
1. 继承 `BaseDownloader`
2. 实现必需的抽象方法
3. 在DataService中集成新下载器

```python
from stock_analysis.data.downloaders.base import BaseDownloader

class NewAPIDownloader(BaseDownloader):
    def download_stock_data(self, symbol, start_date=None, end_date=None):
        # 实现下载逻辑
        pass
        
    def download_financial_data(self, symbol):
        # 实现财务数据下载
        pass
```

### 自定义存储后端
```python
from stock_analysis.data.storage.base import BaseStorage

class CustomStorage(BaseStorage):
    def store_stock_data(self, symbol, data):
        # 实现存储逻辑
        pass
```

## 🛡️ 错误处理和最佳实践

### 错误处理
```python
# 总是检查返回结果
result = service.download_and_store_stock_data("INVALID_SYMBOL")
if not result.success:
    print(f"下载失败: {result.error_message}")
    # 处理错误...
```

### 批量操作最佳实践
```python
# ✅ 推荐：批量操作
batch = service.batch_download_and_store(symbols, include_financial=True)

# ❌ 避免：循环单个操作
for symbol in symbols:
    service.download_and_store_stock_data(symbol)
    service.download_and_store_financial_data(symbol)  # 效率低
```

### 资源管理
```python
# 记得关闭服务释放资源
try:
    service = DataService()
    # ... 使用服务
finally:
    service.close()
```

## 📊 监控和调试

### 日志配置
```python
import logging
logging.basicConfig(level=logging.INFO)

# 查看详细的下载过程
service = DataService()
result = service.download_and_store_stock_data("AAPL")
# 日志输出: [INFO] 📈 开始下载并存储 AAPL 股票数据
# 日志输出: [INFO] 使用策略: Finnhub增量更新
```

### 配置检查
```python
# 查看当前配置
config = DataServiceConfig.from_env()
print(f"增量阈值: {config.downloader.stock_incremental_threshold_days}天")
print(f"数据库路径: {config.database.db_path}")
```

---

这个数据服务层通过混合下载策略和智能决策机制，为股票分析系统提供了高效可靠的数据基础设施。模块化设计和配置化管理使得系统易于维护和扩展。
