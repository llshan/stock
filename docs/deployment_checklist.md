# 批次级别交易系统部署清单

## 生产环境部署前检查

### 系统要求
- [ ] Python 3.8+ 已安装
- [ ] SQLite 3.24+ 或 PostgreSQL 12+ 已安装
- [ ] 服务器内存 >= 4GB
- [ ] 磁盘空间 >= 50GB（根据数据量调整）
- [ ] 网络连接稳定

### 依赖检查
- [ ] 所有Python包已安装 (`pip install -r requirements.txt`)
- [ ] 环境变量已配置
- [ ] 数据库连接正常
- [ ] 日志目录可写

### 代码部署
- [ ] 代码已从版本控制系统拉取
- [ ] 配置文件已更新为生产环境设置
- [ ] 数据库迁移脚本已执行
- [ ] 静态文件已部署（如有）

## 数据库配置

### 表结构验证
```bash
# 检查所有必需的表是否存在
python -c "
from stock_analysis.data.storage import create_storage
storage = create_storage('sqlite', db_path='database/stock_data.db')
print('Tables exist:', storage.lot_tracking_tables_exist())
storage.close()
"
```

### 索引优化
- [ ] 所有性能优化索引已创建
- [ ] 查询计划已分析和优化
- [ ] 数据库统计信息已更新

### 数据完整性
```bash
# 运行完整性检查
python tools/integrity_check.py --db-path database/stock_data.db
```

## 配置验证

### 交易配置
```python
# config/production.py
TRADING_CONFIG = {
    # 批次追踪设置
    'enable_lot_tracking': True,
    'default_cost_basis_method': 'FIFO',
    'enable_precise_calculations': True,
    
    # 性能设置
    'batch_query_size': 1000,
    'pagination_size': 100,
    'max_calculation_days': 3650,  # 10年
    
    # 精度设置
    'decimal_precision': 4,
    'currency_precision': 2,
    
    # 安全设置
    'enable_external_id_validation': True,
    
    # 日志设置
    'log_level': 'INFO',
    'log_file': '/var/log/stock_trading.log',
    'enable_audit_log': True
}
```

### 数据库连接配置
```python
# database/config.py
DATABASE_CONFIG = {
    'type': 'sqlite',  # 或 'postgresql'
    'path': '/data/stock_data.db',  # SQLite路径
    # PostgreSQL配置（如适用）
    'host': 'localhost',
    'port': 5432,
    'database': 'stock_trading',
    'user': 'stock_user',
    'password': 'secure_password',
    'pool_size': 10,
    'max_connections': 50
}
```

## 性能优化配置

### SQLite优化（如使用SQLite）
```sql
-- 优化SQLite配置
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA cache_size = 10000;
PRAGMA temp_store = memory;
PRAGMA mmap_size = 268435456; -- 256MB
```

### PostgreSQL优化（如使用PostgreSQL）
```sql
-- postgresql.conf 建议设置
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
```

## 监控设置

### 系统监控
- [ ] CPU使用率监控
- [ ] 内存使用率监控
- [ ] 磁盘空间监控
- [ ] 数据库连接数监控

### 应用监控
```python
# monitoring/metrics.py
MONITORING_CONFIG = {
    'enable_metrics': True,
    'metrics_endpoint': '/metrics',
    'alert_thresholds': {
        'transaction_failure_rate': 0.05,  # 5%
        'query_timeout_rate': 0.02,        # 2%
        'data_inconsistency_count': 0,     # 0个
        'average_response_time': 1.0       # 1秒
    }
}
```

### 数据一致性监控
```bash
#!/bin/bash
# scripts/consistency_monitor.sh

# 每小时检查数据一致性
*/60 * * * * /usr/bin/python /app/tools/consistency_check.py --alert-on-failure

# 每日生成健康报告
0 6 * * * /usr/bin/python /app/tools/health_report.py --email admin@company.com
```

## 备份策略

### 数据库备份
```bash
#!/bin/bash
# scripts/backup.sh

BACKUP_DIR="/backup/stock_trading"
DATE=$(date +%Y%m%d_%H%M%S)

# SQLite备份
if [ "$DB_TYPE" = "sqlite" ]; then
    sqlite3 $DB_PATH ".backup $BACKUP_DIR/stock_data_$DATE.db"
fi

# PostgreSQL备份
if [ "$DB_TYPE" = "postgresql" ]; then
    pg_dump -h $DB_HOST -U $DB_USER $DB_NAME > $BACKUP_DIR/stock_data_$DATE.sql
fi

# 保留最近30天的备份
find $BACKUP_DIR -name "stock_data_*.db" -mtime +30 -delete
find $BACKUP_DIR -name "stock_data_*.sql" -mtime +30 -delete
```

### 备份验证
```bash
#!/bin/bash
# scripts/backup_verify.sh

# 验证备份文件完整性
LATEST_BACKUP=$(ls -t /backup/stock_trading/stock_data_*.db | head -1)

if [ -f "$LATEST_BACKUP" ]; then
    # 测试备份文件可读性
    sqlite3 "$LATEST_BACKUP" "SELECT COUNT(*) FROM transactions;" > /dev/null
    if [ $? -eq 0 ]; then
        echo "Backup verification successful: $LATEST_BACKUP"
    else
        echo "Backup verification failed: $LATEST_BACKUP"
        # 发送告警
        echo "Backup verification failed" | mail -s "Backup Alert" admin@company.com
    fi
fi
```

## 安全配置

### 文件权限
```bash
# 设置适当的文件权限
chmod 600 database/stock_data.db
chmod 600 config/production.py
chmod 700 /var/log/stock_trading
chown -R app_user:app_group /app/stock_trading/
```

### 网络安全
- [ ] 防火墙规则已配置
- [ ] SSH密钥认证已启用
- [ ] 不必要的端口已关闭
- [ ] SSL/TLS证书已配置（如有Web界面）

### 应用安全
```python
# security/config.py
SECURITY_CONFIG = {
    'enable_input_validation': True,
    'max_transaction_amount': 1000000,  # $1M
    'rate_limiting': {
        'requests_per_minute': 60,
        'requests_per_hour': 3600
    },
    'audit_logging': {
        'enabled': True,
        'log_all_transactions': True,
        'log_failed_attempts': True
    }
}
```

## 日志配置

### 日志轮转
```bash
# /etc/logrotate.d/stock-trading
/var/log/stock_trading/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    create 0644 app_user app_group
    postrotate
        systemctl reload stock-trading-service
    endscript
}
```

### 日志级别配置
```python
# logging/config.py
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
        },
        'detailed': {
            'format': '[%(asctime)s] %(levelname)s in %(module)s.%(funcName)s:%(lineno)d: %(message)s'
        }
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/stock_trading/app.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'standard'
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/stock_trading/error.log',
            'maxBytes': 10485760,
            'backupCount': 5,
            'formatter': 'detailed'
        }
    },
    'loggers': {
        'stock_analysis': {
            'handlers': ['file', 'error_file'],
            'level': 'INFO',
            'propagate': False
        }
    }
}
```

## 服务配置

### Systemd服务文件
```ini
# /etc/systemd/system/stock-trading.service
[Unit]
Description=Stock Trading Management Service
After=network.target

[Service]
Type=simple
User=app_user
Group=app_group
WorkingDirectory=/app/stock_trading
Environment=PYTHONPATH=/app/stock_trading
ExecStart=/usr/bin/python -m stock_analysis.cli.trading_manager daily
Restart=always
RestartSec=10

# 安全设置
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log/stock_trading /data

[Install]
WantedBy=multi-user.target
```

### Cron任务配置
```bash
# /etc/cron.d/stock-trading
# 每日凌晨2点计算盈亏
0 2 * * * app_user /usr/bin/python /app/stock_trading/stock_analysis/cli/trading_manager.py daily >> /var/log/stock_trading/daily.log 2>&1

# 每周日凌晨3点进行数据一致性检查
0 3 * * 0 app_user /usr/bin/python /app/stock_trading/tools/consistency_check.py >> /var/log/stock_trading/consistency.log 2>&1

# 每月1号凌晨4点进行数据归档
0 4 1 * * app_user /usr/bin/python /app/stock_trading/tools/archive_old_data.py >> /var/log/stock_trading/archive.log 2>&1
```

## 测试验证

### 功能测试
```bash
# 基础功能测试脚本
#!/bin/bash
# tests/deployment_test.sh

echo "开始部署验证测试..."

# 测试数据库连接
echo "测试数据库连接..."
python -c "from stock_analysis.data.storage import create_storage; storage = create_storage('sqlite', db_path='database/stock_data.db'); print('数据库连接正常'); storage.close()"

# 测试基础交易功能
echo "测试买入交易..."
stock-trading buy --symbol TEST -q 10 -p 100 -d 2024-01-01

# 测试批次查询
echo "测试批次查询..."
stock-trading lots

# 测试卖出交易
echo "测试卖出交易..."
stock-trading sell --symbol TEST -q 5 -p 110 -d 2024-01-02

# 测试税务报告
echo "测试税务报告..."
stock-trading tax-report --start-date 2024-01-01 --end-date 2024-12-31

echo "部署验证测试完成！"
```

### 性能测试
```bash
# 性能基准测试
#!/bin/bash
# tests/performance_test.sh

echo "开始性能测试..."

# 批量交易性能测试
python tests/test_trading_performance.py

# 查询性能测试
time stock-trading lots
time stock-trading sales
time stock-trading positions

echo "性能测试完成！"
```

## 部署后验证清单

### 立即验证（部署后1小时内）
- [ ] 所有服务正常启动
- [ ] 数据库连接正常
- [ ] 基础CLI命令可用
- [ ] 日志正常输出
- [ ] 监控指标正常

### 短期验证（部署后24小时内）
- [ ] 定时任务正常执行
- [ ] 数据一致性检查通过
- [ ] 性能指标在预期范围内
- [ ] 备份任务正常执行
- [ ] 告警系统工作正常

### 长期验证（部署后1周内）
- [ ] 用户反馈收集
- [ ] 性能趋势分析
- [ ] 数据增长趋势正常
- [ ] 系统稳定性确认
- [ ] 容量规划验证

## 故障排除

### 常见问题
1. **数据库连接失败**
   ```bash
   # 检查数据库文件权限
   ls -la database/stock_data.db
   # 检查连接配置
   python -c "import sqlite3; sqlite3.connect('database/stock_data.db').execute('SELECT 1')"
   ```

2. **交易记录失败**
   ```bash
   # 检查表结构
   sqlite3 database/stock_data.db ".schema transactions"
   # 检查约束
   sqlite3 database/stock_data.db "PRAGMA foreign_key_check;"
   ```

3. **性能问题**
   ```bash
   # 检查索引使用情况
   sqlite3 database/stock_data.db "EXPLAIN QUERY PLAN SELECT * FROM position_lots WHERE symbol='AAPL';"
   # 更新统计信息
   sqlite3 database/stock_data.db "ANALYZE;"
   ```

### 应急响应
```bash
#!/bin/bash
# scripts/emergency_response.sh

# 停止服务
systemctl stop stock-trading

# 恢复最新备份
LATEST_BACKUP=$(ls -t /backup/stock_trading/stock_data_*.db | head -1)
cp "$LATEST_BACKUP" database/stock_data.db

# 验证备份
python tools/integrity_check.py --db-path database/stock_data.db

# 重启服务
systemctl start stock-trading

# 发送通知
echo "Emergency recovery completed" | mail -s "System Recovery" admin@company.com
```

## 联系信息

**技术支持团队：**
- 邮箱：tech-support@company.com
- 电话：+1-555-TECH (24/7)
- Slack：#stock-trading-support

**运维团队：**
- 邮箱：ops@company.com
- 电话：+1-555-OPS (24/7)
- Slack：#infrastructure

**升级联系人：**
- 技术主管：tech-lead@company.com
- 产品经理：product@company.com
- 项目经理：pm@company.com