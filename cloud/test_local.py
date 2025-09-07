#!/usr/bin/env python3
"""
本地测试脚本
测试 Cloud Function 的逻辑，但不上传到 GCS
"""

import os
import json
import sys
import logging
from logging_utils import setup_logging
from datetime import datetime

# 设置环境变量进行本地测试
os.environ['GCS_BUCKET_NAME'] = 'test-bucket'
os.environ['STOCK_SYMBOLS'] = 'AAPL,GOOGL'

def mock_upload_results_to_gcs(results, bucket_name):
    """模拟上传到 GCS，实际保存到本地"""
    logging.getLogger(__name__).info(f"📤 模拟上传到 GCS 存储桶: {bucket_name}")
    
    # 保存到本地文件
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"test_results_{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    logging.getLogger(__name__).info(f"📄 结果已保存到本地文件: {filename}")
    
    # 显示摘要
    summary = results.get('summary', {})
    logger = logging.getLogger(__name__)
    logger.info("📊 分析摘要:")
    logger.info(f"  • 总股票数: {summary.get('total_stocks_analyzed', 0)}")
    logger.info(f"  • 成功分析: {summary.get('successful_analysis', 0)}")
    logger.info(f"  • 失败分析: {summary.get('failed_analysis', 0)}")
    logger.info(f"  • 高评级股票: {len(summary.get('high_rated_stocks', []))}")
    logger.info(f"  • 1天下跌警告: {summary.get('drop_alerts_1d', 0)}")
    logger.info(f"  • 7天下跌警告: {summary.get('drop_alerts_7d', 0)}")
    logger.info(f"  • 紧急下跌: {summary.get('urgent_drops', 0)}")

def main():
    setup_logging()
    logging.getLogger(__name__).info("🧪 本地测试 Cloud Function 逻辑")
    logging.getLogger(__name__).info("================================")
    
    try:
        # 添加父目录到 Python 路径
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        
        # 动态导入 main.py 中的函数，但替换 GCS 上传函数
        import main
        
        # 临时替换上传函数
        original_upload = main.upload_results_to_gcs
        main.upload_results_to_gcs = mock_upload_results_to_gcs
        
        # 执行分析任务
        result = main.stock_analysis_job()
        
        # 恢复原始函数
        main.upload_results_to_gcs = original_upload
        
        logging.getLogger(__name__).info("✅ 测试完成")
        logging.getLogger(__name__).info(f"📊 执行结果: {result}")
        
    except ImportError as e:
        logging.getLogger(__name__).error(f"❌ 导入错误: {e}")
        logging.getLogger(__name__).error("请确保 main.py 文件存在且可以正常导入")
        sys.exit(1)
    except Exception as e:
        logging.getLogger(__name__).error(f"❌ 测试失败: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
