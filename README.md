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
