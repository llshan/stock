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

### 安装依赖（源码运行）

```bash
# 克隆项目
git clone <repository-url>
cd Stock

# 安装依赖（推荐固定版本）
pip install -r requirements.txt
```

## 🎮 使用方法

### 🔥 推荐：综合分析系统

**直接运行模块（源码）:**
```bash
# 综合分析（示例，可作为样例运行）
python -m Stock.analysis_service.comprehensive_analyzer

# 数据管理器（下载/初始化/更新）- 示例：下载两只股票
python tools/data_manager.py download -s AAPL MSFT
```

**编程方式使用:**
```python
from Stock.analysis_service import ComprehensiveStockAnalyzer

analyzer = ComprehensiveStockAnalyzer()
symbols = ["AAPL", "GOOGL", "MSFT", "TSLA"]
results = analyzer.run_comprehensive_analysis(symbols, period="1y")
```

### 📊 数据下载和管理

**在代码中调用模块:**
```python
from Stock.data_service import DataService, create_storage

# 创建服务（价格数据统一走 Hybrid）
storage = create_storage('sqlite', db_path="stocks.db")
service = DataService(storage)

# 下载数据
result = service.download_and_store_stock_data("AAPL")
```

### 💼 按需启用算子
```python
from analysis_service import run_analysis_for_symbols
results = run_analysis_for_symbols(
    ["AAPL"], db_path='database/stock_data.db',
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
from Stock.data_service import HybridDataDownloader, create_storage

# 创建数据管理器（价格统一走 Hybrid）
storage = create_storage('sqlite', db_path="stocks.db")
manager = HybridDataDownloader(storage)

# 多只股票时：在应用层逐只调用
symbols = ['AAPL', 'GOOGL', 'MSFT']
results = {s: manager.download_stock_data(s) for s in symbols}
```

（已移除旧版：不再提供 yfinance 直连与图表生成功能）

### 🎯 高级自定义

```python
from analysis_service import ComprehensiveStockAnalyzer
analyzer = ComprehensiveStockAnalyzer(db_path='database/stock_data.db', enabled_operators=['ma','rsi','drop_alert','fin_ratios','fin_health'])
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
├── 📊 analysis_service/         # 核心分析模块包
│   ├── __init__.py                     # 包初始化
│   ├── comprehensive_analyzer.py       # 🔥 综合分析系统（封装流水线调用）
│   ├── app/
│   │   └── runner.py                  # 流水线运行入口（构建算子/执行/汇总）
│   ├── data/
│   │   ├── price_repository.py        # 价格数据仓储（OHLCV）
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
├── tools/                       # 工具脚本
│   └── data_manager.py          # 📊 数据管理命令行工具
 
├── requirements.txt            # 依赖包列表
├── README.md                   # 项目说明文档 (本文件)
└── result/                     # 📁 分析结果输出文件夹
    ├── {股票}_candlestick.html          # K线图
    ├── {股票}_financial_metrics.png     # 财务指标图
    ├── {股票}_health_dashboard.html     # 健康仪表盘
    └── ... (其他图表文件)
```

（云端部署相关文件与入口已移除，专注本地分析与数据管理）

## 🔧 故障排除

### 日志初始化
在脚本或入口处可初始化统一日志：
```python
from utils.logging_utils import setup_logging
setup_logging()
```

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
