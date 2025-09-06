# 📊 股票分析模块

此目录包含所有股票分析相关的核心模块。

## 📁 模块结构

```
analyzer/
├── __init__.py                      # 📦 包初始化文件
├── stock_analyzer.py                # 📈 技术分析模块 (含价格下跌监控)
├── financial_analyzer.py            # 💼 财务分析模块
├── comprehensive_analyzer.py        # 🎯 综合分析模块
└── README.md                        # 📄 本文件
```

## 🧩 模块功能

### 📈 `stock_analyzer.py`
**技术分析核心模块**
- `StockDataFetcher`: 实时和历史数据获取
- `StockAnalyzer`: 技术指标计算 (RSI, MA, 布林带等)
- `ChartGenerator`: 技术分析图表生成
- 价格下跌检测功能

**主要功能:**
- 实时股价数据获取
- 技术指标计算 (MA5/10/20/50, RSI, 布林带)
- K线图、RSI图、布林带图生成
- 价格下跌警告系统

### 💼 `financial_analyzer.py` 
**财务分析核心模块**
- `FinancialDataFetcher`: 财务报表数据获取
- `FinancialAnalyzer`: 财务比率计算和健康评估
- `FinancialChartGenerator`: 财务分析图表生成

**主要功能:**
- 财务报表数据获取 (损益表、资产负债表、现金流量表)
- 财务比率计算 (ROE, ROA, 市盈率, 负债率等)
- 财务健康评分和等级评定
- 营收趋势图、财务指标图、健康仪表盘

### 🎯 `comprehensive_analyzer.py`
**综合分析系统**
- `ComprehensiveStockAnalyzer`: 技术+财务双重分析

**主要功能:**
- 整合技术分析和财务分析
- 智能投资评级系统 (A-F级)
- 生成综合投资建议
- 一键生成完整分析报告


## 🔧 使用方式

### 作为包导入
```python
from analyzer import StockAnalyzer, FinancialAnalyzer, ComprehensiveStockAnalyzer

# 或者
from analyzer.stock_analyzer import StockAnalyzer
from analyzer.comprehensive_analyzer import ComprehensiveStockAnalyzer
```

### 直接运行模块
```bash
# 运行综合分析
python analyzer/comprehensive_analyzer.py

# 技术分析 (包含价格下跌监控功能)
python analyzer/stock_analyzer.py
```

## 📊 模块依赖关系

```
comprehensive_analyzer.py
├── stock_analyzer.py (含价格下跌监控)
└── financial_analyzer.py

stock_analyzer.py
└── (外部依赖: yfinance, pandas, matplotlib, plotly)

financial_analyzer.py
└── (外部依赖: yfinance, pandas, matplotlib, plotly)
```

## 🎮 快速开始

### 1. 技术分析
```python
from analyzer import StockAnalyzer, StockDataFetcher

fetcher = StockDataFetcher()
analyzer = StockAnalyzer(fetcher)

# 技术分析
result = analyzer.analyze_stock("AAPL", period="6mo")
print(f"趋势: {result['trend']}")
print(f"RSI: {result['rsi']:.2f}")

# 价格下跌检测
drop_result = analyzer.check_price_drop("AAPL", days=1, threshold_percent=15.0)
if drop_result['is_drop_alert']:
    print(f"警告: {drop_result['alert_message']}")
```

### 2. 财务分析
```python
from analyzer import FinancialAnalyzer, FinancialDataFetcher

fetcher = FinancialDataFetcher()
analyzer = FinancialAnalyzer(fetcher)

# 财务比率分析
ratios = analyzer.calculate_financial_ratios("AAPL")
print(f"净利润率: {ratios['ratios']['net_profit_margin']:.2f}%")

# 财务健康评估
health = analyzer.analyze_financial_health("AAPL")
print(f"健康等级: {health['grade']}")
```

### 3. 综合分析
```python
from analyzer import ComprehensiveStockAnalyzer

analyzer = ComprehensiveStockAnalyzer()
results = analyzer.run_comprehensive_analysis(["AAPL", "GOOGL"], period="1y")

for symbol, data in results.items():
    report = data['comprehensive_report']
    print(f"{symbol}: {report['overall_rating']} - {report['investment_recommendation']}")
```

### 4. 价格下跌监控
```python
from analyzer import StockAnalyzer, StockDataFetcher

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

## ⚙️ 配置说明

### 数据源
- **股价数据**: Yahoo Finance (通过 yfinance)
- **财务数据**: Yahoo Finance 财务报表
- **更新频率**: 实时获取 (有API限制)

### 技术指标参数
- **移动平均线**: MA5, MA10, MA20, MA50
- **RSI 周期**: 14天
- **布林带**: 20天周期，2倍标准差

### 财务指标
- **盈利能力**: 净利润率、ROE、ROA
- **偿债能力**: 负债率、流动比率  
- **估值指标**: 市盈率、市净率
- **成长指标**: 营收增长率、利润增长率

### 评级系统
- **A级 (80-100分)**: 强烈推荐 - 买入
- **B级 (60-79分)**: 推荐 - 买入/持有  
- **C级 (40-59分)**: 中性 - 持有
- **D级 (20-39分)**: 不推荐 - 减持
- **F级 (0-19分)**: 强烈不推荐 - 卖出

## 🛠️ 开发注意事项

### 相对导入处理
模块支持两种使用方式：
1. **作为包导入** - 使用相对导入 (`from .module import Class`)
2. **直接运行** - 自动处理路径并使用绝对导入

### 错误处理
- 网络连接错误处理
- API 限制处理  
- 数据缺失处理
- 股票代码无效处理

### 性能优化
- 批量数据获取
- 缓存机制 (避免重复请求)
- 延迟处理 (避免API限制)

## 📈 输出文件

各模块生成的文件会保存到 `results/` 目录:
- `{股票代码}_candlestick.html`: K线图
- `{股票代码}_rsi.png`: RSI指标图
- `{股票代码}_bollinger.html`: 布林带图
- `{股票代码}_financial_metrics.png`: 财务指标图
- `{股票代码}_health_dashboard.html`: 财务健康仪表盘
- `{股票代码}_revenue_trend.html`: 营收趋势图