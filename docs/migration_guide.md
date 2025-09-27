# 批次级别系统迁移指南

## 概述

本指南帮助用户从传统平均成本系统升级到批次级别交易追踪系统。迁移过程包括数据备份、表结构升级、数据迁移和验证等步骤。

## 迁移前准备

### 1. 系统要求
- Python 3.8+
- SQLite 3.24+
- 足够的磁盘空间（建议预留原数据库大小的2倍）

### 2. 数据备份
```bash
# 备份原数据库文件
cp database/stock_data.db database/stock_data_backup_$(date +%Y%m%d_%H%M%S).db

# 导出关键数据为CSV（可选）
sqlite3 database/stock_data.db <<EOF
.headers on
.mode csv
.output backup_transactions.csv
SELECT * FROM transactions;
.output backup_positions.csv
SELECT * FROM positions;
.quit
EOF
```

### 3. 环境准备
```bash
# 创建迁移工作目录
mkdir -p migration_work
cd migration_work

# 安装依赖
pip install -r requirements.txt
```

## 迁移步骤

### 步骤1: 数据一致性检查

运行迁移前检查脚本：
```bash
python tools/pre_migration_check.py --db-path database/stock_data.db
```

检查项目包括：
- 交易记录完整性
- 持仓数据一致性
- 外键约束验证
- 数据类型校验

### 步骤2: 表结构升级

```bash
# 执行表结构升级脚本
python tools/migrate_add_trading_tables.py --db-path database/stock_data.db
```

此脚本会：
- 创建 `position_lots` 表
- 创建 `sale_allocations` 表
- 添加新的索引
- 更新现有表结构（如添加 `external_id` 字段）

### 步骤3: 数据迁移

```bash
# 执行数据迁移脚本
python tools/migrate_to_lot_tracking.py --db-path database/stock_data.db --dry-run

# 确认无误后执行实际迁移
python tools/migrate_to_lot_tracking.py --db-path database/stock_data.db
```

迁移过程：
1. **买入交易处理**：为每笔买入交易创建对应的批次记录
2. **卖出交易处理**：根据FIFO原则为历史卖出交易创建分配记录
3. **持仓重算**：基于批次数据重新计算持仓
4. **数据验证**：验证迁移后数据的一致性

### 步骤4: 迁移验证

#### 4.1 数据一致性验证
```bash
# 运行完整的数据验证
python tools/post_migration_validation.py --db-path database/stock_data.db
```

#### 4.2 功能测试
```bash
# 测试基础CLI功能
stock-trading positions --db-path database/stock_data.db
stock-trading lots --db-path database/stock_data.db
stock-trading sales --db-path database/stock_data.db
```

#### 4.3 数据对比
```bash
# 对比迁移前后的关键指标
python tools/compare_migration_results.py --db-path database/stock_data.db --backup-path database/stock_data_backup.db
```

## 迁移后配置

### 1. 更新应用配置

#### 1.1 启用批次级别功能
```python
# config.py
TRADING_CONFIG = {
    'enable_lot_tracking': True,
    'default_cost_basis_method': 'FIFO',
    'enable_precise_calculations': True,
    'decimal_precision': 4
}
```

#### 1.2 更新CLI别名
```bash
# 添加到 ~/.bashrc 或 ~/.zshrc
alias st='stock-trading'
alias st-lots='stock-trading lots'
alias st-sales='stock-trading sales' 
alias st-tax='stock-trading tax-report'
```

### 2. 设置定时任务

#### 2.1 每日盈亏计算
```bash
# 添加到crontab
# 每日凌晨2点计算盈亏
0 2 * * * /usr/bin/python /path/to/stock-trading daily >> /var/log/daily_pnl.log 2>&1
```

#### 2.2 数据一致性检查
```bash
# 每周日凌晨3点进行数据一致性检查
0 3 * * 0 /usr/bin/python /path/to/tools/consistency_check.py >> /var/log/consistency_check.log 2>&1
```

## 回滚计划

如果迁移过程中出现问题，可以使用以下回滚步骤：

### 1. 立即回滚
```bash
# 停止应用服务
sudo systemctl stop stock-trading-service

# 恢复备份数据库
cp database/stock_data_backup.db database/stock_data.db

# 重启应用服务  
sudo systemctl start stock-trading-service
```

### 2. 部分回滚
```bash
# 只回滚批次相关表，保留其他改进
python tools/rollback_lot_tracking.py --db-path database/stock_data.db
```

## 常见问题和解决方案

### Q1: 迁移过程中出现外键约束错误
**解决方案：**
```bash
# 临时禁用外键约束
python tools/migrate_to_lot_tracking.py --db-path database/stock_data.db --disable-foreign-keys
```

### Q2: 历史卖出交易无法正确分配到批次
**解决方案：**
1. 检查交易记录的完整性
2. 使用手动分配模式：
```bash
python tools/manual_allocation.py --db-path database/stock_data.db --symbol AAPL
```

### Q3: 迁移后持仓数量不匹配
**解决方案：**
1. 运行数据验证工具
2. 检查是否有遗漏的交易记录
3. 使用重算工具：
```bash
python tools/recalculate_positions.py --db-path database/stock_data.db
```

### Q4: 性能下降明显
**解决方案：**
1. 执行索引优化：
```bash
python tools/optimize_indexes.py --db-path database/stock_data.db
```
2. 启用查询缓存
3. 考虑归档老旧数据

## 性能优化建议

### 1. 数据库优化
```sql
-- 分析查询计划
EXPLAIN QUERY PLAN SELECT * FROM position_lots WHERE symbol = 'AAPL';

-- 更新统计信息
ANALYZE;

-- 重建索引（如果必要）
REINDEX;
```

### 2. 应用层优化
- 使用批量查询 API
- 启用结果缓存
- 实现分页查询
- 使用连接池

### 3. 数据归档
```bash
# 归档老旧的已关闭批次
python tools/archive_old_lots.py --db-path database/stock_data.db --older-than-days 365
```

## 监控和维护

### 1. 设置监控指标
- 数据库大小增长趋势
- 查询性能指标
- 数据一致性状态
- 批次数量统计

### 2. 定期维护任务
```bash
# 每月执行的维护脚本
#!/bin/bash
# monthly_maintenance.sh

# 数据一致性检查
python tools/consistency_check.py --db-path database/stock_data.db

# 性能分析
python tools/performance_analysis.py --db-path database/stock_data.db

# 数据归档
python tools/archive_old_data.py --db-path database/stock_data.db

# 生成月度报告
python tools/generate_monthly_report.py --db-path database/stock_data.db
```

## 联系支持

如果在迁移过程中遇到问题：

1. **查看日志文件**：`/var/log/migration.log`
2. **运行诊断工具**：`python tools/diagnose.py`
3. **收集系统信息**：`python tools/system_info.py`
4. **联系技术支持**：提供错误信息和诊断报告

## 迁移时间表模板

| 阶段 | 时间 | 任务 | 负责人 | 状态 |
|------|------|------|--------|------|
| 准备 | Week 1 | 环境准备、数据备份 | DevOps | ⏳ |
| 测试 | Week 2 | 测试环境迁移、功能验证 | QA | ⏳ |
| 迁移 | Week 3 | 生产环境迁移 | DevOps + Dev | ⏳ |
| 验证 | Week 4 | 数据验证、用户培训 | QA + BA | ⏳ |
| 上线 | Week 5 | 正式上线、监控 | All | ⏳ |

## 成功标准

迁移成功的标准：
- ✅ 所有历史交易数据成功迁移
- ✅ 批次数据与交易记录完全一致
- ✅ 持仓数量与迁移前保持一致
- ✅ 新功能（批次查询、税务报告等）正常工作
- ✅ 性能指标在可接受范围内
- ✅ 用户能够正常使用新系统