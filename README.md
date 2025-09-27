# 股票分析与投资组合管理系统

一个现代化的股票数据获取、存储、分析和投资组合管理系统，采用模块化的 Python 包架构设计。

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Code Style](https://img.shields.io/badge/Code%20Style-Black-black.svg)](https://black.readthedocs.io)

## ✨ 核心特性

- **数据管理**: 智能获取和存储股票价格及公司财务数据。
- **技术分析**: 支持多种可插拔的技术指标分析算子。
- **批次会计法 (Lot-based Accounting)**: 完整的投资组合管理功能，精确追踪每一笔交易。
- **命令行工具 (CLI)**: 提供功能强大的 `stock-trading` CLI 用于所有交易管理操作。

---

## 📈 投资组合管理 (Trading System)

本项目的核心亮点之一是其完全实现的、基于批次会计法的投资组合管理系统。

### 功能亮点

- **精确成本追踪**: 每次买入都记录为一个独立的“批次” (Lot)，包含独立的成本基础（已分摊佣金），彻底告别平均成本法的估算。
- **灵活的卖出策略**: 卖出时可通过 `--basis` 参数指定成本计算方法，支持：
  - `FIFO`: 先进先出，按买入时间顺序卖出。
  - `LIFO`: 后进先出，按买入时间倒序卖出。
  - `SpecificLot`: 通过 `--specific-lots` 参数手动指定卖出任意批次和数量，实现最大程度的税务优化和策略灵活性。
- **准确的盈亏计算**: 无论是已实现盈亏（Realized PnL）还是未实现盈亏（Unrealized PnL），都基于精确的批次数据进行计算。
- **完整的审计追溯**: 每一笔卖出交易都会生成详细的分配记录 (`SaleAllocation`)，清晰展示其来源于哪些批次，便于审计和复核。

### CLI 使用指南

所有交易管理功能都通过 `stock-trading` 命令进行。

#### 1. 记录买入
每次买入都会自动创建一个新的持仓批次。
```bash
stock-trading buy --user-id u1 -s AAPL -q 100 -p 150.50 -d 2024-01-15 --commission 9.95
```

#### 2. 记录卖出

- **FIFO 卖出 (默认)**
```bash
stock-trading sell --user-id u1 -s AAPL -q 50 -p 160.25 -d 2024-02-20 --basis fifo
```

- **LIFO 卖出**
```bash
stock-trading sell --user-id u1 -s AAPL -q 30 -p 165.00 -d 2024-02-25 --basis lifo
```

- **指定批次 (Specific Lot) 卖出**
使用 `lot=<批次ID>:<数量>` 格式，多个批次用逗号分隔。
```bash
# 假设通过 stock-trading lots 命令查到批次ID为 1 和 2
stock-trading sell --user-id u1 -s AAPL -q 25 -p 170.00 -d 2024-03-01 --basis specific --specific-lots "lot=1:15,lot=2:10"
```

#### 3. 查看持仓与历史

- **查看持仓汇总** (基于批次实时计算)
```bash
stock-trading positions --user-id u1
```

- **查看持仓批次详情** (最常用！)
```bash
stock-trading lots --user-id u1 -s AAPL
```

- **查看卖出分配历史**
```bash
stock-trading sales --user-id u1 -s AAPL
```

#### 4. 盈亏计算

- **计算指定日期的盈亏**
```bash
stock-trading calculate-pnl --user-id u1 --date 2024-03-10
```

- **计算今日盈亏** (适合放入定时任务)
```bash
stock-trading daily --user-id u1
```

- **批量计算历史盈亏**
```bash
stock-trading batch-calculate --user-id u1 --start-date 2024-01-01 --end-date 2024-03-10
```

---

## 🚀 快速开始

### 1. 安装

```bash
# 克隆项目
git clone https://github.com/llshan/stock.git
cd stock

# (推荐) 创建并激活虚拟环境
python -m venv venv
source venv/bin/activate

# 安装依赖并以开发模式安装项目
pip install -e "."
```

### 2. 数据库迁移 (为已有数据库启用交易功能)

如果您是首次使用或使用的是一个旧的数据库，请运行以下命令来创建交易系统所需的表结构。

```bash
# 1. (建议) 备份现有数据库
cp database/stock_data.db database/stock_data.db.bak

# 2. 执行迁移脚本
python tools/migrate_add_trading_tables.py
```
此脚本会为您的数据库添加 `transactions`, `position_lots`, `sale_allocations` 等表，并自动从您已有的 `BUY` 交易历史中初始化批次数据。

### 3. 开始使用
完成安装和迁移后，您就可以开始使用 `stock-trading` 命令了。

---

## 🗃️ 其他模块

本系统同样包含强大的数据下载和分析功能。

### 数据下载
```bash
# 下载单只股票的综合数据（价格+财务）
stock-data download -s AAPL --comprehensive
```

### 技术分析
```bash
# 对AAPL进行为期1年的技术分析
stock-analyze -s AAPL --period 1y
```

## 🤝 贡献

欢迎各种形式的贡献！请参考 `CONTRIBUTING.md` (如果存在) 或直接提交 Pull Request。

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。