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

## 安装依赖

```bash
pip install -r requirements.txt
```

## 🎮 使用方法

### 🔥 推荐：综合分析系统

**基本使用:**
```bash
python analyzer/comprehensive_analyzer.py
```

**自定义分析:**
```python
from analyzer import ComprehensiveStockAnalyzer

analyzer = ComprehensiveStockAnalyzer()
symbols = ["AAPL", "GOOGL", "MSFT", "TSLA"]
results = analyzer.run_comprehensive_analysis(symbols, period="1y")
```

### 📊 单独技术分析

```bash
python analyzer/stock_analyzer.py
```

### 💼 单独财务分析

```python
from analyzer import FinancialAnalyzer, FinancialDataFetcher

fetcher = FinancialDataFetcher()
analyzer = FinancialAnalyzer(fetcher)

# 财务比率分析
ratios = analyzer.calculate_financial_ratios("AAPL")
print(f"净利润率: {ratios['ratios']['net_profit_margin']:.2f}%")

# 财务健康评估
health = analyzer.analyze_financial_health("AAPL")
print(f"财务健康等级: {health['grade']}")
```

### ⚠️ 价格下跌监控

价格下跌监控功能已集成在技术分析和综合分析中：

```python
from analyzer import StockAnalyzer, StockDataFetcher

# 创建分析器
fetcher = StockDataFetcher()
analyzer = StockAnalyzer(fetcher)

# 单个股票下跌检测
result = analyzer.check_price_drop('AAPL', days=1, threshold_percent=15.0)
if result['is_drop_alert']:
    print(f"警告: {result['alert_message']}")

# 批量股票下跌检测
symbols = ['AAPL', 'GOOGL', 'MSFT']
results = analyzer.batch_check_price_drops(symbols, days=1, threshold_percent=15.0)
print(f"发现 {results['summary']['alerts_count']} 只股票触发警告")
```

### 💾 历史数据管理

**下载完整历史数据:**
```bash
# 下载预设观察清单的所有数据（从2020年开始）
python data_manager.py --use-watchlist --action download

# 下载特定股票的数据
python data_manager.py --symbols AAPL GOOGL MSFT --action download

# 更新已有股票的数据
python data_manager.py --symbols AAPL --action update
```

**数据质量报告:**
```bash
# 生成数据质量报告
python data_manager.py --action report

# 备份数据库
python data_manager.py --action backup --backup-path backup.db
```

**编程方式使用:**
```python
from data_service.yfinance_downloader import YFinanceDataDownloader
from data_service.database import StockDatabase

# 创建下载器和数据库
downloader = YFinanceDataDownloader()
database = StockDatabase("my_stock_data.db")

# 下载并存储数据
symbols = ['AAPL', 'GOOGL', 'MSFT']
for symbol in symbols:
    data = downloader.download_comprehensive_data(symbol, start_date="2020-01-01")
    if 'error' not in data:
        database.store_comprehensive_data(symbol, data)

# 查询历史数据
price_data = database.get_stock_prices('AAPL', '2023-01-01', '2023-12-31')
financial_data = database.get_financial_data('AAPL', 'income_statement')
```

### 🎯 高级自定义

```python
from analyzer import ComprehensiveStockAnalyzer

# 创建分析器
analyzer = ComprehensiveStockAnalyzer()

# 自定义股票列表和分析周期
symbols = ["AAPL", "AMZN", "NFLX", "META", "NVDA"]
results = analyzer.run_comprehensive_analysis(symbols, period="2y")

# 查看分析结果
for symbol, data in results.items():
    report = data['comprehensive_report']
    print(f"{symbol}: {report['overall_rating']} - {report['investment_recommendation']}")
    
    # 访问详细技术分析数据
    tech = data['technical_analysis']
    if 'error' not in tech:
        print(f"  RSI: {tech['rsi']:.2f}, 趋势: {tech['trend']}")
    
    # 访问详细财务分析数据
    fin = data['financial_analysis']
    if 'error' not in fin:
        ratios = fin['ratios']
        print(f"  净利润率: {ratios.get('net_profit_margin', 0):.2f}%")
```

## 📁 输出文件

程序会在 `results/` 文件夹中生成以下文件：

### 🎯 综合分析输出
**技术分析图表:**
- `{股票代码}_candlestick.html`: 交互式K线图
- `{股票代码}_rsi.png`: RSI指标图  
- `{股票代码}_bollinger.html`: 布林带图表

**财务分析图表:**
- `{股票代码}_revenue_trend.html`: 营收趋势图
- `{股票代码}_financial_metrics.png`: 财务指标分析图
- `{股票代码}_health_dashboard.html`: 财务健康仪表盘

### 📊 单独技术分析输出
- `{股票代码}_candlestick.html`: K线图
- `{股票代码}_rsi.png`: RSI指标图
- `{股票代码}_bollinger.html`: 布林带图表

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

## 📂 项目结构

```
Stock/
├── 📊 analyzer/                 # 核心分析模块包
│   ├── __init__.py                     # 包初始化
│   ├── stock_analyzer.py               # 📈 技术分析模块 (含价格下跌监控)
│   ├── financial_analyzer.py           # 💼 财务分析模块
│   ├── comprehensive_analyzer.py       # 🔥 综合分析系统
│   ├── data_downloader.py              # 💾 历史数据下载器
│   ├── database.py                     # 🗄️ 数据库存储模块
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
