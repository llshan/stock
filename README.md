# 股票分析程序

一个功能完整的股票分析工具，支持实时数据获取、技术指标分析和图表生成。

## 功能特点

1. **实时数据获取**：获取股票的实时价格和交易信息
2. **历史数据分析**：下载和分析历史价格数据
3. **技术指标计算**：
   - 移动平均线 (MA5, MA10, MA20, MA50)
   - 相对强弱指数 (RSI)
   - 布林带 (Bollinger Bands)
4. **图表生成**：
   - K线图 (蜡烛图)
   - RSI指标图
   - 布林带图表

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### 基本使用

**真实数据版本 (需要网络连接):**
```bash
python stock_analyzer.py
```

**演示数据版本 (无需网络):**
```bash
python stock_analyzer_mock.py
```

默认分析 AAPL, GOOGL, MSFT, TSLA 四只股票。

### 自定义分析

**使用真实数据:**
```python
from stock_analyzer import StockAnalysisApp

app = StockAnalysisApp()
symbols = ["AAPL", "GOOGL"]
results = app.run_analysis(symbols, period="1y")
```

**使用演示数据:**
```python
from stock_analyzer_mock import MockStockAnalysisApp

app = MockStockAnalysisApp()
symbols = ["AAPL", "GOOGL"]
results = app.run_analysis(symbols, period="1y")
```

## 输出文件

程序会在 `analytics/` 文件夹中生成以下文件：

**真实数据版本:**
- `analytics/{股票代码}_candlestick.html`: 交互式K线图
- `analytics/{股票代码}_rsi.png`: RSI指标图
- `analytics/{股票代码}_bollinger.html`: 布林带图表

**演示数据版本:**
- `analytics/{股票代码}_candlestick_demo.html`: 交互式K线图 (演示数据)
- `analytics/{股票代码}_rsi_demo.png`: RSI指标图 (演示数据)
- `analytics/{股票代码}_bollinger_demo.html`: 布林带图表 (演示数据)

## 技术指标说明

### 移动平均线 (MA)
- MA5, MA20, MA50: 5日、20日、50日移动平均线
- 用于判断股价趋势方向

### RSI (相对强弱指数)
- 范围: 0-100
- > 70: 超买信号
- < 30: 超卖信号

### 布林带
- 上轨、中轨(MA20)、下轨
- 股价位置反映波动性和可能的买卖点

## 故障排除

如果遇到网络连接问题或 Yahoo Finance API 限制，请使用演示版本:
```bash
python stock_analyzer_mock.py
```

## 注意事项

1. **真实数据版本**：数据来源于 Yahoo Finance，可能有延迟或访问限制
2. **演示数据版本**：使用模拟数据，适合学习和测试功能
3. 技术指标仅供参考，不构成投资建议
4. 中文字体显示问题属正常现象，不影响功能