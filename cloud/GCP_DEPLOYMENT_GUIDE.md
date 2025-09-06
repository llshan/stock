# 🚀 GCP 部署指南 - 股票分析系统

将股票分析系统部署到 Google Cloud Platform，实现每小时自动分析并存储结果。

## 📋 部署前准备

### 1. 安装 Google Cloud SDK
```bash
# macOS
brew install --cask google-cloud-sdk

# Linux
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Windows
# 下载并安装: https://cloud.google.com/sdk/docs/install
```

### 2. 初始化 gcloud
```bash
gcloud init
gcloud auth login
gcloud auth application-default login
```

### 3. 创建 GCP 项目 (如果没有)
```bash
# 创建新项目
gcloud projects create YOUR-PROJECT-ID --name="股票分析系统"

# 设置默认项目
gcloud config set project YOUR-PROJECT-ID

# 启用计费 (必需)
# 需要在 GCP Console 中启用: https://console.cloud.google.com/billing
```

## 🚀 快速部署

### 方法一: 使用自动部署脚本 (推荐)
```bash
# 进入 cloud 目录
cd cloud

# 赋予执行权限
chmod +x deploy.sh

# 执行部署 (替换为您的项目ID)
./deploy.sh YOUR-PROJECT-ID
```

### 方法二: 手动部署步骤
```bash
# 1. 设置项目
gcloud config set project YOUR-PROJECT-ID

# 2. 启用必要的 API
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable cloudscheduler.googleapis.com
gcloud services enable storage.googleapis.com

# 3. 创建存储桶
gsutil mb gs://stock-analysis-results-YOUR-PROJECT-ID

# 4. 部署 Cloud Function
gcloud functions deploy stock-analysis-job \
    --source=. \
    --entry-point=stock_analysis_job \
    --runtime=python39 \
    --trigger-http \
    --allow-unauthenticated \
    --memory=1GB \
    --timeout=540s \
    --set-env-vars="GCS_BUCKET_NAME=stock-analysis-results-YOUR-PROJECT-ID,STOCK_SYMBOLS=AAPL,GOOGL,MSFT,AMZN,META,TSLA,NVDA" \
    --region=us-central1

# 5. 创建调度器任务
gcloud scheduler jobs create http stock-analysis-scheduler \
    --schedule="0 */1 * * *" \
    --uri="https://us-central1-YOUR-PROJECT-ID.cloudfunctions.net/stock-analysis-job" \
    --http-method=POST \
    --headers="Content-Type=application/json" \
    --message-body='{}' \
    --time-zone="Asia/Shanghai" \
    --description="每小时执行股票分析任务" \
    --location=us-central1
```

## 📊 系统架构

```
┌─────────────────┐    每小时触发    ┌──────────────────┐
│ Cloud Scheduler │ ───────────────► │ Cloud Function   │
└─────────────────┘                 │ (stock-analysis) │
                                    └──────────────────┘
                                             │
                                             │ 分析结果
                                             ▼
┌─────────────────┐    存储结果      ┌──────────────────┐
│ Cloud Storage   │ ◄───────────────│ 股票分析逻辑      │
│ (JSON 报告)     │                 │ • 技术分析       │
└─────────────────┘                 │ • 财务分析       │
                                    │ • 价格监控       │
                                    └──────────────────┘
```

## 🔧 配置说明

### 环境变量
- `GCS_BUCKET_NAME`: Cloud Storage 存储桶名称
- `STOCK_SYMBOLS`: 监控的股票代码，逗号分隔 (如: `AAPL,GOOGL,MSFT`)

### 调度设置
- **频率**: 每小时执行一次 (`0 */1 * * *`)
- **时区**: 亚洲/上海 (`Asia/Shanghai`)
- **超时**: 9分钟 (540秒)

### 资源配置
- **内存**: 1GB
- **超时**: 9分钟
- **地区**: us-central1

## 📁 输出文件结构

Cloud Storage 存储桶结构:
```
gs://stock-analysis-results-YOUR-PROJECT-ID/
├── results/                          # 历史分析结果
│   ├── stock_analysis_20240315_140000.json
│   ├── stock_analysis_20240315_150000.json
│   └── ...
├── latest/                           # 最新分析结果
│   └── stock_analysis_latest.json    # 总是最新的分析结果
└── alerts/                           # 紧急警告
    ├── urgent_alerts_20240315_140000.json
    └── ...
```

### 结果文件格式
```json
{
  \"timestamp\": \"2024-03-15T14:00:00\",
  \"symbols_analyzed\": [\"AAPL\", \"GOOGL\"],
  \"comprehensive_analysis\": {
    \"AAPL\": {
      \"comprehensive_report\": {
        \"overall_rating\": \"A - 强烈推荐\",
        \"investment_recommendation\": \"买入\",
        \"key_strengths\": [\"技术趋势向好\", \"财务状况优秀\"],
        \"key_concerns\": []
      },
      \"technical_summary\": { ... },
      \"financial_summary\": { ... }
    }
  },
  \"price_drop_monitoring\": { ... },
  \"summary\": {
    \"total_stocks_analyzed\": 10,
    \"successful_analysis\": 9,
    \"high_rated_stocks\": 3,
    \"drop_alerts_1d\": 0,
    \"urgent_drops\": 0
  }
}
```

## 📊 监控和管理

### 使用监控脚本
```bash
# 进入 cloud 目录
cd cloud

# 检查部署状态
./monitor.sh YOUR-PROJECT-ID
```

### 常用管理命令
```bash
# 查看 Function 日志
gcloud functions logs read stock-analysis-job --region=us-central1

# 手动触发分析
gcloud scheduler jobs run stock-analysis-scheduler --location=us-central1

# 暂停自动调度
gcloud scheduler jobs pause stock-analysis-scheduler --location=us-central1

# 恢复自动调度
gcloud scheduler jobs resume stock-analysis-scheduler --location=us-central1

# 下载最新分析结果
gsutil cp gs://stock-analysis-results-YOUR-PROJECT-ID/latest/stock_analysis_latest.json .
```

### Web 控制台链接
- [Cloud Functions](https://console.cloud.google.com/functions/list)
- [Cloud Scheduler](https://console.cloud.google.com/cloudscheduler)
- [Cloud Storage](https://console.cloud.google.com/storage/browser)
- [Cloud Logging](https://console.cloud.google.com/logs/query)

## 🧪 本地测试

在部署前本地测试:
```bash
# 安装依赖 (在项目根目录)
pip install -r requirements.txt

# 进入 cloud 目录进行本地测试
cd cloud
python test_local.py
```

## 💰 成本估算

基于默认配置的预估月成本 (每小时执行):
- Cloud Function: ~$5-10/月 (30天 × 24次/天 × $0.0000004/次)
- Cloud Scheduler: ~$0.10/月 (固定费用)
- Cloud Storage: ~$1-2/月 (假设 1GB 存储)
- **总计**: ~$6-12/月

*实际成本可能因使用量而异*

## 🔐 安全注意事项

1. **权限控制**: Function 具有 Cloud Storage 写入权限
2. **网络访问**: Function 需要访问 Yahoo Finance API
3. **数据保护**: 分析结果存储在 Cloud Storage 中
4. **认证**: 使用 Google Cloud 默认服务账号

## 🛠️ 故障排除

### 常见问题

**Q: Function 部署失败**
```bash
# 检查项目权限和 API 启用状态
gcloud services list --enabled
gcloud projects get-iam-policy YOUR-PROJECT-ID
```

**Q: 调度器无法触发 Function**
```bash
# 检查 Function URL 和调度器配置
gcloud functions describe stock-analysis-job --region=us-central1
gcloud scheduler jobs describe stock-analysis-scheduler --location=us-central1
```

**Q: 数据获取失败**
- 检查网络连接
- Yahoo Finance API 可能有地区限制
- 查看 Function 日志获取详细错误信息

**Q: 存储桶访问错误**
```bash
# 检查存储桶权限
gsutil iam get gs://your-bucket-name
```

### 调试方法
```bash
# 查看详细日志
gcloud functions logs read stock-analysis-job --region=us-central1 --limit=50

# 手动测试 Function
curl -X POST https://YOUR-REGION-YOUR-PROJECT.cloudfunctions.net/stock-analysis-job \
     -H \"Content-Type: application/json\" \
     -d '{}'
```

## 📈 扩展功能

可考虑的功能扩展:
1. **邮件通知**: 集成 SendGrid 或 Gmail API
2. **Slack 通知**: 重要警告推送到 Slack
3. **更多数据源**: 集成更多财经数据 API
4. **机器学习**: 添加股价预测模型
5. **Web 界面**: 创建查看分析结果的网页
6. **移动 App**: 开发移动端应用

## 🆘 支持

如果遇到问题:
1. 查看 [GCP 官方文档](https://cloud.google.com/docs)
2. 检查项目 README.md 文件
3. 查看 Cloud Function 日志
4. 使用 `monitor.sh` 脚本进行诊断