#!/bin/bash

# GCP 股票分析系统部署脚本
# 使用方法: ./deploy.sh [PROJECT_ID]

set -e  # 遇到错误时退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 配置变量
PROJECT_ID=${1:-"your-project-id"}
REGION="us-central1"
FUNCTION_NAME="stock-analysis-job"
BUCKET_NAME="stock-analysis-results-${PROJECT_ID}"
SCHEDULER_JOB="stock-analysis-scheduler"
STOCK_SYMBOLS="AAPL,GOOGL,MSFT,AMZN,META,TSLA,NVDA,NFLX,UBER,BABA,JD,BIDU"

# 数据库配置
DB_INSTANCE_NAME="stock-analysis-db"
DB_NAME="stockdb"
DB_USER="stockuser"
DB_PASSWORD=${DB_PASSWORD:-$(openssl rand -base64 24)}

echo -e "${BLUE}🚀 开始部署股票分析系统到 GCP${NC}"
echo -e "${BLUE}项目ID: ${PROJECT_ID}${NC}"
echo -e "${BLUE}区域: ${REGION}${NC}"
echo "=================================================="

# 检查 gcloud 是否已安装
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ 错误: gcloud CLI 未安装${NC}"
    echo "请安装 Google Cloud SDK: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# 设置项目
echo -e "${YELLOW}📋 设置 GCP 项目...${NC}"
gcloud config set project $PROJECT_ID

# 启用必要的 API
echo -e "${YELLOW}🔧 启用必要的 GCP API...${NC}"
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable cloudscheduler.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable sqladmin.googleapis.com

# 创建 Cloud Storage 存储桶
echo -e "${YELLOW}📦 创建 Cloud Storage 存储桶...${NC}"
if ! gsutil ls gs://$BUCKET_NAME &> /dev/null; then
    gsutil mb gs://$BUCKET_NAME
    echo -e "${GREEN}✅ 存储桶创建成功: gs://$BUCKET_NAME${NC}"
else
    echo -e "${YELLOW}⚠️ 存储桶已存在: gs://$BUCKET_NAME${NC}"
fi

# 创建存储桶目录结构
echo -e "${YELLOW}📁 设置存储桶目录结构...${NC}"
echo '{}' | gsutil cp - gs://$BUCKET_NAME/results/.gitkeep
echo '{}' | gsutil cp - gs://$BUCKET_NAME/latest/.gitkeep
echo '{}' | gsutil cp - gs://$BUCKET_NAME/alerts/.gitkeep

# 创建 Cloud SQL 数据库
echo -e "${YELLOW}🗄️ 创建 Cloud SQL 数据库...${NC}"
if ! gcloud sql instances describe $DB_INSTANCE_NAME &> /dev/null; then
    echo -e "${YELLOW}   创建 PostgreSQL 实例...${NC}"
    gcloud sql instances create $DB_INSTANCE_NAME \
        --database-version=POSTGRES_14 \
        --tier=db-f1-micro \
        --region=$REGION \
        --storage-type=SSD \
        --storage-size=10GB \
        --backup \
        --maintenance-window-day=SUN \
        --maintenance-window-hour=02
    
    echo -e "${YELLOW}   创建数据库...${NC}"
    gcloud sql databases create $DB_NAME --instance=$DB_INSTANCE_NAME
    
    echo -e "${YELLOW}   创建数据库用户...${NC}"
    gcloud sql users create $DB_USER \
        --instance=$DB_INSTANCE_NAME \
        --password=$DB_PASSWORD
    
    echo -e "${GREEN}✅ Cloud SQL 实例创建成功${NC}"
    echo -e "${GREEN}📋 数据库密码: $DB_PASSWORD${NC}"
    echo -e "${YELLOW}⚠️ 请妥善保存数据库密码${NC}"
else
    echo -e "${YELLOW}⚠️ Cloud SQL 实例已存在: $DB_INSTANCE_NAME${NC}"
fi

# 部署 Cloud Function
echo -e "${YELLOW}☁️ 部署 Cloud Function...${NC}"
echo -e "${YELLOW}📂 从上级目录部署源码...${NC}"
gcloud functions deploy $FUNCTION_NAME \
    --source=.. \
    --entry-point=stock_analysis_job \
    --runtime=python39 \
    --trigger-http \
    --allow-unauthenticated \
    --memory=1GB \
    --timeout=540s \
    --set-env-vars="GCS_BUCKET_NAME=$BUCKET_NAME,STOCK_SYMBOLS=$STOCK_SYMBOLS,GCP_PROJECT_ID=$PROJECT_ID,CLOUD_SQL_REGION=$REGION,CLOUD_SQL_INSTANCE=$DB_INSTANCE_NAME,CLOUD_SQL_DATABASE=$DB_NAME,CLOUD_SQL_USERNAME=$DB_USER,CLOUD_SQL_PASSWORD=$DB_PASSWORD,DOWNLOAD_FULL_DATA=false" \
    --region=$REGION

# 获取 Cloud Function URL
FUNCTION_URL=$(gcloud functions describe $FUNCTION_NAME --region=$REGION --format="value(httpsTrigger.url)")
echo -e "${GREEN}✅ Cloud Function 部署成功${NC}"
echo -e "${GREEN}📎 Function URL: $FUNCTION_URL${NC}"

# 删除现有的调度器任务（如果存在）
echo -e "${YELLOW}🗑️ 检查并删除现有调度器任务...${NC}"
if gcloud scheduler jobs describe $SCHEDULER_JOB --location=$REGION &> /dev/null; then
    gcloud scheduler jobs delete $SCHEDULER_JOB --location=$REGION --quiet
    echo -e "${GREEN}✅ 现有调度器任务已删除${NC}"
fi

# 创建 Cloud Scheduler 任务
echo -e "${YELLOW}⏰ 创建 Cloud Scheduler 任务...${NC}"
gcloud scheduler jobs create http $SCHEDULER_JOB \
    --schedule="0 */1 * * *" \
    --uri="$FUNCTION_URL" \
    --http-method=POST \
    --headers="Content-Type=application/json" \
    --message-body='{}' \
    --time-zone="Asia/Shanghai" \
    --description="每小时执行股票分析任务" \
    --location=$REGION

echo -e "${GREEN}✅ Cloud Scheduler 任务创建成功${NC}"

# 手动触发一次测试
echo -e "${YELLOW}🧪 执行首次测试运行...${NC}"
gcloud scheduler jobs run $SCHEDULER_JOB --location=$REGION

echo ""
echo "=================================================="
echo -e "${GREEN}🎉 部署完成！${NC}"
echo ""
echo -e "${BLUE}📊 部署信息:${NC}"
echo -e "  项目ID: ${PROJECT_ID}"
echo -e "  区域: ${REGION}"
echo -e "  Function名称: ${FUNCTION_NAME}"
echo -e "  存储桶: gs://${BUCKET_NAME}"
echo -e "  调度器: ${SCHEDULER_JOB} (每小时执行)"
echo -e "  监控股票: ${STOCK_SYMBOLS}"
echo ""
echo -e "${BLUE}🔗 有用的链接:${NC}"
echo -e "  Cloud Functions: https://console.cloud.google.com/functions/list?project=${PROJECT_ID}"
echo -e "  Cloud Scheduler: https://console.cloud.google.com/cloudscheduler?project=${PROJECT_ID}"
echo -e "  Cloud Storage: https://console.cloud.google.com/storage/browser/${BUCKET_NAME}?project=${PROJECT_ID}"
echo -e "  Logs: https://console.cloud.google.com/logs/query?project=${PROJECT_ID}"
echo ""
echo -e "${BLUE}📋 管理命令:${NC}"
echo -e "  查看日志: gcloud functions logs read ${FUNCTION_NAME} --region=${REGION}"
echo -e "  手动触发: gcloud scheduler jobs run ${SCHEDULER_JOB} --location=${REGION}"
echo -e "  暂停调度: gcloud scheduler jobs pause ${SCHEDULER_JOB} --location=${REGION}"
echo -e "  恢复调度: gcloud scheduler jobs resume ${SCHEDULER_JOB} --location=${REGION}"
echo ""
echo -e "${GREEN}✅ 系统将每小时自动分析股票并将结果保存到 Cloud Storage${NC}"