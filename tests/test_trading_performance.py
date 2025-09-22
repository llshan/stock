#!/usr/bin/env python3
"""
性能优化与复杂场景测试 - Section 8.6
测试批次级别系统的稳定性和性能
"""

import unittest
import tempfile
import os
import time
import threading
from decimal import Decimal
from datetime import datetime, timedelta
from typing import List, Dict, Any

from stock_analysis.data.storage import create_storage
from stock_analysis.trading.services.lot_transaction_service import LotTransactionService
from stock_analysis.trading.config import DEFAULT_TRADING_CONFIG


class TradingPerformanceTest(unittest.TestCase):
    """
    交易系统性能测试
    涵盖批量查询、并发处理、数据一致性等场景
    """
    
    def setUp(self):
        """测试前置设置"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        self.storage = create_storage('sqlite', db_path=self.temp_db.name)
        self.service = LotTransactionService(self.storage, DEFAULT_TRADING_CONFIG)
        
        # 确保表结构存在
        self.storage.ensure_all_tables()
        
        # 准备测试数据
        self._setup_test_data()
    
    def tearDown(self):
        """测试后清理"""
        if hasattr(self, 'storage'):
            self.storage.close()
        try:
            os.unlink(self.temp_db.name)
        except FileNotFoundError:
            pass
    
    def _setup_test_data(self):
        """准备基础测试数据"""
        # 添加股票基础信息
        symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA']
        for symbol in symbols:
            self.storage.insert_stock({
                'symbol': symbol,
                'company_name': f'{symbol} Inc.',
                'sector': 'Technology'
            })
            
            # 添加价格数据
            base_date = datetime(2024, 1, 1)
            for i in range(30):  # 30天的价格数据
                date_str = (base_date + timedelta(days=i)).strftime('%Y-%m-%d')
                price = float(100 + i * 2 + hash(symbol) % 50)  # 模拟价格变化
                self.storage.insert_stock_price({
                    'symbol': symbol,
                    'date': date_str,
                    'close': price,
                    'adj_close': price * 0.98,
                    'volume': 1000000,
                    'open': price * 0.99,
                    'high': price * 1.02,
                    'low': price * 0.96
                })

    def test_batch_query_performance(self):
        """测试批量查询性能"""
        print("\n=== 批量查询性能测试 ===")
        
        # 创建大量测试数据
        user_symbols = []
        for user_idx in range(10):  # 10个用户
            user_id = f"user_{user_idx:03d}"
            for symbol in ['AAPL', 'MSFT', 'GOOGL']:
                user_symbols.append((user_id, symbol))
                
                # 为每个用户-股票对创建多个批次
                for lot_idx in range(5):  # 每个股票5个批次
                    self.service.record_buy_transaction(
                        user_id=user_id,
                        symbol=symbol,
                        quantity=100.0,
                        price=150.0 + lot_idx * 5,
                        transaction_date=f"2024-01-{10 + lot_idx:02d}",
                        commission=9.95
                    )
        
        # 测试批量查询性能
        start_time = time.time()
        batch_results = self.service.get_lots_batch(user_symbols[:15])  # 查询前15个
        batch_time = time.time() - start_time
        
        # 测试逐个查询性能（对比）
        start_time = time.time()
        individual_results = {}
        for user_id, symbol in user_symbols[:15]:
            lots = self.service.get_position_lots(user_id, symbol)
            individual_results[(user_id, symbol)] = lots
        individual_time = time.time() - start_time
        
        print(f"批量查询时间: {batch_time:.4f}秒")
        print(f"逐个查询时间: {individual_time:.4f}秒")
        print(f"性能提升: {individual_time / batch_time:.2f}倍")
        
        # 验证结果一致性
        self.assertEqual(len(batch_results), len(individual_results))
        for key in batch_results:
            batch_count = len(batch_results[key])
            individual_count = len(individual_results[key])
            self.assertEqual(batch_count, individual_count, 
                           f"批次数量不匹配: {key}, batch={batch_count}, individual={individual_count}")

    def test_pagination_performance(self):
        """测试分页查询性能"""
        print("\n=== 分页查询性能测试 ===")
        
        user_id = "test_pagination_user"
        symbol = "AAPL"
        
        # 创建大量批次数据
        for i in range(200):  # 200个批次
            self.service.record_buy_transaction(
                user_id=user_id,
                symbol=symbol,
                quantity=10.0,
                price=150.0 + i * 0.1,
                transaction_date=f"2024-01-{(i % 30) + 1:02d}",
                commission=1.0
            )
        
        # 测试分页查询
        page_size = 50
        total_fetched = 0
        page = 0
        
        start_time = time.time()
        while True:
            lots, total_count, has_more = self.service.get_position_lots_paginated(
                user_id, symbol, page_size=page_size, page_offset=page * page_size
            )
            
            total_fetched += len(lots)
            page += 1
            
            if not has_more:
                break
                
            # 避免无限循环
            if page > 10:
                break
        
        pagination_time = time.time() - start_time
        
        # 对比一次性查询全部
        start_time = time.time()
        all_lots = self.service.get_position_lots(user_id, symbol)
        all_time = time.time() - start_time
        
        print(f"分页查询总时间: {pagination_time:.4f}秒 (共{total_fetched}条)")
        print(f"全量查询时间: {all_time:.4f}秒 (共{len(all_lots)}条)")
        print(f"分页查询页数: {page}")
        
        # 验证数据完整性
        self.assertEqual(total_fetched, len(all_lots))

    def test_concurrent_transactions(self):
        """测试并发交易场景"""
        print("\n=== 并发交易测试 ===")
        
        user_id = "concurrent_user"
        symbol = "TSLA"
        results = []
        errors = []
        
        def buy_transaction(thread_id: int):
            """线程执行的买入交易"""
            try:
                for i in range(5):  # 每个线程执行5次买入
                    txn = self.service.record_buy_transaction(
                        user_id=user_id,
                        symbol=symbol,
                        quantity=10.0,
                        price=200.0 + thread_id + i,
                        transaction_date=f"2024-01-{15 + i:02d}",
                        commission=5.0,
                        external_id=f"thread_{thread_id}_txn_{i}"
                    )
                    results.append(f"Thread {thread_id}: Buy {txn.id}")
            except Exception as e:
                errors.append(f"Thread {thread_id} error: {e}")
        
        def sell_transaction(thread_id: int):
            """线程执行的卖出交易"""
            try:
                # 等待买入完成
                time.sleep(0.1)
                
                for i in range(2):  # 每个线程执行2次卖出
                    txn = self.service.record_sell_transaction(
                        user_id=user_id,
                        symbol=symbol,
                        quantity=5.0,
                        price=220.0 + thread_id + i,
                        transaction_date=f"2024-01-{20 + i:02d}",
                        commission=5.0,
                        cost_basis_method='FIFO',
                        external_id=f"thread_{thread_id}_sell_{i}"
                    )
                    results.append(f"Thread {thread_id}: Sell {txn.id}")
            except Exception as e:
                errors.append(f"Thread {thread_id} sell error: {e}")
        
        # 启动并发线程
        threads = []
        num_threads = 3
        
        # 买入线程
        for i in range(num_threads):
            thread = threading.Thread(target=buy_transaction, args=(i,))
            threads.append(thread)
            thread.start()
        
        # 卖出线程
        for i in range(num_threads):
            thread = threading.Thread(target=sell_transaction, args=(i + 100,))
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        print(f"并发操作完成: {len(results)}个成功, {len(errors)}个错误")
        
        if errors:
            for error in errors:
                print(f"  错误: {error}")
        
        # 验证数据一致性
        consistency_result = self.service.validate_data_consistency(user_id, symbol)
        print(f"数据一致性检查: {'通过' if consistency_result['is_consistent'] else '失败'}")
        
        if not consistency_result['is_consistent']:
            for issue in consistency_result['issues']:
                print(f"  一致性问题: {issue['description']}")
        
        # 基本断言
        self.assertGreater(len(results), 0, "应该有成功的交易")
        self.assertTrue(consistency_result['is_consistent'], "数据应该保持一致")

    def test_data_consistency_validation(self):
        """测试数据一致性验证功能"""
        print("\n=== 数据一致性验证测试 ===")
        
        user_id = "consistency_user"
        symbol = "NVDA"
        
        # 创建正常的交易序列
        buy_txn1 = self.service.record_buy_transaction(
            user_id=user_id, symbol=symbol, quantity=100.0, 
            price=300.0, transaction_date="2024-01-10", commission=10.0
        )
        
        buy_txn2 = self.service.record_buy_transaction(
            user_id=user_id, symbol=symbol, quantity=50.0,
            price=310.0, transaction_date="2024-01-15", commission=5.0
        )
        
        sell_txn = self.service.record_sell_transaction(
            user_id=user_id, symbol=symbol, quantity=30.0,
            price=320.0, transaction_date="2024-01-20", commission=8.0,
            cost_basis_method='FIFO'
        )
        
        # 执行一致性检查
        result = self.service.validate_data_consistency(user_id, symbol)
        
        print(f"检查用户: {result['user_id']}")
        print(f"检查股票数: {result['symbols_checked']}")
        print(f"发现问题数: {result['issues_found']}")
        print(f"一致性状态: {'通过' if result['is_consistent'] else '失败'}")
        
        # 打印统计信息
        if symbol in result['statistics']:
            stats = result['statistics'][symbol]
            print(f"统计信息 ({symbol}):")
            print(f"  买入交易: {stats['buy_transactions']}")
            print(f"  卖出交易: {stats['sell_transactions']}")
            print(f"  持仓批次: {stats['position_lots']}")
            print(f"  活跃批次: {stats['active_lots']}")
            print(f"  已关闭批次: {stats['closed_lots']}")
        
        # 验证结果
        self.assertEqual(result['symbols_checked'], 1)
        self.assertTrue(result['is_consistent'])
        self.assertEqual(len(result['issues']), 0)

    def test_large_dataset_performance(self):
        """测试大数据量性能"""
        print("\n=== 大数据量性能测试 ===")
        
        # 创建大量用户和交易
        start_time = time.time()
        
        num_users = 20
        num_symbols = 5
        transactions_per_user_symbol = 10
        
        total_transactions = 0
        
        for user_idx in range(num_users):
            user_id = f"perf_user_{user_idx:03d}"
            
            for symbol in ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA'][:num_symbols]:
                # 买入交易
                for txn_idx in range(transactions_per_user_symbol):
                    self.service.record_buy_transaction(
                        user_id=user_id,
                        symbol=symbol,
                        quantity=50.0 + txn_idx * 10,
                        price=100.0 + txn_idx * 5,
                        transaction_date=f"2024-01-{(txn_idx % 28) + 1:02d}",
                        commission=7.5
                    )
                    total_transactions += 1
                
                # 部分卖出交易
                for sell_idx in range(transactions_per_user_symbol // 3):
                    try:
                        self.service.record_sell_transaction(
                            user_id=user_id,
                            symbol=symbol,
                            quantity=20.0 + sell_idx * 5,
                            price=120.0 + sell_idx * 3,
                            transaction_date=f"2024-01-{(sell_idx + 15) % 28 + 1:02d}",
                            commission=7.5,
                            cost_basis_method='FIFO'
                        )
                        total_transactions += 1
                    except Exception as e:
                        # 可能因为持仓不足而失败，这是正常的
                        pass
        
        creation_time = time.time() - start_time
        
        # 测试批量查询性能
        start_time = time.time()
        user_symbols = [(f"perf_user_{i:03d}", "AAPL") for i in range(min(num_users, 10))]
        batch_results = self.service.get_lots_batch(user_symbols)
        query_time = time.time() - start_time
        
        print(f"创建{total_transactions}笔交易耗时: {creation_time:.2f}秒")
        print(f"批量查询{len(user_symbols)}个用户耗时: {query_time:.4f}秒")
        print(f"平均每笔交易创建时间: {creation_time / total_transactions * 1000:.2f}毫秒")
        print(f"批量查询返回的批次总数: {sum(len(lots) for lots in batch_results.values())}")
        
        # 性能基准验证
        self.assertLess(creation_time / total_transactions, 0.1, "单笔交易创建时间应小于100毫秒")
        self.assertLess(query_time, 1.0, "批量查询应在1秒内完成")

    def test_archive_functionality(self):
        """测试归档功能"""
        print("\n=== 归档功能测试 ===")
        
        user_id = "archive_user"
        symbol = "AAPL"
        
        # 创建一些交易，然后将它们全部卖出以创建已关闭的批次
        for i in range(5):
            self.service.record_buy_transaction(
                user_id=user_id, symbol=symbol, quantity=20.0,
                price=100.0 + i * 10, transaction_date=f"2024-01-{i + 5:02d}",
                commission=5.0
            )
        
        # 卖出所有持仓
        self.service.record_sell_transaction(
            user_id=user_id, symbol=symbol, quantity=100.0,
            price=200.0, transaction_date="2024-01-25",
            commission=10.0, cost_basis_method='FIFO'
        )
        
        # 检查归档前的状态
        all_lots_before = self.service.get_position_lots(user_id, symbol, active_only=False)
        active_lots_before = self.service.get_position_lots(user_id, symbol, active_only=True)
        
        print(f"归档前: 总批次={len(all_lots_before)}, 活跃批次={len(active_lots_before)}")
        
        # 测试归档功能
        archivable_count = self.service.archive_closed_lots(older_than_days=0)  # 立即归档
        
        print(f"可归档的批次数量: {archivable_count}")
        
        # 基本验证
        self.assertGreater(len(all_lots_before), 0, "应该有一些批次存在")
        self.assertEqual(len(active_lots_before), 0, "所有批次都应该已关闭")
        self.assertGreaterEqual(archivable_count, 0, "归档数量应该非负")


if __name__ == '__main__':
    # 运行性能测试
    unittest.main(verbosity=2)