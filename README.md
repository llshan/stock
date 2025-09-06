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

### 🎯 综合分析系统 (新增)
1. **技术+财务双重分析**：结合价格走势和基本面
2. **智能评级系统**：A-F五级评定
3. **投资建议生成**：买入/持有/卖出建议
4. **风险提示**：识别潜在投资风险
5. **综合报告**：生成专业投资分析报告

## 安装依赖

```bash
pip install -r requirements.txt
```

## 🎮 使用方法

### 🔥 推荐：综合分析系统

**基本使用:**
```bash
python comprehensive_analyzer.py
```

**自定义分析:**
```python
from comprehensive_analyzer import ComprehensiveStockAnalyzer

analyzer = ComprehensiveStockAnalyzer()
symbols = ["AAPL", "GOOGL", "MSFT", "TSLA"]
results = analyzer.run_comprehensive_analysis(symbols, period="1y")
```

### 📊 单独技术分析

```bash
python stock_analyzer.py
```

### 💼 单独财务分析

```python
from financial_analyzer import FinancialAnalyzer, FinancialDataFetcher

fetcher = FinancialDataFetcher()
analyzer = FinancialAnalyzer(fetcher)

# 财务比率分析
ratios = analyzer.calculate_financial_ratios("AAPL")
print(f"净利润率: {ratios['ratios']['net_profit_margin']:.2f}%")

# 财务健康评估
health = analyzer.analyze_financial_health("AAPL")
print(f"财务健康等级: {health['grade']}")
```

### 🎯 高级自定义

```python
from comprehensive_analyzer import ComprehensiveStockAnalyzer

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

程序会在 `analytics/` 文件夹中生成以下文件：

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
├── comprehensive_analyzer.py    # 🔥 综合分析系统 (主程序)
├── financial_analyzer.py       # 💼 财务分析模块
├── stock_analyzer.py           # 📊 技术分析模块
├── requirements.txt            # 依赖包列表
├── README.md                   # 项目说明文档
└── analytics/                  # 📁 分析结果输出文件夹
    ├── {股票}_candlestick.html          # K线图
    ├── {股票}_financial_metrics.png     # 财务指标图
    ├── {股票}_health_dashboard.html     # 健康仪表盘
    └── ... (其他图表文件)
```

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