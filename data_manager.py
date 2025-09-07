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

from data_service.yfinance_downloader import YFinanceDataDownloader, create_watchlist
from analyzer.database import StockDatabase
from analyzer.hybrid_downloader import HybridStockDownloader

class StockDataManager:
    def __init__(self, db_path: str = "stock_data.db", max_retries: int = 3, base_delay: int = 30, use_hybrid: bool = True):
        """初始化股票数据管理器"""
        self.database = StockDatabase(db_path)
        self.use_hybrid = use_hybrid
        
        if use_hybrid:
            # 使用混合下载器（推荐）
            self.downloader = HybridStockDownloader(self.database, max_retries, base_delay)
        else:
            # 使用传统yfinance下载器
            self.downloader = YFinanceDataDownloader(
                database=self.database, 
                max_retries=max_retries, 
                base_delay=base_delay
            )
        self.logger = logging.getLogger(__name__)
    
    def download_and_store_stock(self, symbol: str, start_date: str = None, incremental: bool = True, use_retry: bool = True) -> bool:
        """下载并存储单个股票的数据"""
        try:
            mode_text = "增量更新" if incremental else "全量下载"
            retry_text = "（启用重试）" if use_retry else ""
            self.logger.info(f"🚀 处理股票: {symbol} ({mode_text}){retry_text}")
            
            if self.use_hybrid:
                # 使用混合下载器（自动选择策略）
                self.logger.info(f"🔄 使用混合策略处理 {symbol}")
                data = self.downloader.download_stock_data(symbol, start_date or "2000-01-01")
            else:
                # 下载综合数据（传统方式）
                data = self.downloader.download_comprehensive_data(symbol, start_date, incremental, use_retry)
            
            # 检查下载是否成功
            if 'error' in data:
                self.logger.error(f"❌ {symbol} 下载失败: {data['error']}")
                return False
            
            # 对于混合下载器，数据已经在下载过程中存储
            if not self.use_hybrid:
                # 存储到数据库（仅限传统下载器）
                self.database.store_comprehensive_data(symbol, data)
            
            self.logger.info(f"✅ {symbol} 数据处理完成")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 处理 {symbol} 时出错: {str(e)}")
            return False
    
    def batch_download_and_store(self, symbols: List[str], start_date: str = None, incremental: bool = True, use_retry: bool = True) -> Dict:
        """批量下载并存储股票数据"""
        if self.use_hybrid:
            # 使用混合下载器的批量方法
            self.logger.info(f"🔄 使用混合策略批量下载 {len(symbols)} 个股票")
            print(f"\n🔄 混合策略批量下载股票数据")
            print(f"📅 数据时间范围: {start_date or '2000-01-01'} 至今")
            print(f"📈 股票数量: {len(symbols)}")
            print("💡 策略: 新股票用Stooq批量下载 + 已有股票用yfinance增量更新")
            
            # 直接使用混合下载器的批量方法
            batch_results = self.downloader.batch_download(symbols, start_date or "2000-01-01")
            
            # 转换结果格式以保持兼容性
            results = {
                'total': len(symbols),
                'successful': len([r for r in batch_results.values() if 'error' not in r]),
                'failed': len([r for r in batch_results.values() if 'error' in r]),
                'skipped': 0,
                'details': {symbol: 'success' if 'error' not in result else 'failed' 
                          for symbol, result in batch_results.items()}
            }
            
            return results
        
        else:
            # 传统批量下载方式
            results = {
                'total': len(symbols),
                'successful': 0,
                'failed': 0,
                'skipped': 0,
                'details': {}
            }
            
            mode_text = "增量更新" if incremental else "全量下载"
            retry_text = "（启用重试）" if use_retry else ""
            self.logger.info(f"🎯 开始批量处理 {len(symbols)} 个股票 ({mode_text}){retry_text}")
            print(f"\n📊 批量{mode_text}股票数据{retry_text}")
            print(f"📅 数据时间范围: {start_date or '2020-01-01'} 至今")
            print(f"📈 股票数量: {len(symbols)}")
            print("=" * 60)
            
            for i, symbol in enumerate(symbols):
                print(f"\n[{i+1}/{len(symbols)}] 处理 {symbol}...")
                
                success = self.download_and_store_stock(symbol, start_date, incremental, use_retry)
                
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
            print(f"📊 批量{mode_text}结果:")
            print(f"✅ 成功: {results['successful']}")
            print(f"❌ 失败: {results['failed']}")
            print(f"📊 成功率: {results['successful']/results['total']*100:.1f}%")
            
            return results
    
    def update_stock_data(self, symbol: str, incremental: bool = True, use_retry: bool = True) -> bool:
        """更新单个股票的数据（默认增量更新）"""
        mode_text = "增量更新" if incremental else "全量更新" 
        retry_text = "（启用重试）" if use_retry else ""
        self.logger.info(f"🔄 {mode_text} {symbol} 的数据...{retry_text}")
        
        # 下载并存储数据（支持增量更新）
        return self.download_and_store_stock(symbol, incremental=incremental, use_retry=use_retry)
    
    def get_existing_stocks_info(self) -> Dict:
        """获取数据库中已有股票的信息"""
        try:
            existing_symbols = self.database.get_existing_symbols()
            
            info = {
                'total_stocks': len(existing_symbols),
                'symbols': existing_symbols,
                'last_updates': {}
            }
            
            # 获取每个股票的最后更新日期
            for symbol in existing_symbols:
                last_date = self.database.get_last_update_date(symbol)
                info['last_updates'][symbol] = last_date
            
            return info
            
        except Exception as e:
            self.logger.error(f"获取已有股票信息失败: {str(e)}")
            return {'error': str(e)}
    
    def print_existing_stocks_info(self):
        """打印已有股票信息"""
        info = self.get_existing_stocks_info()
        
        if 'error' in info:
            print(f"❌ 获取股票信息失败: {info['error']}")
            return
        
        print("\n" + "=" * 60)
        print("📊 数据库中已有股票信息")
        print("=" * 60)
        print(f"📈 总股票数量: {info['total_stocks']}")
        
        if info['symbols']:
            print("\n📋 股票列表及最后更新日期:")
            for symbol in sorted(info['symbols']):
                last_update = info['last_updates'].get(symbol, '未知')
                print(f"   {symbol}: {last_update}")
        else:
            print("\n📭 数据库中暂无股票数据")
    
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
    parser.add_argument('--action', '-a', choices=['download', 'update', 'report', 'backup', 'info'], 
                       default='download', help='执行的操作')
    parser.add_argument('--symbols', '-s', nargs='+', help='股票代码列表')
    parser.add_argument('--start-date', '-d', default='2020-01-01', help='开始日期')
    parser.add_argument('--db-path', default='stock_data.db', help='数据库路径')
    parser.add_argument('--backup-path', help='备份文件路径')
    parser.add_argument('--use-watchlist', action='store_true', help='使用预设关注清单')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    parser.add_argument('--full-download', action='store_true', help='强制全量下载（忽略增量更新）')
    parser.add_argument('--incremental', action='store_true', default=True, help='使用增量下载（默认）')
    parser.add_argument('--no-retry', action='store_true', help='禁用重试机制')
    parser.add_argument('--max-retries', type=int, default=3, help='最大重试次数（默认3次）')
    parser.add_argument('--no-hybrid', action='store_true', help='禁用混合下载策略，仅使用yfinance')
    parser.add_argument('--retry-delay', type=int, default=30, help='重试基础延迟时间（秒，默认30）')
    
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
    use_hybrid_mode = not args.no_hybrid  # 默认使用混合下载策略
    manager = StockDataManager(
        db_path=args.db_path,
        max_retries=args.max_retries,
        base_delay=args.retry_delay,
        use_hybrid=use_hybrid_mode
    )
    
    # 确定下载模式和重试设置
    incremental_mode = not args.full_download  # 如果指定了 --full-download，则不使用增量模式
    use_retry = not args.no_retry  # 如果指定了 --no-retry，则不使用重试
    
    # 显示下载策略
    strategy_text = "混合策略（Stooq批量+yfinance增量）" if use_hybrid_mode else "yfinance策略"
    print(f"🔄 下载策略: {strategy_text}")
    
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
                print("   python data_manager.py --use-watchlist --full-download  # 全量下载")
                return
            
            # 显示下载模式和重试设置
            mode_text = "增量下载" if incremental_mode else "全量下载"
            retry_text = f"重试机制（最大{args.max_retries}次，延迟{args.retry_delay}s）" if use_retry else "禁用重试"
            print(f"🔄 下载模式: {mode_text}")
            print(f"🔄 重试设置: {retry_text}")
            
            # 执行批量下载
            results = manager.batch_download_and_store(symbols, args.start_date, incremental_mode, use_retry)
            
            # 显示数据报告
            manager.print_data_report()
            
        elif args.action == 'update':
            if not args.symbols:
                print("❌ 更新操作需要指定股票代码")
                print("💡 示例用法:")
                print("   python data_manager.py --action update --symbols AAPL GOOGL")
                print("   python data_manager.py --action update --symbols AAPL --full-download")
                return
            
            for symbol in args.symbols:
                success = manager.update_stock_data(symbol.upper(), incremental_mode, use_retry)
                mode_text = "增量" if incremental_mode else "全量"
                retry_text = "（重试）" if use_retry else ""
                if success:
                    print(f"✅ {symbol} {mode_text}更新成功{retry_text}")
                else:
                    print(f"❌ {symbol} {mode_text}更新失败{retry_text}")
        
        elif args.action == 'info':
            # 显示数据库中已有股票信息
            manager.print_existing_stocks_info()
        
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
