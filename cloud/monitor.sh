#!/bin/bash

# GCP 股票分析系统监控脚本
# 使用方法: ./monitor.sh [PROJECT_ID]

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 配置变量
PROJECT_ID=${1:-"your-project-id"}
REGION="us-central1"
FUNCTION_NAME="stock-analysis-job"
BUCKET_NAME="stock-analysis-results-${PROJECT_ID}"
SCHEDULER_JOB="stock-analysis-scheduler"

echo -e "${BLUE}📊 股票分析系统监控面板${NC}"
echo -e "${BLUE}项目ID: ${PROJECT_ID}${NC}"
echo "=================================================="

# 设置项目
gcloud config set project $PROJECT_ID --quiet

echo -e "${YELLOW}☁️ Cloud Function 状态:${NC}"
if gcloud functions describe $FUNCTION_NAME --region=$REGION --quiet &> /dev/null; then
    echo -e "${GREEN}✅ Function 运行中: $FUNCTION_NAME${NC}"
    
    # 获取 Function URL
    FUNCTION_URL=$(gcloud functions describe $FUNCTION_NAME --region=$REGION --format="value(httpsTrigger.url)" 2>/dev/null)
    echo -e "   📎 URL: $FUNCTION_URL"
    
    # 获取最后部署时间
    LAST_UPDATE=$(gcloud functions describe $FUNCTION_NAME --region=$REGION --format="value(updateTime)" 2>/dev/null)
    echo -e "   🕐 最后更新: $LAST_UPDATE"
else
    echo -e "${RED}❌ Function 不存在或未部署${NC}"
fi

echo ""
echo -e "${YELLOW}⏰ Cloud Scheduler 状态:${NC}"
if gcloud scheduler jobs describe $SCHEDULER_JOB --location=$REGION --quiet &> /dev/null; then
    SCHEDULER_STATE=$(gcloud scheduler jobs describe $SCHEDULER_JOB --location=$REGION --format="value(state)" 2>/dev/null)
    if [ "$SCHEDULER_STATE" = "ENABLED" ]; then
        echo -e "${GREEN}✅ 调度器运行中: $SCHEDULER_JOB${NC}"
    else
        echo -e "${YELLOW}⚠️ 调度器状态: $SCHEDULER_STATE${NC}"
    fi
    
    # 获取下次执行时间
    NEXT_RUN=$(gcloud scheduler jobs describe $SCHEDULER_JOB --location=$REGION --format="value(scheduleTime)" 2>/dev/null)
    if [ -n "$NEXT_RUN" ]; then
        echo -e "   ⏭️ 下次执行: $NEXT_RUN"
    fi
    
    # 获取最后执行状态
    LAST_ATTEMPT=$(gcloud scheduler jobs describe $SCHEDULER_JOB --location=$REGION --format="value(lastAttemptTime)" 2>/dev/null)
    if [ -n "$LAST_ATTEMPT" ]; then
        echo -e "   🕒 最后执行: $LAST_ATTEMPT"
    fi
else
    echo -e "${RED}❌ 调度器任务不存在${NC}"
fi

echo ""
echo -e "${YELLOW}📦 Cloud Storage 状态:${NC}"
if gsutil ls gs://$BUCKET_NAME &> /dev/null; then
    echo -e "${GREEN}✅ 存储桶存在: gs://$BUCKET_NAME${NC}"
    
    # 检查最新结果文件
    if gsutil ls gs://$BUCKET_NAME/latest/stock_analysis_latest.json &> /dev/null; then
        LATEST_FILE_TIME=$(gsutil stat gs://$BUCKET_NAME/latest/stock_analysis_latest.json | grep "Time created" | cut -d: -f2- | xargs)
        echo -e "   📄 最新分析: $LATEST_FILE_TIME"
    else
        echo -e "${YELLOW}   ⚠️ 暂无分析结果文件${NC}"
    fi
    
    # 统计历史文件数量
    RESULT_COUNT=$(gsutil ls gs://$BUCKET_NAME/results/*.json 2>/dev/null | wc -l | xargs)
    echo -e "   📊 历史分析文件: $RESULT_COUNT 个"
    
    # 检查警告文件
    ALERT_COUNT=$(gsutil ls gs://$BUCKET_NAME/alerts/*.json 2>/dev/null | wc -l | xargs)
    if [ "$ALERT_COUNT" -gt 0 ]; then
        echo -e "   🚨 警告文件: $ALERT_COUNT 个"
    fi
else
    echo -e "${RED}❌ 存储桶不存在${NC}"
fi

echo ""
echo -e "${YELLOW}📋 最近的执行日志:${NC}"
echo "----------------------------------------"
gcloud functions logs read $FUNCTION_NAME --region=$REGION --limit=10 --format="table(timestamp,severity,textPayload)" 2>/dev/null || echo -e "${RED}无法获取日志${NC}"

echo ""
echo -e "${BLUE}🔧 管理命令:${NC}"
echo "  查看详细日志: gcloud functions logs read $FUNCTION_NAME --region=$REGION"
echo "  手动触发分析: gcloud scheduler jobs run $SCHEDULER_JOB --location=$REGION"
echo "  暂停调度器: gcloud scheduler jobs pause $SCHEDULER_JOB --location=$REGION"
echo "  恢复调度器: gcloud scheduler jobs resume $SCHEDULER_JOB --location=$REGION"
echo "  下载最新结果: gsutil cp gs://$BUCKET_NAME/latest/stock_analysis_latest.json ."
echo ""

# 检查是否有紧急警告
if gsutil ls gs://$BUCKET_NAME/alerts/ &> /dev/null; then
    RECENT_ALERTS=$(gsutil ls -l gs://$BUCKET_NAME/alerts/*.json 2>/dev/null | tail -5 | wc -l | xargs)
    if [ "$RECENT_ALERTS" -gt 0 ]; then
        echo -e "${RED}🚨 检测到 $RECENT_ALERTS 个最近的紧急警告文件${NC}"
        echo "  查看警告: gsutil ls gs://$BUCKET_NAME/alerts/"
        echo ""
    fi
fi

echo -e "${GREEN}✅ 监控检查完成${NC}"