#!/usr/bin/env python3
"""
GCP Cloud Function 入口点
用于定期执行股票分析并将结果存储到 Cloud Storage
"""

import os
import json
import logging
from logging_utils import setup_logging
from datetime import datetime
from typing import Dict, Any
from google.cloud import storage
from analyzer.comprehensive_analyzer import ComprehensiveStockAnalyzer
from analyzer.app.runner import run_analysis_for_symbols, build_operators
from data_service.downloaders.yfinance import YFinanceDataDownloader

# 尝试导入数据库功能
try:
    from cloud.database_setup import create_database_connection
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False
    logger.warning("数据库功能不可用，将只使用Cloud Storage存储")

# 配置日志（统一入口）
setup_logging()
logger = logging.getLogger(__name__)

def stock_analysis_job(request=None):
    """
    Cloud Function 主函数
    Args:
        request: HTTP 请求对象 (由 Cloud Scheduler 触发时可能为空)
    Returns:
        str: 执行结果消息
    """
    try:
        logger.info("🚀 开始执行定时股票分析任务")
        
        # 从环境变量获取配置
        bucket_name = os.environ.get('GCS_BUCKET_NAME', 'stock-analysis-results')
        symbols_env = os.environ.get('STOCK_SYMBOLS', 'AAPL,GOOGL,MSFT,AMZN,META,TSLA,NVDA')
        symbols = [s.strip() for s in symbols_env.split(',')]
        
        logger.info(f"📊 分析股票: {', '.join(symbols)}")
        
        # 检查是否需要完整数据下载
        download_full_data = os.environ.get('DOWNLOAD_FULL_DATA', 'false').lower() == 'true'
        
        if download_full_data:
            # 执行完整数据下载和存储
            full_data_results = run_full_data_download(symbols)
        else:
            full_data_results = {'skipped': True, 'reason': 'DOWNLOAD_FULL_DATA not enabled'}
        
        # 执行综合分析
        comprehensive_results = run_comprehensive_analysis(symbols)
        
        # 执行价格下跌监控
        drop_monitor_results = run_price_drop_monitoring(symbols)
        
        # 合并结果
        combined_results = {
            'timestamp': datetime.now().isoformat(),
            'symbols_analyzed': symbols,
            'full_data_download': full_data_results,
            'comprehensive_analysis': comprehensive_results,
            'price_drop_monitoring': drop_monitor_results,
            'summary': generate_summary(comprehensive_results, drop_monitor_results)
        }
        
        # 上传结果到 Cloud Storage
        upload_results_to_gcs(combined_results, bucket_name)
        
        logger.info("✅ 股票分析任务完成")
        return json.dumps({
            'status': 'success',
            'message': f'分析了 {len(symbols)} 只股票',
            'timestamp': combined_results['timestamp']
        })
        
    except Exception as e:
        error_msg = f"❌ 分析任务执行失败: {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            'status': 'error',
            'message': error_msg,
            'timestamp': datetime.now().isoformat()
        })

def run_comprehensive_analysis(symbols: list) -> Dict[str, Any]:
    """执行综合分析"""
    try:
        logger.info("📈 开始综合分析...")
        results = run_analysis_for_symbols(symbols, db_path=os.environ.get('DB_PATH', 'stock_data.db'))
        processed_results = {}
        for symbol, data in results.items():
            ops = data.get('operators', {})
            processed_results[symbol] = {
                'operators': ops,
                'summary': data.get('summary', {})
            }
        logger.info("✅ 综合分析完成")
        return processed_results
        
    except Exception as e:
        logger.error(f"❌ 综合分析失败: {str(e)}")
        return {'error': str(e)}

def run_price_drop_monitoring(symbols: list) -> Dict[str, Any]:
    """执行价格下跌监控"""
    try:
        logger.info("⚠️ 开始价格下跌监控...")
        # 1天与7天分别运行
        res_1d = run_analysis_for_symbols(symbols, db_path=os.environ.get('DB_PATH', 'stock_data.db'), enabled_operators=['drop_alert'])
        res_7d = run_analysis_for_symbols(symbols, db_path=os.environ.get('DB_PATH', 'stock_data.db'), enabled_operators=['drop_alert_7d'])
        alerts_1d = []
        alerts_7d = []
        for sym, data in res_1d.items():
            da = data.get('operators', {}).get('drop_alert', {})
            if da and not da.get('error') and da.get('is_alert'):
                alerts_1d.append({'symbol': sym, **da})
        for sym, data in res_7d.items():
            da7 = data.get('operators', {}).get('drop_alert_7d', {})
            if da7 and not da7.get('error') and da7.get('is_alert'):
                alerts_7d.append({'symbol': sym, **da7})
        combined = {
            '1_day_monitoring': {'alerts': alerts_1d},
            '7_day_monitoring': {'alerts': alerts_7d},
            'urgent_alerts': [a for a in alerts_1d if abs(a.get('percent_change', 0)) >= 20]
        }
        logger.info("✅ 价格下跌监控完成")
        return combined
        
    except Exception as e:
        logger.error(f"❌ 价格下跌监控失败: {str(e)}")
        return {'error': str(e)}

def run_full_data_download(symbols: list) -> Dict[str, Any]:
    """执行完整股票数据下载和存储"""
    try:
        logger.info("💾 开始完整数据下载和存储...")
        
        # 创建数据下载器
        downloader = YFinanceDataDownloader()
        
        # 创建数据库连接（如果可用）
        database = None
        if DATABASE_AVAILABLE:
            database = create_database_connection()
            if database:
                logger.info("✅ 数据库连接已建立")
        
        if not database:
            logger.warning("⚠️ 数据库不可用，跳过数据库存储")
        
        # 批量下载数据
        results = downloader.batch_download(symbols, start_date="2020-01-01")
        
        # 存储到数据库（如果可用）
        storage_results = {}
        if database:
            for symbol, data in results.items():
                try:
                    if 'error' not in data:
                        database.store_comprehensive_data(symbol, data)
                        storage_results[symbol] = 'stored_successfully'
                    else:
                        storage_results[symbol] = f'download_failed: {data["error"]}'
                except Exception as e:
                    storage_results[symbol] = f'storage_failed: {str(e)}'
                    logger.error(f"存储 {symbol} 数据失败: {str(e)}")
        
        # 关闭数据库连接
        if database:
            database.close()
        
        # 生成摘要
        successful_downloads = len([r for r in results.values() if 'error' not in r])
        successful_storage = len([r for r in storage_results.values() if r == 'stored_successfully'])
        
        summary = {
            'total_symbols': len(symbols),
            'successful_downloads': successful_downloads,
            'failed_downloads': len(symbols) - successful_downloads,
            'successful_storage': successful_storage,
            'database_available': database is not None,
            'download_results': results,
            'storage_results': storage_results
        }
        
        logger.info(f"✅ 完整数据下载完成: {successful_downloads}/{len(symbols)} 成功")
        if database:
            logger.info(f"✅ 数据库存储完成: {successful_storage}/{len(symbols)} 成功")
        
        return summary
        
    except Exception as e:
        logger.error(f"❌ 完整数据下载失败: {str(e)}")
        return {'error': str(e)}

def extract_technical_summary(operators: Dict) -> Dict:
    """从 operators 结果提取技术摘要"""
    rsi = operators.get('rsi', {})
    return {
        'trend': 'N/A',
        'rsi': rsi.get('rsi', 0),
        'rsi_signal': rsi.get('signal', 'N/A'),
    }

def extract_financial_summary(operators: Dict) -> Dict:
    """从 operators 结果提取财务摘要"""
    ratios = operators.get('fin_ratios', {})
    health = operators.get('fin_health', {})
    return {
        'net_profit_margin': ratios.get('net_profit_margin', 0),
        'roe': ratios.get('roe', 0),
        'pe_ratio': ratios.get('pe_ratio', 0),
        'debt_ratio': ratios.get('debt_ratio', 0),
        'health_grade': health.get('grade', 'N/A'),
        'health_score': health.get('health_score', 0)
    }

def generate_summary(comprehensive_results: Dict, drop_monitor_results: Dict) -> Dict:
    """生成分析摘要"""
    summary = {
        'total_stocks_analyzed': 0,
        'successful_analysis': 0,
        'failed_analysis': 0,
        'high_rated_stocks': [],  # A级或B级
        'drop_alerts_1d': 0,
        'drop_alerts_7d': 0,
        'urgent_drops': 0
    }
    
    # 统计综合分析结果
    if 'error' not in comprehensive_results:
        summary['total_stocks_analyzed'] = len(comprehensive_results)
        for symbol, data in comprehensive_results.items():
            if 'error' in data:
                summary['failed_analysis'] += 1
            else:
                summary['successful_analysis'] += 1
                # 根据健康评分判断高评级
                ops = data.get('operators', {})
                fin = extract_financial_summary(ops)
                if fin.get('health_grade', '').startswith(('A','B')):
                    summary['high_rated_stocks'].append({
                        'symbol': symbol,
                        'rating': fin.get('health_grade'),
                        'recommendation': ''
                    })
    
    # 统计价格下跌警告
    if 'error' not in drop_monitor_results:
        summary['drop_alerts_1d'] = len(drop_monitor_results.get('1_day_monitoring', {}).get('alerts', []))
        summary['drop_alerts_7d'] = len(drop_monitor_results.get('7_day_monitoring', {}).get('alerts', []))
        summary['urgent_drops'] = len(drop_monitor_results.get('urgent_alerts', []))
    
    return summary

def upload_results_to_gcs(results: Dict, bucket_name: str):
    """上传结果到 Google Cloud Storage"""
    try:
        # 初始化 Storage 客户端
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        
        # 创建文件名（按日期时间）
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"stock_analysis_{timestamp}.json"
        
        # 上传主结果文件
        blob = bucket.blob(f"results/{filename}")
        blob.upload_from_string(
            json.dumps(results, ensure_ascii=False, indent=2),
            content_type='application/json'
        )
        
        # 上传最新结果（覆盖）
        latest_blob = bucket.blob("latest/stock_analysis_latest.json")
        latest_blob.upload_from_string(
            json.dumps(results, ensure_ascii=False, indent=2),
            content_type='application/json'
        )
        
        logger.info(f"📤 结果已上传到 GCS: gs://{bucket_name}/{filename}")
        
        # 如果有紧急警告，创建单独的警告文件
        urgent_alerts = results.get('price_drop_monitoring', {}).get('urgent_alerts', [])
        if urgent_alerts:
            alert_filename = f"alerts/urgent_alerts_{timestamp}.json"
            alert_blob = bucket.blob(alert_filename)
            alert_blob.upload_from_string(
                json.dumps({
                    'timestamp': results['timestamp'],
                    'urgent_alerts': urgent_alerts
                }, ensure_ascii=False, indent=2),
                content_type='application/json'
            )
            logger.info(f"🚨 紧急警告已上传: gs://{bucket_name}/{alert_filename}")
        
    except Exception as e:
        logger.error(f"❌ 上传到 GCS 失败: {str(e)}")
        raise

# 本地测试入口点
if __name__ == "__main__":
    logger.info("🧪 本地测试模式")
    os.environ.setdefault('GCS_BUCKET_NAME', 'test-stock-analysis')
    os.environ.setdefault('STOCK_SYMBOLS', 'AAPL,GOOGL,MSFT')
    
    result = stock_analysis_job()
    logger.info("📊 测试结果:")
    logger.info(result)
