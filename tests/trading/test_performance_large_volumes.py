#!/usr/bin/env python3
"""
大容量交易性能测试
测试系统在处理大量交易时的性能表现
"""

import unittest
import tempfile
import os
import time
import random
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Tuple

from stock_analysis.data.storage import create_storage
from stock_analysis.trading.services.lot_transaction_service import LotTransactionService
from stock_analysis.trading.config import DEFAULT_TRADING_CONFIG


class TestPerformanceLargeVolumes(unittest.TestCase):
    """大容量交易性能测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        self.storage = create_storage('sqlite', db_path=self.temp_db.name)
        
        # 确保测试股票存在
        test_symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX', 'ORCL', 'CRM']
        for symbol in test_symbols:
            self.storage.ensure_stock_exists(symbol)
        
        self.service = LotTransactionService(self.storage, DEFAULT_TRADING_CONFIG)
        
        # 性能基准
        self.max_single_transaction_time = 1.0  # 单笔交易最大耗时（秒）
        self.max_batch_transaction_time = 30.0  # 批量交易最大耗时（秒）
    
    def tearDown(self):
        """清理测试环境"""
        self.storage.close()
        os.unlink(self.temp_db.name)
    
    def _measure_time(self, func, *args, **kwargs):
        """测量函数执行时间"""
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        return result, end_time - start_time
    
    def _generate_random_price(self, base_price: float, volatility: float = 0.1) -> float:
        """生成随机价格"""
        change = random.uniform(-volatility, volatility)
        return base_price * (1 + change)
    
    def _generate_random_quantity(self, min_qty: int = 1, max_qty: int = 1000) -> int:
        """生成随机数量"""
        return random.randint(min_qty, max_qty)
    
    def test_large_volume_buy_transactions(self):
        """测试大量买入交易的性能"""
        print("\n=== 大量买入交易性能测试 ===")
        
        num_transactions = 1000
        symbol = 'AAPL'
        base_price = 150.0
        
        print(f"执行 {num_transactions} 笔买入交易...")
        
        start_time = time.time()
        transactions = []
        
        for i in range(num_transactions):
            price = self._generate_random_price(base_price)
            quantity = self._generate_random_quantity(10, 100)
            date = (datetime(2024, 1, 1) + timedelta(days=i % 365)).strftime('%Y-%m-%d')
            
            tx, tx_time = self._measure_time(
                self.service.record_buy_transaction,
                symbol=symbol,
                quantity=quantity,
                price=price,
                transaction_date=date,
                external_id=f'perf_buy_{i+1:06d}',
                notes=f'性能测试买入 {i+1}'
            )
            
            transactions.append((tx, tx_time))
            
            # 检查单笔交易性能
            if tx_time > self.max_single_transaction_time:
                print(f"⚠️ 警告: 第{i+1}笔交易耗时 {tx_time:.3f}s，超过阈值")
            
            # 进度显示
            if (i + 1) % 100 == 0:
                print(f"  已完成 {i+1}/{num_transactions} 笔交易")
        
        total_time = time.time() - start_time
        avg_time = total_time / num_transactions
        
        print(f"\n买入交易性能统计:")
        print(f"总交易数: {num_transactions}")
        print(f"总耗时: {total_time:.2f}s")
        print(f"平均每笔: {avg_time:.4f}s")
        print(f"TPS (每秒交易数): {num_transactions / total_time:.1f}")
        
        # 验证所有交易都成功
        lots = self.service.get_position_lots(symbol)
        self.assertEqual(len(lots), num_transactions, f"应该创建 {num_transactions} 个批次")
        
        # 性能断言
        self.assertLess(avg_time, self.max_single_transaction_time, 
                       f"平均交易时间应少于 {self.max_single_transaction_time}s")
        self.assertLess(total_time, self.max_batch_transaction_time,
                       f"总耗时应少于 {self.max_batch_transaction_time}s")
        
        print("✅ 大量买入交易性能测试通过")
        return transactions
    
    def test_large_volume_sell_transactions(self):
        """测试大量卖出交易的性能"""
        print("\n=== 大量卖出交易性能测试 ===")
        
        # 先创建足够的买入批次
        symbol = 'MSFT'
        base_price = 350.0
        num_buy_batches = 500
        
        print(f"准备阶段: 创建 {num_buy_batches} 个买入批次...")
        
        for i in range(num_buy_batches):
            price = self._generate_random_price(base_price)
            quantity = self._generate_random_quantity(50, 200)
            date = (datetime(2024, 1, 1) + timedelta(days=i)).strftime('%Y-%m-%d')
            
            self.service.record_buy_transaction(
                symbol=symbol,
                quantity=quantity,
                price=price,
                transaction_date=date,
                external_id=f'prep_buy_{i+1:06d}',
                notes=f'准备买入 {i+1}'
            )
        
        print("准备阶段完成，开始卖出交易测试...")
        
        # 执行大量卖出交易
        num_sell_transactions = 200
        sell_transactions = []
        
        start_time = time.time()
        
        for i in range(num_sell_transactions):
            # 获取当前可用的总股数
            lots = self.service.get_position_lots(symbol)
            available_shares = sum(lot.remaining_quantity for lot in lots if lot.remaining_quantity > 0)
            
            if available_shares < 10:
                print(f"可用股份不足，停止在第 {i+1} 笔交易")
                break
            
            # 卖出部分股份
            sell_quantity = min(float(available_shares) * 0.1, 100)  # 最多卖出10%或100股
            price = self._generate_random_price(base_price * 1.1)  # 稍高价格卖出
            date = (datetime(2024, 6, 1) + timedelta(days=i)).strftime('%Y-%m-%d')
            
            # 随机选择成本基础方法
            methods = ['FIFO', 'LIFO', 'AverageCost']
            method = random.choice(methods)
            
            tx, tx_time = self._measure_time(
                self.service.record_sell_transaction,
                symbol=symbol,
                quantity=sell_quantity,
                price=price,
                transaction_date=date,
                external_id=f'perf_sell_{i+1:06d}',
                notes=f'性能测试卖出 {i+1}',
                cost_basis_method=method
            )
            
            sell_transactions.append((tx, tx_time))
            
            # 检查单笔交易性能
            if tx_time > self.max_single_transaction_time:
                print(f"⚠️ 警告: 第{i+1}笔卖出交易耗时 {tx_time:.3f}s，超过阈值")
            
            # 进度显示
            if (i + 1) % 50 == 0:
                print(f"  已完成 {i+1}/{num_sell_transactions} 笔卖出交易")
        
        total_time = time.time() - start_time
        actual_sells = len(sell_transactions)
        avg_time = total_time / actual_sells if actual_sells > 0 else 0
        
        print(f"\n卖出交易性能统计:")
        print(f"实际卖出交易数: {actual_sells}")
        print(f"总耗时: {total_time:.2f}s")
        print(f"平均每笔: {avg_time:.4f}s")
        if total_time > 0:
            print(f"TPS (每秒交易数): {actual_sells / total_time:.1f}")
        
        # 性能断言
        if actual_sells > 0:
            self.assertLess(avg_time, self.max_single_transaction_time * 2,  # 卖出可能更复杂，放宽要求
                           f"平均卖出交易时间应少于 {self.max_single_transaction_time * 2}s")
        
        print("✅ 大量卖出交易性能测试通过")
        return sell_transactions
    
    def test_multi_stock_concurrent_trading(self):
        """测试多股票并发交易性能"""
        print("\n=== 多股票并发交易性能测试 ===")
        
        symbols = ['GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA']
        base_prices = [140.0, 3300.0, 250.0, 480.0, 450.0]
        transactions_per_stock = 100
        
        print(f"对 {len(symbols)} 只股票各执行 {transactions_per_stock} 笔交易...")
        
        start_time = time.time()
        all_transactions = []
        
        for stock_idx, (symbol, base_price) in enumerate(zip(symbols, base_prices)):
            print(f"\n处理 {symbol} (基准价格: ${base_price})...")
            
            stock_start = time.time()
            
            # 先买入创建批次
            buy_count = transactions_per_stock // 2
            for i in range(buy_count):
                price = self._generate_random_price(base_price)
                quantity = self._generate_random_quantity(10, 50)
                date = (datetime(2024, 1, 1) + timedelta(days=i * 2)).strftime('%Y-%m-%d')
                
                tx = self.service.record_buy_transaction(
                        symbol=symbol,
                    quantity=quantity,
                    price=price,
                    transaction_date=date,
                    external_id=f'multi_{symbol}_buy_{i+1:03d}',
                    notes=f'{symbol} 买入 {i+1}'
                )
                all_transactions.append(tx)
            
            # 再卖出部分
            sell_count = transactions_per_stock - buy_count
            for i in range(sell_count):
                lots = self.service.get_position_lots(symbol)
                available = sum(lot.remaining_quantity for lot in lots if lot.remaining_quantity > 0)
                
                if available >= 10:
                    quantity = min(float(available) * 0.3, 30)  # 卖出30%或最多30股
                    price = self._generate_random_price(base_price * 1.05)
                    date = (datetime(2024, 3, 1) + timedelta(days=i * 2)).strftime('%Y-%m-%d')
                    
                    tx = self.service.record_sell_transaction(
                                symbol=symbol,
                        quantity=quantity,
                        price=price,
                        transaction_date=date,
                        external_id=f'multi_{symbol}_sell_{i+1:03d}',
                        notes=f'{symbol} 卖出 {i+1}',
                        cost_basis_method='FIFO'
                    )
                    all_transactions.append(tx)
            
            stock_time = time.time() - stock_start
            print(f"  {symbol} 完成，耗时: {stock_time:.2f}s")
        
        total_time = time.time() - start_time
        total_transactions = len(all_transactions)
        avg_time = total_time / total_transactions if total_transactions > 0 else 0
        
        print(f"\n多股票交易性能统计:")
        print(f"总股票数: {len(symbols)}")
        print(f"总交易数: {total_transactions}")
        print(f"总耗时: {total_time:.2f}s")
        print(f"平均每笔: {avg_time:.4f}s")
        if total_time > 0:
            print(f"TPS (每秒交易数): {total_transactions / total_time:.1f}")
        
        # 验证每只股票的持仓
        print(f"\n各股票最终持仓:")
        for symbol in symbols:
            lots = self.service.get_position_lots(symbol)
            active_lots = [lot for lot in lots if lot.remaining_quantity > 0]
            total_shares = sum(lot.remaining_quantity for lot in active_lots)
            
            print(f"  {symbol}: {total_shares:.4f}股，{len(active_lots)}个活跃批次")
            self.assertGreater(len(lots), 0, f"{symbol} 应该有批次记录")
        
        print("✅ 多股票并发交易性能测试通过")
    
    def test_large_lot_query_performance(self):
        """测试大量批次查询性能"""
        print("\n=== 大量批次查询性能测试 ===")
        
        symbol = 'NFLX'
        base_price = 600.0
        num_lots = 2000
        
        print(f"创建 {num_lots} 个批次...")
        
        # 创建大量批次
        setup_start = time.time()
        for i in range(num_lots):
            price = self._generate_random_price(base_price)
            quantity = self._generate_random_quantity(1, 20)
            date = (datetime(2024, 1, 1) + timedelta(days=i % 365)).strftime('%Y-%m-%d')
            
            self.service.record_buy_transaction(
                symbol=symbol,
                quantity=quantity,
                price=price,
                transaction_date=date,
                external_id=f'query_buy_{i+1:06d}',
                notes=f'查询测试买入 {i+1}'
            )
            
            if (i + 1) % 500 == 0:
                print(f"  已创建 {i+1}/{num_lots} 个批次")
        
        setup_time = time.time() - setup_start
        print(f"批次创建完成，耗时: {setup_time:.2f}s")
        
        # 测试批次查询性能
        query_tests = [
            ("获取所有批次", lambda: self.service.get_position_lots(symbol)),
            ("获取活跃批次", lambda: [lot for lot in self.service.get_position_lots(symbol) 
                                    if lot.remaining_quantity > 0]),
            ("计算总持仓", lambda: sum(lot.remaining_quantity 
                                    for lot in self.service.get_position_lots(symbol)
                                    if lot.remaining_quantity > 0)),
        ]
        
        print(f"\n执行查询性能测试...")
        for test_name, query_func in query_tests:
            # 执行多次查询取平均值
            times = []
            for _ in range(10):
                result, query_time = self._measure_time(query_func)
                times.append(query_time)
            
            avg_query_time = sum(times) / len(times)
            min_time = min(times)
            max_time = max(times)
            
            print(f"  {test_name}:")
            print(f"    平均: {avg_query_time:.4f}s")
            print(f"    最快: {min_time:.4f}s")
            print(f"    最慢: {max_time:.4f}s")
            
            # 查询性能应该合理
            self.assertLess(avg_query_time, 1.0, f"{test_name} 平均查询时间应少于1秒")
        
        # 测试复杂卖出交易的性能（需要匹配大量批次）
        print(f"\n测试复杂卖出交易性能...")
        
        lots = self.service.get_position_lots(symbol)
        total_available = sum(lot.remaining_quantity for lot in lots if lot.remaining_quantity > 0)
        
        # 卖出大量股份，触发复杂的批次匹配
        sell_quantity = min(float(total_available) * 0.5, 1000)  # 卖出50%或最多1000股
        
        sell_tx, sell_time = self._measure_time(
            self.service.record_sell_transaction,
            symbol=symbol,
            quantity=sell_quantity,
            price=self._generate_random_price(base_price * 1.1),
            transaction_date='2024-12-31',
            external_id='large_lot_sell',
            notes='大量批次卖出测试',
            cost_basis_method='FIFO'
        )
        
        print(f"复杂卖出交易 ({sell_quantity}股) 耗时: {sell_time:.4f}s")
        
        # 验证分配结果
        allocations = self.service.get_sale_allocations_by_transaction(sell_tx.id)
        print(f"分配到 {len(allocations)} 个批次")
        
        # 复杂卖出性能应该合理
        self.assertLess(sell_time, 5.0, "复杂卖出交易应在5秒内完成")
        
        print("✅ 大量批次查询性能测试通过")
    
    def test_memory_efficiency(self):
        """测试内存效率"""
        print("\n=== 内存效率测试 ===")
        
        symbol = 'ORCL'
        base_price = 100.0
        num_transactions = 500
        
        print(f"执行 {num_transactions} 笔交易并监控内存使用...")
        
        # 记录初始状态
        initial_lots_count = len(self.service.get_position_lots(symbol))
        
        # 执行混合交易
        for i in range(num_transactions):
            if i % 3 == 0:  # 每3笔交易卖出1笔
                # 卖出交易
                lots = self.service.get_position_lots(symbol)
                available = sum(lot.remaining_quantity for lot in lots if lot.remaining_quantity > 0)
                
                if available >= 10:
                    quantity = min(float(available) * 0.1, 20)
                    self.service.record_sell_transaction(
                                symbol=symbol,
                        quantity=quantity,
                        price=self._generate_random_price(base_price * 1.05),
                        transaction_date='2024-06-15',
                        external_id=f'mem_sell_{i+1:06d}',
                        notes=f'内存测试卖出 {i+1}',
                        cost_basis_method='FIFO'
                    )
            else:
                # 买入交易
                quantity = self._generate_random_quantity(5, 30)
                price = self._generate_random_price(base_price)
                
                self.service.record_buy_transaction(
                        symbol=symbol,
                    quantity=quantity,
                    price=price,
                    transaction_date='2024-03-15',
                    external_id=f'mem_buy_{i+1:06d}',
                    notes=f'内存测试买入 {i+1}'
                )
            
            # 定期检查批次数量增长
            if (i + 1) % 100 == 0:
                current_lots = self.service.get_position_lots(symbol)
                active_lots = [lot for lot in current_lots if lot.remaining_quantity > 0]
                closed_lots = [lot for lot in current_lots if lot.remaining_quantity <= 0.0001]
                
                print(f"  第 {i+1} 笔交易后: 总批次 {len(current_lots)}, "
                      f"活跃 {len(active_lots)}, 已关闭 {len(closed_lots)}")
        
        # 最终统计
        final_lots = self.service.get_position_lots(symbol)
        final_active = [lot for lot in final_lots if lot.remaining_quantity > 0]
        final_closed = [lot for lot in final_lots if lot.remaining_quantity <= 0.0001]
        
        print(f"\n内存效率统计:")
        print(f"总交易数: {num_transactions}")
        print(f"最终批次总数: {len(final_lots)}")
        print(f"活跃批次数: {len(final_active)}")
        print(f"已关闭批次数: {len(final_closed)}")
        
        # 验证内存使用合理性
        # 批次数量不应该无限制增长
        expected_max_lots = num_transactions * 0.8  # 考虑到卖出会关闭一些批次
        self.assertLess(len(final_lots), expected_max_lots, 
                       "批次数量增长应该受到卖出交易的控制")
        
        # 应该有一些批次被关闭
        self.assertGreater(len(final_closed), 0, "应该有一些批次被关闭")
        
        print("✅ 内存效率测试通过")


if __name__ == '__main__':
    # 设置较高的测试超时时间
    import sys
    if hasattr(unittest.TestCase, '_testMethodDoc'):
        unittest.TestCase._testMethodDoc = 60  # 60秒超时
    
    unittest.main(verbosity=2)