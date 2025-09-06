# 🌥️ GCP 部署文件夹

此目录包含将股票分析系统部署到 Google Cloud Platform 所需的所有文件。

## 📁 文件结构

```
cloud/
├── deploy.sh                    # 🚀 自动部署脚本
├── monitor.sh                   # 📊 系统监控脚本  
├── test_local.py               # 🧪 本地测试脚本
├── cloudbuild.yaml             # ☁️ Cloud Build 配置
├── GCP_DEPLOYMENT_GUIDE.md     # 📖 详细部署指南
└── README.md                   # 📄 本文件
```

## 🚀 快速开始

### 1. 部署系统
```bash
cd cloud
chmod +x deploy.sh
./deploy.sh YOUR-PROJECT-ID
```

### 2. 监控状态
```bash
./monitor.sh YOUR-PROJECT-ID
```

### 3. 本地测试
```bash
python test_local.py
```

## 📖 详细文档

完整的部署指南请参考：[GCP_DEPLOYMENT_GUIDE.md](./GCP_DEPLOYMENT_GUIDE.md)

## 🏗️ 系统架构

```
┌─────────────────┐    每小时触发    ┌──────────────────┐
│ Cloud Scheduler │ ───────────────► │ Cloud Function   │
└─────────────────┘                 │ (stock-analysis) │
                                    └──────────────────┘
                                             │
                                             │ 运行分析
                                             ▼
┌─────────────────┐                 ┌──────────────────┐
│ 源代码文件夹     │                 │ ../main.py       │
│ ../             │ ◄───────────────│ (入口点)         │
│ • stock_analyzer│                 │                  │
│ • financial_*   │                 │ 调用:            │
│ • comprehensive │                 │ • StockAnalyzer  │
│ • price_drop_*  │                 │ • FinancialAnalyzer│
└─────────────────┘                 │ • PriceDropMonitor│
                                    └──────────────────┘
                                             │
                                             │ 保存结果
                                             ▼
                                    ┌──────────────────┐
                                    │ Cloud Storage    │
                                    │ • results/       │
                                    │ • latest/        │
                                    │ • alerts/        │
                                    └──────────────────┘
```

## 🔧 文件说明

### 🚀 deploy.sh
- **功能**: 一键部署整个系统到 GCP
- **包含**: API 启用、存储桶创建、Cloud Function 部署、调度器设置
- **使用**: `./deploy.sh YOUR-PROJECT-ID`

### 📊 monitor.sh  
- **功能**: 监控部署的系统状态
- **显示**: Function 状态、调度器状态、存储使用情况、最近日志
- **使用**: `./monitor.sh YOUR-PROJECT-ID`

### 🧪 test_local.py
- **功能**: 本地测试 Cloud Function 逻辑
- **特点**: 不上传到 GCS，保存到本地文件
- **使用**: `python test_local.py`

### ☁️ cloudbuild.yaml
- **功能**: Google Cloud Build 配置文件
- **用途**: CI/CD 自动部署 (可选)
- **使用**: 与 Cloud Build 触发器配合

## ⚙️ 重要说明

1. **源代码位置**: Cloud Function 的源代码 (`main.py`) 位于父目录 (`../`)
2. **部署源**: 部署脚本使用 `--source=..` 从父目录部署
3. **依赖管理**: `requirements.txt` 位于父目录
4. **本地测试**: 测试脚本会自动添加父目录到 Python 路径

## 💡 使用提示

- 确保在 `cloud/` 目录下运行所有脚本
- 部署前请先阅读 `GCP_DEPLOYMENT_GUIDE.md`
- 部署需要有效的 GCP 项目和启用计费
- 系统将每小时自动分析股票并保存结果