# 批次级别交易追踪系统使用指南

## 概述

本系统实现了精确的批次级别(Lot-Level)股票交易追踪，相比传统的平均成本法，能够提供更准确的成本基础计算和税务申报支持。

## 核心概念

### 批次 (Position Lot)
每次买入交易会创建一个独立的批次，记录：
- 原始数量 (Original Quantity)
- 剩余数量 (Remaining Quantity)  
- 成本基础 (Cost Basis)
- 购买日期 (Purchase Date)
- 状态 (开放/关闭)

### 成本基础方法
系统支持四种成本基础方法：
- **FIFO (先进先出)**：税务最常用，按购买日期从早到晚匹配
- **LIFO (后进先出)**：按购买日期从晚到早匹配
- **SpecificLot (指定批次)**：手动指定卖出特定批次，提供最大灵活性
- **AverageCost (平均成本)**：向后兼容的传统方法

### 卖出分配 (Sale Allocation)
每次卖出交易会创建分配记录，详细记录：
- 来源批次
- 卖出数量
- 成本基础
- 已实现盈亏
- 佣金分摊

## CLI命令使用

### 基础交易操作

#### 记录买入交易
```bash
# 基础买入
stock-trading buy --user-id user1 -s AAPL -q 100 -p 150.5 -d 2024-01-15 --commission 9.95

# 带外部ID的买入（用于去重）
stock-trading buy --user-id user1 -s AAPL -q 50 -p 155.0 -d 2024-01-20 --external-id "order_123456"
```

#### 记录卖出交易
```bash
# 默认FIFO卖出
stock-trading sell --user-id user1 -s AAPL -q 30 -p 160.0 -d 2024-02-01

# 指定成本基础方法
stock-trading sell --user-id user1 -s AAPL -q 20 -p 165.0 -d 2024-02-05 --basis lifo

# 指定特定批次卖出
stock-trading sell --user-id user1 -s AAPL -q 30 -p 160.0 -d 2024-02-01 --basis specific --specific-lots "lot=1:20,lot=3:10"
```

### 查看持仓和批次

#### 查看当前持仓汇总
```bash
stock-trading positions --user-id user1
```

#### 查看详细批次信息
```bash
# 查看所有批次
stock-trading lots --user-id user1

# 查看特定股票的批次
stock-trading lots --user-id user1 -s AAPL
```

#### 查看卖出分配历史
```bash
# 查看所有卖出分配
stock-trading sales --user-id user1

# 查看特定股票的卖出分配
stock-trading sales --user-id user1 -s AAPL
```

### 盈亏计算

#### 计算单日盈亏
```bash
stock-trading calculate-pnl --user-id user1 --date 2024-02-20
```

#### 批量计算历史盈亏
```bash
stock-trading batch-calculate --user-id user1 --start-date 2024-01-01 --end-date 2024-02-29
```

#### 每日自动盈亏计算
```bash
# 适合cron定时任务
stock-trading daily --user-id user1
```

### 高级分析功能

#### 投资组合摘要
```bash
# 当前投资组合
stock-trading portfolio --user-id user1

# 历史时点投资组合
stock-trading portfolio --user-id user1 --as-of-date 2024-02-15
```

#### 税务报告
```bash
# 年度税务报告
stock-trading tax-report --user-id user1 --start-date 2024-01-01 --end-date 2024-12-31

# 季度税务报告  
stock-trading tax-report --user-id user1 --start-date 2024-01-01 --end-date 2024-03-31
```

#### 成本基础方法模拟
```bash
# 模拟不同方法的税负影响
stock-trading rebalance-simulate --user-id user1 -s AAPL -q 50 -p 180.0
```

## 成本基础方法选择指南

### FIFO (先进先出)
**优点：**
- 税务部门普遍接受
- 简单易懂
- 在价格上涨市场中实现损失较小

**缺点：**
- 在价格上涨时产生更高的资本利得税

**适用场景：**
- 长期投资策略
- 税务合规要求严格的情况

### LIFO (后进先出)
**优点：**
- 在价格上涨市场中可以减少资本利得税
- 适合短期交易策略

**缺点：**
- 部分税务管辖区不允许
- 复杂度较高

**适用场景：**
- 短期交易
- 需要税务优化的情况

### SpecificLot (指定批次)
**优点：**
- 最大的灵活性
- 可以精确控制税务影响
- 适合复杂的税务筹划

**缺点：**
- 需要仔细记录和管理
- 操作复杂度最高

**适用场景：**
- 专业投资者
- 需要精确税务筹划
- 有专业会计支持

### AverageCost (平均成本)
**优点：**
- 简单易懂
- 适合基金投资

**缺点：**
- 精确度不如批次方法
- 税务申报支持有限

**适用场景：**
- 基金投资
- 简单的投资组合

## 最佳实践

### 1. 数据录入
- **及时录入**：尽快录入交易数据，避免遗忘
- **使用外部ID**：为每笔交易设置唯一的外部ID，便于对账和去重
- **详细备注**：在notes字段记录重要信息

### 2. 成本基础选择
- **一致性**：对同一股票使用一致的成本基础方法
- **文档记录**：记录选择特定方法的原因
- **定期审查**：定期审查是否需要调整策略

### 3. 税务管理
- **定期报告**：定期生成税务报告
- **专业咨询**：复杂情况下咨询税务专业人士
- **记录保存**：保留完整的交易记录和计算过程

### 4. 数据验证
- **定期检查**：使用一致性检查功能验证数据
- **备份数据**：定期备份交易数据
- **对账验证**：与券商记录定期对账

## 常见问题解答

### Q: 如何处理股票拆分？
A: 系统目前不自动处理股票拆分，需要手动调整批次数据。建议在股票拆分时：
1. 记录拆分事件
2. 按比例调整数量和价格
3. 保持总成本基础不变

### Q: 如何处理股息？
A: 股息不影响批次数据，建议单独记录股息收入用于税务申报。

### Q: 卖出数量超过持仓怎么办？
A: 系统会阻止此类交易并报错。请检查：
1. 持仓数据是否准确
2. 是否有未记录的买入交易
3. 数量计算是否正确

### Q: 如何修正错误的交易记录？
A: 目前系统不支持直接修改交易记录。建议：
1. 记录冲销交易
2. 重新录入正确交易
3. 在备注中说明原因

### Q: 系统支持哪些股票市场？
A: 系统理论上支持任何股票市场，只需要确保股票代码的一致性。

## 技术支持

如遇到技术问题，请：
1. 检查错误信息和日志
2. 验证数据一致性
3. 查阅API文档
4. 联系技术支持团队

## 更新日志

### v2.0.0 (批次级别系统)
- 新增批次级别交易追踪
- 支持FIFO/LIFO/SpecificLot成本基础方法
- 新增税务报告功能
- 新增成本基础模拟功能
- 性能优化和批量查询支持

### v1.x (传统平均成本系统)
- 基础交易记录
- 平均成本计算
- 简单盈亏分析