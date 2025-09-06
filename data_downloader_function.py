#!/usr/bin/env python3
"""
独立的数据下载 Cloud Function
专门用于下载和存储2020年以来的完整股票数据
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any

from analyzer.data_downloader import StockDataDownloader, create_watchlist

# 尝试导入数据库功能
try:
    from cloud.database_setup import create_database_connection
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False
    logging.warning("数据库功能不可用")

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def data_download_job(request):
    """
    数据下载 Cloud Function 主函数
    专门用于下载和存储历史数据
    
    Args:
        request: HTTP 请求对象
    Returns:
        str: 执行结果消息
    """
    try:
        logger.info("🚀 开始执行股票历史数据下载任务")
        
        # 解析请求参数
        request_json = request.get_json() or {}
        
        # 获取配置
        symbols_env = os.environ.get('STOCK_SYMBOLS', 'AAPL,GOOGL,MSFT,AMZN,META,TSLA,NVDA')
        default_symbols = [s.strip() for s in symbols_env.split(',')]
        
        # 允许通过请求覆盖股票列表
        symbols = request_json.get('symbols', default_symbols)
        start_date = request_json.get('start_date', '2020-01-01')
        
        if isinstance(symbols, str):
            symbols = [s.strip() for s in symbols.split(',')]
        
        logger.info(f"📊 下载股票: {', '.join(symbols)}")
        logger.info(f"📅 开始日期: {start_date}")
        
        # 创建数据下载器
        downloader = StockDataDownloader()
        
        # 创建数据库连接（如果可用）
        database = None
        if DATABASE_AVAILABLE:
            database = create_database_connection()
            if database:
                logger.info("✅ 数据库连接已建立")
        
        if not database:
            logger.warning("⚠️ 数据库不可用，将跳过数据库存储")
        
        # 批量下载数据
        logger.info("🔄 开始批量下载数据...")
        download_results = downloader.batch_download(symbols, start_date=start_date)
        
        # 存储到数据库（如果可用）
        storage_results = {}
        if database:
            logger.info("💾 开始存储数据到数据库...")
            for symbol, data in download_results.items():
                try:
                    if 'error' not in data:
                        database.store_comprehensive_data(symbol, data)
                        storage_results[symbol] = 'stored_successfully'
                        logger.info(f"✅ {symbol} 数据存储成功")
                    else:
                        storage_results[symbol] = f'download_failed: {data["error"]}'
                        logger.warning(f"⚠️ {symbol} 下载失败: {data['error']}")
                except Exception as e:
                    storage_results[symbol] = f'storage_failed: {str(e)}'
                    logger.error(f"❌ {symbol} 存储失败: {str(e)}")
            
            # 关闭数据库连接
            database.close()
            logger.info("📊 数据库连接已关闭")
        
        # 生成执行摘要
        successful_downloads = len([r for r in download_results.values() if 'error' not in r])
        successful_storage = len([r for r in storage_results.values() if r == 'stored_successfully'])
        
        summary = {
            'execution_timestamp': datetime.now().isoformat(),
            'parameters': {
                'symbols': symbols,
                'start_date': start_date,
                'total_symbols': len(symbols)
            },
            'results': {
                'successful_downloads': successful_downloads,
                'failed_downloads': len(symbols) - successful_downloads,
                'successful_storage': successful_storage,
                'database_available': database is not None
            },
            'details': {
                'download_results': {
                    symbol: 'success' if 'error' not in data else data['error']
                    for symbol, data in download_results.items()
                },
                'storage_results': storage_results
            }
        }
        
        logger.info(f"✅ 数据下载任务完成")
        logger.info(f"📊 下载成功: {successful_downloads}/{len(symbols)}")
        if database:
            logger.info(f"💾 存储成功: {successful_storage}/{len(symbols)}")
        
        return json.dumps({
            'status': 'success',
            'message': f'下载了 {successful_downloads}/{len(symbols)} 个股票的数据',
            'summary': summary
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        error_msg = f"❌ 数据下载任务执行失败: {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            'status': 'error',
            'message': error_msg,
            'timestamp': datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)

# 本地测试入口点
if __name__ == "__main__":
    print("🧪 本地测试数据下载功能")
    
    # 模拟请求对象
    class MockRequest:
        def get_json(self):
            return {
                'symbols': ['AAPL', 'GOOGL'],
                'start_date': '2020-01-01'
            }
    
    # 设置环境变量
    os.environ.setdefault('STOCK_SYMBOLS', 'AAPL,GOOGL')
    
    # 执行测试
    mock_request = MockRequest()
    result = data_download_job(mock_request)
    print("📊 测试结果:")
    print(result)