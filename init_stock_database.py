#!/usr/bin/env python3
"""
使用Stooq数据源初始化股票数据库
作为yfinance的替代方案
"""

import os
import sys
import argparse
import logging
from datetime import datetime, timedelta
from typing import List, Dict

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from analyzer.stooq_downloader import StooqDataDownloader
from analyzer.database import StockDatabase

class StooqDatabaseInitializer:
    def __init__(self, db_path: str = "stock_data_stooq.db", max_retries: int = 3):
        """
        初始化Stooq数据库初始化器
        
        Args:
            db_path: 数据库路径
            max_retries: 最大重试次数
        """
        self.database = StockDatabase(db_path)
        self.downloader = StooqDataDownloader(max_retries=max_retries)
        self.logger = logging.getLogger(__name__)
        self.db_path = db_path
        
    def initialize_database(self, symbols: List[str], start_date: str = "2000-01-01") -> Dict:
        """
        初始化数据库，下载股票历史数据
        
        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            
        Returns:
            初始化结果统计
        """
        results = {
            'total': len(symbols),
            'successful': 0,
            'failed': 0,
            'details': {},
            'start_time': datetime.now().isoformat(),
            'data_source': 'Stooq'
        }
        
        print(f"🌐 使用Stooq初始化股票数据库")
        print(f"💾 数据库路径: {self.db_path}")
        print(f"📅 数据时间范围: {start_date} 至今")
        print(f"📈 股票数量: {len(symbols)}")
        print("=" * 60)
        
        # 测试Stooq连接
        print("🔍 测试Stooq连接...")
        if not self.downloader.test_connection():
            print("❌ Stooq连接失败，无法初始化数据库")
            results['connection_error'] = True
            return results
        
        print("✅ Stooq连接正常，开始下载数据...\n")
        
        for i, symbol in enumerate(symbols):
            print(f"[{i+1}/{len(symbols)}] 处理 {symbol}...")
            
            try:
                # 从Stooq下载数据
                stock_data = self.downloader.download_stock_data(symbol, start_date)
                
                if 'error' in stock_data:
                    print(f"❌ {symbol} 下载失败: {stock_data['error']}")
                    results['failed'] += 1
                    results['details'][symbol] = 'download_failed'
                    continue
                
                # 转换为与现有数据库兼容的格式
                comprehensive_data = self._convert_to_comprehensive_format(stock_data)
                
                # 存储到数据库
                self.database.store_comprehensive_data(symbol, comprehensive_data)
                
                print(f"✅ {symbol} 完成 ({stock_data['data_points']} 个数据点)")
                results['successful'] += 1
                results['details'][symbol] = 'success'
                
            except Exception as e:
                self.logger.error(f"处理 {symbol} 时出错: {str(e)}")
                print(f"❌ {symbol} 处理失败: {str(e)}")
                results['failed'] += 1
                results['details'][symbol] = 'processing_failed'
        
        results['end_time'] = datetime.now().isoformat()
        results['success_rate'] = results['successful'] / results['total'] * 100
        
        # 显示最终结果
        self._display_results(results)
        
        return results
    
    def _convert_to_comprehensive_format(self, stock_data: Dict) -> Dict:
        """将Stooq数据转换为comprehensive_data格式"""
        symbol = stock_data['symbol']
        
        # 创建基本信息
        basic_info = {
            'company_name': f'{symbol} Inc.',
            'sector': 'Unknown',
            'industry': 'Unknown',
            'market_cap': 0,
            'employees': 0,
            'description': f'{symbol} stock data from Stooq'
        }
        
        # 评估数据质量
        data_quality = {
            'stock_data_available': True,
            'financial_data_available': False,  # Stooq主要提供价格数据
            'data_completeness': 0.6,  # 只有价格数据，没有财务数据
            'quality_grade': 'B - 良好',
            'issues': ['仅提供价格数据，无财务报表']
        }
        
        # 构造comprehensive格式
        comprehensive_data = {
            'symbol': symbol,
            'download_timestamp': datetime.now().isoformat(),
            'stock_data': stock_data,
            'financial_data': {
                'error': 'Stooq不提供财务数据',
                'basic_info': basic_info
            },
            'data_quality': data_quality
        }
        
        return comprehensive_data
    
    def _display_results(self, results: Dict):
        """显示初始化结果"""
        print("\n" + "=" * 60)
        print("📊 数据库初始化结果:")
        print("=" * 60)
        print(f"✅ 成功: {results['successful']} 个股票")
        print(f"❌ 失败: {results['failed']} 个股票")
        print(f"📊 成功率: {results['success_rate']:.1f}%")
        print(f"⏰ 总耗时: {self._calculate_duration(results['start_time'], results['end_time'])}")
        
        if results['failed'] > 0:
            print(f"\n❌ 失败的股票:")
            for symbol, status in results['details'].items():
                if status != 'success':
                    print(f"   • {symbol}: {status}")
        
        print(f"\n💾 数据库文件: {self.db_path}")
        print(f"📈 数据源: Stooq")
    
    def _calculate_duration(self, start_time: str, end_time: str) -> str:
        """计算执行时间"""
        try:
            start = datetime.fromisoformat(start_time)
            end = datetime.fromisoformat(end_time)
            duration = end - start
            return str(duration).split('.')[0]  # 去掉微秒
        except:
            return "未知"
    
    def verify_database(self) -> Dict:
        """验证数据库内容"""
        print("\n🔍 验证数据库内容...")
        
        try:
            # 获取股票列表
            existing_symbols = self.database.get_existing_symbols()
            
            verification = {
                'total_stocks': len(existing_symbols),
                'symbols': existing_symbols,
                'sample_data': {}
            }
            
            print(f"📈 数据库中共有 {len(existing_symbols)} 个股票")
            
            # 检查所有股票的数据并找出最早时间
            earliest_date = None
            for symbol in existing_symbols:
                price_data = self.database.get_stock_prices(symbol)
                if len(price_data) > 0:
                    min_date = price_data['date'].min()
                    max_date = price_data['date'].max()
                    latest_price = float(price_data.iloc[-1]['close_price'])
                    
                    verification['sample_data'][symbol] = {
                        'records': len(price_data),
                        'date_range': f"{min_date} 到 {max_date}",
                        'earliest_date': min_date,
                        'latest_price': latest_price
                    }
                    
                    # 更新全局最早日期
                    if earliest_date is None or min_date < earliest_date:
                        earliest_date = min_date
                    
                    print(f"   {symbol}: {len(price_data)} 条记录, 时间范围: {min_date} 到 {max_date}, 最新价格: ${latest_price:.2f}")
            
            # 显示整个数据库的最早数据时间
            if earliest_date:
                verification['earliest_date'] = earliest_date
                print(f"\n📅 数据库最早数据时间: {earliest_date}")
            
            return verification
            
        except Exception as e:
            self.logger.error(f"验证数据库时出错: {str(e)}")
            return {'error': str(e)}
    
    def close(self):
        """关闭数据库连接"""
        self.database.close()

def create_default_watchlist() -> List[str]:
    """创建默认股票观察清单"""
    return [
        # 大型科技股
        "AAPL", "GOOGL", "MSFT", "AMZN", "META", "TSLA", "NVDA",
        
        # 热门成长股
        "NFLX", "UBER", "ZOOM",
        
        # 传统蓝筹股
        "JPM", "JNJ", "PG", "KO", "WMT",
        
        # 其他重要股票
        "DIS", "V", "MA"
    ]

def main():
    """命令行主函数"""
    parser = argparse.ArgumentParser(description='使用Stooq初始化股票数据库')
    parser.add_argument('--symbols', '-s', nargs='+', help='股票代码列表')
    parser.add_argument('--start-date', '-d', default='2000-01-01', help='开始日期')
    parser.add_argument('--db-path', default='stock_data_stooq.db', help='数据库路径')
    parser.add_argument('--use-watchlist', action='store_true', help='使用默认观察清单')
    parser.add_argument('--max-retries', type=int, default=3, help='最大重试次数')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    parser.add_argument('--verify-only', action='store_true', help='仅验证现有数据库')
    
    args = parser.parse_args()
    
    # 配置日志
    level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    print("🌐 Stooq股票数据库初始化器")
    print("=" * 50)
    
    # 创建初始化器
    initializer = StooqDatabaseInitializer(
        db_path=args.db_path,
        max_retries=args.max_retries
    )
    
    try:
        if args.verify_only:
            # 仅验证现有数据库
            verification = initializer.verify_database()
            if 'error' not in verification:
                print(f"\n✅ 数据库验证完成")
            else:
                print(f"\n❌ 数据库验证失败: {verification['error']}")
        
        else:
            # 初始化数据库
            if args.use_watchlist:
                symbols = create_default_watchlist()
                print(f"📋 使用默认观察清单: {len(symbols)} 个股票")
            elif args.symbols:
                symbols = [s.upper() for s in args.symbols]
                print(f"📋 自定义股票清单: {len(symbols)} 个股票")
            else:
                print("❌ 请指定股票代码或使用 --use-watchlist 参数")
                print("💡 示例用法:")
                print("   python init_database_stooq.py --use-watchlist")
                print("   python init_database_stooq.py --symbols AAPL GOOGL MSFT")
                return
            
            # 执行初始化
            results = initializer.initialize_database(symbols, args.start_date)
            
            # 验证结果
            if results['successful'] > 0:
                initializer.verify_database()
                
                print(f"\n💡 后续可以使用常规data_manager操作此数据库:")
                print(f"   python data_manager.py --db-path {args.db_path} --action info")
                print(f"   python data_manager.py --db-path {args.db_path} --action report")
            
    finally:
        initializer.close()

if __name__ == "__main__":
    main()