#!/usr/bin/env python3
"""
股票数据管理器
整合数据下载和数据库存储功能
"""

import os
import sys
import argparse
import logging
from datetime import datetime
from typing import List, Dict

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from analyzer.data_downloader import StockDataDownloader, create_watchlist
from analyzer.database import StockDatabase

class StockDataManager:
    def __init__(self, db_path: str = "stock_data.db"):
        """初始化股票数据管理器"""
        self.downloader = StockDataDownloader()
        self.database = StockDatabase(db_path)
        self.logger = logging.getLogger(__name__)
    
    def download_and_store_stock(self, symbol: str, start_date: str = None) -> bool:
        """下载并存储单个股票的数据"""
        try:
            self.logger.info(f"🚀 处理股票: {symbol}")
            
            # 下载综合数据
            data = self.downloader.download_comprehensive_data(symbol, start_date)
            
            # 检查下载是否成功
            if 'error' in data:
                self.logger.error(f"❌ {symbol} 下载失败: {data['error']}")
                return False
            
            # 存储到数据库
            self.database.store_comprehensive_data(symbol, data)
            self.logger.info(f"✅ {symbol} 数据处理完成")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 处理 {symbol} 时出错: {str(e)}")
            return False
    
    def batch_download_and_store(self, symbols: List[str], start_date: str = None) -> Dict:
        """批量下载并存储股票数据"""
        results = {
            'total': len(symbols),
            'successful': 0,
            'failed': 0,
            'details': {}
        }
        
        self.logger.info(f"🎯 开始批量处理 {len(symbols)} 个股票")
        print(f"\n📊 批量下载并存储股票数据")
        print(f"📅 数据时间范围: {start_date or '2020-01-01'} 至今")
        print(f"📈 股票数量: {len(symbols)}")
        print("=" * 60)
        
        for i, symbol in enumerate(symbols):
            print(f"\n[{i+1}/{len(symbols)}] 处理 {symbol}...")
            
            success = self.download_and_store_stock(symbol, start_date)
            
            if success:
                results['successful'] += 1
                results['details'][symbol] = 'success'
                print(f"✅ {symbol} 完成")
            else:
                results['failed'] += 1 
                results['details'][symbol] = 'failed'
                print(f"❌ {symbol} 失败")
        
        # 显示最终结果
        print("\n" + "=" * 60)
        print("📊 批量处理结果:")
        print(f"✅ 成功: {results['successful']}")
        print(f"❌ 失败: {results['failed']}")
        print(f"📊 成功率: {results['successful']/results['total']*100:.1f}%")
        
        return results
    
    def update_stock_data(self, symbol: str) -> bool:
        """更新单个股票的数据"""
        self.logger.info(f"🔄 更新 {symbol} 的数据...")
        
        # 重新下载并存储数据
        return self.download_and_store_stock(symbol)
    
    def generate_data_report(self) -> Dict:
        """生成数据质量报告"""
        try:
            self.logger.info("📊 生成数据质量报告...")
            
            # 获取数据质量报告
            quality_df = self.database.get_data_quality_report()
            download_df = self.database.get_download_summary()
            
            report = {
                'generation_time': datetime.now().isoformat(),
                'total_stocks': len(quality_df),
                'quality_distribution': {},
                'data_completeness_stats': {},
                'recent_downloads': len(download_df)
            }
            
            if not quality_df.empty:
                # 质量等级分布
                grade_counts = quality_df['quality_grade'].value_counts()
                report['quality_distribution'] = grade_counts.to_dict()
                
                # 数据完整性统计
                completeness = quality_df['data_completeness']
                report['data_completeness_stats'] = {
                    'average': float(completeness.mean()),
                    'median': float(completeness.median()),
                    'min': float(completeness.min()),
                    'max': float(completeness.max())
                }
                
                # 可用性统计
                report['availability_stats'] = {
                    'stock_data_available': int(quality_df['stock_data_available'].sum()),
                    'financial_data_available': int(quality_df['financial_data_available'].sum())
                }
            
            return report
            
        except Exception as e:
            self.logger.error(f"生成报告失败: {str(e)}")
            return {'error': str(e)}
    
    def print_data_report(self):
        """打印数据质量报告"""
        report = self.generate_data_report()
        
        if 'error' in report:
            print(f"❌ 报告生成失败: {report['error']}")
            return
        
        print("\n" + "=" * 60)
        print("📊 股票数据质量报告")
        print("=" * 60)
        print(f"📅 报告生成时间: {report['generation_time']}")
        print(f"📈 总股票数量: {report['total_stocks']}")
        print(f"📝 最近下载记录: {report['recent_downloads']}")
        
        if 'quality_distribution' in report and report['quality_distribution']:
            print("\n🎯 数据质量等级分布:")
            for grade, count in report['quality_distribution'].items():
                print(f"   {grade}: {count} 个股票")
        
        if 'data_completeness_stats' in report:
            stats = report['data_completeness_stats']
            print(f"\n📊 数据完整性统计:")
            print(f"   平均完整性: {stats.get('average', 0)*100:.1f}%")
            print(f"   中位数完整性: {stats.get('median', 0)*100:.1f}%")
            print(f"   最低完整性: {stats.get('min', 0)*100:.1f}%")
            print(f"   最高完整性: {stats.get('max', 0)*100:.1f}%")
        
        if 'availability_stats' in report:
            avail = report['availability_stats']
            print(f"\n🔍 数据可用性:")
            print(f"   股票价格数据: {avail.get('stock_data_available', 0)} 个股票")
            print(f"   财务报表数据: {avail.get('financial_data_available', 0)} 个股票")
    
    def backup_database(self, backup_path: str):
        """备份数据库"""
        self.database.backup_database(backup_path)
        print(f"✅ 数据库已备份到: {backup_path}")
    
    def close(self):
        """关闭数据库连接"""
        self.database.close()

def main():
    """命令行主函数"""
    parser = argparse.ArgumentParser(description='股票数据管理器')
    parser.add_argument('--action', '-a', choices=['download', 'update', 'report', 'backup'], 
                       default='download', help='执行的操作')
    parser.add_argument('--symbols', '-s', nargs='+', help='股票代码列表')
    parser.add_argument('--start-date', '-d', default='2020-01-01', help='开始日期')
    parser.add_argument('--db-path', default='stock_data.db', help='数据库路径')
    parser.add_argument('--backup-path', help='备份文件路径')
    parser.add_argument('--use-watchlist', action='store_true', help='使用预设关注清单')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    
    args = parser.parse_args()
    
    # 配置日志
    level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    print("🚀 股票数据管理器")
    print("=" * 50)
    
    # 创建数据管理器
    manager = StockDataManager(args.db_path)
    
    try:
        if args.action == 'download':
            # 确定要处理的股票
            if args.use_watchlist:
                symbols = create_watchlist()
                print(f"📋 使用预设关注清单: {len(symbols)} 个股票")
            elif args.symbols:
                symbols = [s.upper() for s in args.symbols]
                print(f"📋 自定义股票清单: {len(symbols)} 个股票")
            else:
                print("❌ 请指定股票代码或使用 --use-watchlist 参数")
                print("💡 示例用法:")
                print("   python data_manager.py --use-watchlist")
                print("   python data_manager.py --symbols AAPL GOOGL MSFT")
                return
            
            # 执行批量下载
            results = manager.batch_download_and_store(symbols, args.start_date)
            
            # 显示数据报告
            manager.print_data_report()
            
        elif args.action == 'update':
            if not args.symbols:
                print("❌ 更新操作需要指定股票代码")
                return
            
            for symbol in args.symbols:
                success = manager.update_stock_data(symbol.upper())
                if success:
                    print(f"✅ {symbol} 更新成功")
                else:
                    print(f"❌ {symbol} 更新失败")
        
        elif args.action == 'report':
            manager.print_data_report()
        
        elif args.action == 'backup':
            if not args.backup_path:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_path = f"stock_data_backup_{timestamp}.db"
            else:
                backup_path = args.backup_path
            
            manager.backup_database(backup_path)
    
    finally:
        manager.close()

if __name__ == "__main__":
    main()