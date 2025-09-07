# 综合股票分析系统

一个功能强大的股票分析工具，结合技术分析和财务分析，提供全方位的投资决策支持。

## 🚀 核心功能

### 📈 技术分析模块
1. **实时数据获取**：获取股票的实时价格和交易信息
2. **历史数据分析**：下载和分析历史价格数据
3. **技术指标计算**：
   - 移动平均线 (MA5, MA10, MA20, MA50)
   - 相对强弱指数 (RSI)
   - 布林带 (Bollinger Bands)
4. **技术图表生成**：
   - K线图 (蜡烛图)
   - RSI指标图
   - 布林带图表

### 💼 财务分析模块 (新增)
1. **财务数据获取**：获取过去5年的财务报表数据
2. **财务指标计算**：
   - 盈利能力：净利润率、ROE、ROA
   - 偿债能力：负债率、流动比率
   - 估值指标：市盈率(PE)、市净率(PB)
   - 成长性：营收增长率、利润增长率
3. **财务健康评估**：综合评分和等级评定
4. **财务图表生成**：
   - 营收趋势图
   - 财务指标对比图
   - 健康评分仪表盘

### 🎯 综合分析系统
1. **技术+财务双重分析**：结合价格走势和基本面
2. **智能评级系统**：A-F五级评定
3. **投资建议生成**：买入/持有/卖出建议
4. **风险提示**：识别潜在投资风险
5. **综合报告**：生成专业投资分析报告

### 💾 历史数据管理系统 (新增)
1. **完整数据下载**：从2020年开始的所有价格和财务数据
2. **结构化存储**：SQLite/PostgreSQL数据库存储
3. **数据质量监控**：自动评估数据完整性和质量
4. **批量管理**：支持多股票批量下载和更新
5. **GCP云端部署**：支持Cloud SQL数据库

## 🚀 快速开始

### 方法1：开发模式安装（推荐）

```bash
# 克隆项目
git clone <repository-url>
cd Stock

# 开发模式安装（可编辑安装）
pip install -e .

# 或者安装依赖
pip install -r requirements.txt
```

### 方法2：正式安装

```bash
# 构建并安装
pip install .

# 或从PyPI安装（如果已发布）
pip install stock-analysis
```

## 🎮 使用方法

### 🔥 推荐：综合分析系统

**使用python -m模块运行:**
```bash
# 综合分析（示例）
python -m Stock.analyzer.comprehensive_analyzer

# 数据下载
python -m Stock.data_service.downloaders.yfinance

# 数据管理器（原混合下载器）
python -m Stock.data_service.downloaders.hybrid
```

**使用命令行工具:**
```bash
# 如果已安装包，可以直接使用命令行工具
stock-analyze        # 综合分析
stock-download       # yfinance下载器
stock-hybrid         # 数据管理器（原混合下载器）
```

**编程方式使用:**
```python
from Stock.analyzer import ComprehensiveStockAnalyzer

analyzer = ComprehensiveStockAnalyzer()
symbols = ["AAPL", "GOOGL", "MSFT", "TSLA"]
results = analyzer.run_comprehensive_analysis(symbols, period="1y")
```

### 📊 数据下载和管理

**使用包模块:**
```python
from Stock.data_service import DataService, StockDatabase, YFinanceDataDownloader

# 创建服务
database = StockDatabase("stocks.db")
downloader = YFinanceDataDownloader()
service = DataService(database, downloader)

# 下载数据
result = service.download_and_store_stock_data("AAPL")
```

### 💼 按需启用算子
```python
from analyzer import run_analysis_for_symbols
results = run_analysis_for_symbols(
    ["AAPL"], db_path='stock_data.db',
    enabled_operators=['ma','rsi','drop_alert','drop_alert_7d','fin_ratios','fin_health']
)
print(results['AAPL']['operators']['fin_ratios'])
```

### 💾 数据管理的新方式

**使用混合下载器（推荐）:**
```bash
# 使用python -m运行混合下载器
python -m Stock.data_service.downloaders.hybrid

# 或使用命令行工具
stock-hybrid
```

**编程方式使用:**
```python
from Stock.data_service import DataManager, StockDatabase

# 创建数据管理器
database = StockDatabase("stocks.db")
manager = DataManager(database)

# 智能批量下载（自动选择最佳数据源）
symbols = ['AAPL', 'GOOGL', 'MSFT']
results = manager.batch_download(symbols)
```

（已移除旧版：不再提供 yfinance 直连与图表生成功能）

### 🎯 高级自定义

```python
from analyzer import ComprehensiveStockAnalyzer
analyzer = ComprehensiveStockAnalyzer(db_path='stock_data.db', enabled_operators=['ma','rsi','drop_alert','fin_ratios','fin_health'])
results = analyzer.run_comprehensive_analysis(["AAPL","NVDA"], period="6mo")
for symbol, data in results.items():
    print(symbol, data['summary'])
```

## 📁 输出
仅文本日志与结构化结果（dict/JSON）。无图表输出。

## 📖 指标说明

### 📈 技术指标
- **移动平均线 (MA)**: MA5, MA20, MA50 用于判断趋势方向
- **RSI (相对强弱指数)**: 0-100区间，>70超买，<30超卖
- **布林带**: 上中下轨反映价格波动性和支撑阻力位

### 💼 财务指标 (新增)
- **盈利能力**: 净利润率、ROE(净资产收益率)、ROA(资产收益率)
- **偿债能力**: 负债率、流动比率
- **估值指标**: 市盈率(PE)、市净率(PB)
- **成长性**: 营收和利润增长率

### 🎯 综合评级系统 (新增)
- **A级 (80-100分)**: 强烈推荐 - 买入
- **B级 (60-79分)**: 推荐 - 买入/持有
- **C级 (40-59分)**: 中性 - 持有
- **D级 (20-39分)**: 不推荐 - 减持
- **F级 (0-19分)**: 强烈不推荐 - 卖出

## 📂 项目结构（节选）

```
Stock/
├── 📊 analyzer/                 # 核心分析模块包
│   ├── __init__.py                     # 包初始化
│   ├── comprehensive_analyzer.py       # 🔥 综合分析系统（封装流水线调用）
│   ├── app/
│   │   └── runner.py                  # 流水线运行入口（构建算子/执行/汇总）
│   ├── data/
│   │   ├── repository.py              # 行情数据仓储（OHLCV）
│   │   └── financial_repository.py    # 财务数据仓储（报表透视）
│   ├── operators/                     # 可插拔算子
│   │   ├── base.py                    # Operator 抽象
│   │   ├── ma.py                      # 移动平均
│   │   ├── rsi.py                     # RSI
│   │   ├── drop_alert.py              # 1天跌幅预警
│   │   ├── drop_alert_7d.py           # 7天跌幅预警
│   │   ├── fin_ratios.py              # 财务比率
│   │   └── fin_health.py              # 财务健康度
│   ├── pipeline/
│   │   ├── context.py                 # 分析上下文
│   │   └── engine.py                  # 执行引擎
│   └── README.md                       # 模块说明文档
├── 🌥️ cloud/                   # GCP 部署文件夹
│   ├── deploy.sh                       # 🚀 自动部署脚本
│   ├── monitor.sh                      # 📊 系统监控脚本
│   ├── test_local.py                   # 🧪 本地测试脚本
│   ├── cloudbuild.yaml                 # ☁️ Cloud Build 配置
│   ├── database_setup.py               # 🗄️ GCP数据库配置
│   ├── GCP_DEPLOYMENT_GUIDE.md         # 📖 GCP 部署指南
│   └── README.md                       # Cloud 目录说明
├── main.py                      # 🌥️ GCP Cloud Function 入口点
├── data_manager.py              # 📊 数据管理命令行工具
├── data_downloader_function.py # 💾 独立数据下载Cloud Function
├── requirements.txt            # 依赖包列表
├── README.md                   # 项目说明文档 (本文件)
└── results/                    # 📁 分析结果输出文件夹
    ├── {股票}_candlestick.html          # K线图
    ├── {股票}_financial_metrics.png     # 财务指标图
    ├── {股票}_health_dashboard.html     # 健康仪表盘
    └── ... (其他图表文件)
```

**💡 为什么 `main.py` 在根目录？**
- `main.py` 是 GCP Cloud Function 的入口点，需要能够导入 `analyzer` 包
- GCP 部署时会包含整个项目根目录，确保所有模块都可用
- 这样的结构使得本地开发和云端部署都能正常工作

## 🔧 故障排除

### 网络问题
如果遇到网络连接问题或 Yahoo Finance API 限制：
1. 检查网络连接是否正常
2. 尝试更换网络环境
3. 程序会自动重试并给出错误提示

### 常见问题
1. **中文字体警告**: 属正常现象，不影响功能
2. **数据获取失败**: 检查股票代码是否正确，网络是否正常
3. **图表无法显示**: 确保浏览器支持HTML5
4. **财务数据缺失**: 某些股票可能没有完整的财务数据

## ⚠️ 重要声明

1. **数据来源**: 数据来自 Yahoo Finance，可能有延迟或不完整
2. **投资建议**: 本程序提供的分析仅供参考，不构成投资建议
3. **风险提示**: 股市有风险，投资需谨慎
4. **数据准确性**: 请以官方财报和实时行情为准

## 🎓 学习价值

本项目展示了以下技术栈和概念：
- **数据科学**: pandas, numpy 数据处理
- **可视化**: matplotlib, plotly 图表生成
- **金融分析**: 技术指标和财务比率计算
- **API集成**: yfinance 数据获取
- **软件工程**: 模块化设计、错误处理、文档编写
