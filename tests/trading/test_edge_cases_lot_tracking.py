#!/usr/bin/env python3
"""
边缘情况和异常场景测试
测试批次追踪系统在各种边缘情况下的行为
"""

import unittest
import tempfile
import os
from datetime import datetime, timedelta
from decimal import Decimal

from stock_analysis.data.storage import create_storage
from stock_analysis.trading.services.lot_transaction_service import LotTransactionService
from stock_analysis.trading.config import DEFAULT_TRADING_CONFIG


class TestEdgeCasesLotTracking(unittest.TestCase):
    """边缘情况批次追踪测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        self.storage = create_storage('sqlite', db_path=self.temp_db.name)
        self.storage.ensure_stock_exists('AAPL')
        
        self.service = LotTransactionService(self.storage, DEFAULT_TRADING_CONFIG)
    
    def tearDown(self):
        """清理测试环境"""
        self.storage.close()
        os.unlink(self.temp_db.name)
    
    def test_fractional_shares_precision(self):
        """测试小数股份的精度处理"""
        print("\n=== 小数股份精度测试 ===")
        
        # 买入小数股份
        tx1 = self.service.record_buy_transaction(
            symbol='AAPL',
            quantity=10.3333,  # 精确到4位小数
            price=150.4567,    # 精确到4位小数
            transaction_date='2024-01-15',
            external_id='frac_buy_001',
            notes='小数股份买入'
        )
        
        print(f"买入: {tx1.quantity}股 @ ${tx1.price}")
        
        # 卖出部分小数股份
        sell1 = self.service.record_sell_transaction(
            symbol='AAPL',
            quantity=3.1415,  # π 的近似值
            price=155.7890,
            transaction_date='2024-01-20',
            external_id='frac_sell_001',
            notes='小数股份卖出',
            cost_basis_method='FIFO'
        )
        
        print(f"卖出: {sell1.quantity}股 @ ${sell1.price}")
        
        # 验证剩余股份
        lots = self.service.get_position_lots('AAPL')
        remaining = lots[0].remaining_quantity
        expected_remaining = Decimal('10.3333') - Decimal('3.1415')
        
        print(f"剩余股份: {remaining}")
        print(f"预期剩余: {expected_remaining}")
        
        # 验证精度保持
        self.assertAlmostEqual(float(remaining), float(expected_remaining), places=4,
                              msg="小数股份计算应保持精度")
        
        # 验证可以继续卖出剩余股份
        remaining_float = float(remaining)
        sell2 = self.service.record_sell_transaction(
            symbol='AAPL',
            quantity=remaining_float,
            price=160.0000,
            transaction_date='2024-01-25',
            external_id='frac_sell_002',
            notes='清空剩余小数股份',
            cost_basis_method='FIFO'
        )
        
        # 验证批次已完全关闭
        lots_after = self.service.get_position_lots('AAPL')
        self.assertTrue(lots_after[0].is_closed, "批次应该已完全关闭")
        self.assertLessEqual(float(lots_after[0].remaining_quantity), 0.0001, "剩余数量应该接近0")
        
        print("✅ 小数股份精度测试通过")
    
    def test_micro_transactions(self):
        """测试微量交易（1股以下）"""
        print("\n=== 微量交易测试 ===")
        
        # 买入微量股份
        micro_quantities = [0.1, 0.01, 0.001, 0.0001]
        
        for i, qty in enumerate(micro_quantities, 1):
            tx = self.service.record_buy_transaction(
                symbol='AAPL',
                quantity=qty,
                price=150.00 + i,  # 不同价格
                transaction_date=f'2024-01-{i:02d}',
                external_id=f'micro_buy_{i:03d}',
                notes=f'微量买入{qty}股'
            )
            print(f"微量买入 {i}: {qty}股 @ ${tx.price}")
        
        # 验证所有微量批次都被创建
        lots = self.service.get_position_lots('AAPL')
        self.assertEqual(len(lots), len(micro_quantities), "应该创建对应数量的批次")
        
        # 计算总持仓
        total_shares = sum(lot.remaining_quantity for lot in lots)
        expected_total = sum(Decimal(str(qty)) for qty in micro_quantities)
        
        print(f"总持仓: {total_shares}")
        print(f"预期总量: {expected_total}")
        
        self.assertAlmostEqual(float(total_shares), float(expected_total), places=4,
                              msg="微量交易总量应正确")
        
        # 卖出部分微量股份
        sell_qty = 0.05  # 跨越多个批次
        sell_tx = self.service.record_sell_transaction(
            symbol='AAPL',
            quantity=sell_qty,
            price=155.00,
            transaction_date='2024-01-10',
            external_id='micro_sell_001',
            notes='微量卖出',
            cost_basis_method='FIFO'
        )
        
        # 验证卖出分配
        allocations = self.service.get_sale_allocations_by_transaction(sell_tx.id)
        total_allocated = sum(alloc.quantity_sold for alloc in allocations)
        
        print(f"卖出分配到 {len(allocations)} 个批次")
        print(f"总分配数量: {total_allocated}")
        
        self.assertAlmostEqual(float(total_allocated), sell_qty, places=4,
                              msg="微量卖出分配应正确")
        
        print("✅ 微量交易测试通过")
    
    def test_same_day_multiple_transactions(self):
        """测试同一日期的多笔交易"""
        print("\n=== 同日多笔交易测试 ===")
        
        same_date = '2024-01-15'
        
        # 同一天多次买入
        buy_txs = []
        for i in range(5):
            tx = self.service.record_buy_transaction(
                symbol='AAPL',
                quantity=10 + i * 5,  # 10, 15, 20, 25, 30
                price=150.00 + i * 0.50,  # 150.00, 150.50, 151.00, ...
                transaction_date=same_date,
                external_id=f'same_day_buy_{i+1:02d}',
                notes=f'同日买入第{i+1}笔'
            )
            buy_txs.append(tx)
            print(f"同日买入 {i+1}: {tx.quantity}股 @ ${tx.price}")
        
        # 验证创建了5个不同的批次
        lots = self.service.get_position_lots('AAPL')
        self.assertEqual(len(lots), 5, "应该创建5个独立批次")
        
        # 同一天多次卖出
        sell_txs = []
        remaining_total = sum(lot.remaining_quantity for lot in lots)
        
        # 分3次卖出
        sell_quantities = [20, 30, 25]
        for i, qty in enumerate(sell_quantities):
            if remaining_total >= qty:
                tx = self.service.record_sell_transaction(
                    symbol='AAPL',
                    quantity=qty,
                    price=155.00 + i * 0.25,
                    transaction_date=same_date,  # 同一天
                    external_id=f'same_day_sell_{i+1:02d}',
                    notes=f'同日卖出第{i+1}笔',
                    cost_basis_method='FIFO'
                )
                sell_txs.append(tx)
                remaining_total -= qty
                print(f"同日卖出 {i+1}: {qty}股 @ ${tx.price}")
        
        # 验证所有交易都被正确记录
        self.assertEqual(len(sell_txs), 3, "应该记录3笔卖出交易")
        
        # 验证批次状态
        final_lots = self.service.get_position_lots('AAPL')
        final_remaining = sum(lot.remaining_quantity for lot in final_lots if lot.remaining_quantity > 0)
        
        print(f"最终剩余: {final_remaining}股")
        
        # 验证数量平衡
        total_bought = sum(tx.quantity for tx in buy_txs)
        total_sold = sum(tx.quantity for tx in sell_txs)
        expected_remaining = total_bought - total_sold
        
        self.assertAlmostEqual(float(final_remaining), expected_remaining, places=4,
                              msg="同日多笔交易后数量应平衡")
        
        print("✅ 同日多笔交易测试通过")
    
    def test_extreme_prices_and_quantities(self):
        """测试极端价格和数量"""
        print("\n=== 极端价格和数量测试 ===")
        
        # 测试极低价格
        tx1 = self.service.record_buy_transaction(
            symbol='AAPL',
            quantity=1000000,  # 100万股
            price=0.0001,      # 极低价格
            transaction_date='2024-01-01',
            external_id='extreme_low_price',
            notes='极低价格大量买入'
        )
        
        print(f"极低价格买入: {tx1.quantity}股 @ ${tx1.price}")
        
        # 测试极高价格
        tx2 = self.service.record_buy_transaction(
            symbol='AAPL',
            quantity=0.0001,   # 极少数量
            price=99999.9999,  # 极高价格
            transaction_date='2024-01-02',
            external_id='extreme_high_price',
            notes='极高价格少量买入'
        )
        
        print(f"极高价格买入: {tx2.quantity}股 @ ${tx2.price}")
        
        # 验证批次创建
        lots = self.service.get_position_lots('AAPL')
        self.assertEqual(len(lots), 2, "应该创建2个批次")
        
        # 测试极端价格的卖出
        sell1 = self.service.record_sell_transaction(
            symbol='AAPL',
            quantity=500000,  # 卖出一半
            price=10000.0,    # 高价卖出
            transaction_date='2024-01-10',
            external_id='extreme_sell_001',
            notes='极端价格卖出',
            cost_basis_method='FIFO'
        )
        
        # 计算盈亏
        allocations = self.service.get_sale_allocations_by_transaction(sell1.id)
        total_pnl = sum(alloc.realized_pnl for alloc in allocations)
        
        print(f"极端价格交易盈亏: ${total_pnl:.4f}")
        
        # 验证盈亏计算合理（应该是巨大的盈利）
        self.assertGreater(total_pnl, 0, "极低成本高价卖出应该盈利")
        self.assertGreater(total_pnl, 1000000, "盈利应该很大")
        
        print("✅ 极端价格和数量测试通过")
    
    def test_lot_depletion_edge_cases(self):
        """测试批次耗尽的边缘情况"""
        print("\n=== 批次耗尽边缘情况测试 ===")
        
        # 创建小批次
        tx1 = self.service.record_buy_transaction(
            symbol='AAPL',
            quantity=10.0,
            price=150.00,
            transaction_date='2024-01-01',
            external_id='depletion_buy_001',
            notes='小批次买入'
        )
        
        # 几乎全部卖出（留下微量）
        sell1 = self.service.record_sell_transaction(
            symbol='AAPL',
            quantity=9.9999,  # 留下0.0001股
            price=155.00,
            transaction_date='2024-01-10',
            external_id='depletion_sell_001',
            notes='几乎全部卖出',
            cost_basis_method='FIFO'
        )
        
        # 验证批次状态
        lots = self.service.get_position_lots('AAPL')
        remaining = lots[0].remaining_quantity
        
        print(f"几乎全部卖出后剩余: {remaining}")
        
        # 批次应该还是活跃的（因为还有微量剩余）
        self.assertFalse(lots[0].is_closed, "微量剩余批次应该仍然活跃")
        self.assertGreater(remaining, 0, "应该还有剩余")
        
        # 卖出剩余微量
        remaining_float = float(remaining)
        sell2 = self.service.record_sell_transaction(
            symbol='AAPL',
            quantity=remaining_float,
            price=160.00,
            transaction_date='2024-01-15',
            external_id='depletion_sell_002',
            notes='清空微量剩余',
            cost_basis_method='FIFO'
        )
        
        # 验证批次完全关闭
        lots_after = self.service.get_position_lots('AAPL')
        self.assertTrue(lots_after[0].is_closed, "批次应该完全关闭")
        self.assertLessEqual(float(lots_after[0].remaining_quantity), 0.0001, "剩余应该接近0")
        
        print("✅ 批次耗尽边缘情况测试通过")
    
    def test_concurrent_lot_matching(self):
        """测试复杂的批次匹配场景"""
        print("\n=== 复杂批次匹配测试 ===")
        
        # 创建多个不同大小的批次
        batch_data = [
            (100, 150.00),
            (50, 155.00),
            (200, 148.00),
            (25, 162.00),
            (150, 151.50),
        ]
        
        for i, (qty, price) in enumerate(batch_data, 1):
            self.service.record_buy_transaction(
                symbol='AAPL',
                quantity=qty,
                price=price,
                transaction_date=f'2024-01-{i:02d}',
                external_id=f'complex_buy_{i:03d}',
                notes=f'批次{i}买入'
            )
        
        # 卖出数量正好跨越多个批次
        total_available = sum(qty for qty, _ in batch_data)
        sell_qty = 275  # 跨越前3个批次的部分
        
        sell_tx = self.service.record_sell_transaction(
            symbol='AAPL',
            quantity=sell_qty,
            price=158.00,
            transaction_date='2024-01-10',
            external_id='complex_sell_001',
            notes='复杂跨批次卖出',
            cost_basis_method='FIFO'
        )
        
        # 验证分配
        allocations = self.service.get_sale_allocations_by_transaction(sell_tx.id)
        total_allocated = sum(alloc.quantity_sold for alloc in allocations)
        
        print(f"卖出 {sell_qty} 股，分配到 {len(allocations)} 个批次")
        print(f"总分配数量: {total_allocated}")
        
        # 验证分配正确
        self.assertEqual(float(total_allocated), sell_qty, "分配数量应该正确")
        
        # 验证FIFO顺序
        expected_allocations = [
            (100, 150.00),  # 第1批次全部
            (50, 155.00),   # 第2批次全部
            (125, 148.00),  # 第3批次部分
        ]
        
        for i, (expected_qty, expected_price) in enumerate(expected_allocations):
            alloc = allocations[i]
            self.assertAlmostEqual(float(alloc.quantity_sold), expected_qty, places=4)
            self.assertAlmostEqual(float(alloc.cost_basis), expected_price, places=2)
        
        # 验证剩余批次状态
        lots = self.service.get_position_lots('AAPL')
        
        # 前两个批次应该关闭
        self.assertTrue(lots[0].is_closed, "第1批次应该关闭")
        self.assertTrue(lots[1].is_closed, "第2批次应该关闭")
        
        # 第3批次应该部分剩余
        self.assertFalse(lots[2].is_closed, "第3批次应该仍然活跃")
        self.assertAlmostEqual(float(lots[2].remaining_quantity), 75.0, places=4)
        
        # 后面批次应该完全保留
        self.assertFalse(lots[3].is_closed, "第4批次应该完全保留")
        self.assertFalse(lots[4].is_closed, "第5批次应该完全保留")
        
        print("✅ 复杂批次匹配测试通过")
    
    def test_data_consistency_validation(self):
        """测试数据一致性验证"""
        print("\n=== 数据一致性验证测试 ===")
        
        # 创建一系列交易
        buy_data = [
            (100, 150.00, '2024-01-01'),
            (50, 155.00, '2024-01-05'),
            (75, 148.00, '2024-01-10'),
        ]
        
        for i, (qty, price, date) in enumerate(buy_data, 1):
            self.service.record_buy_transaction(
                symbol='AAPL',
                quantity=qty,
                price=price,
                transaction_date=date,
                external_id=f'consistency_buy_{i:03d}',
                notes=f'一致性测试买入{i}'
            )
        
        # 执行一些卖出交易
        sell_data = [
            (60, 160.00, '2024-01-15'),
            (40, 158.00, '2024-01-20'),
        ]
        
        for i, (qty, price, date) in enumerate(sell_data, 1):
            self.service.record_sell_transaction(
                symbol='AAPL',
                quantity=qty,
                price=price,
                transaction_date=date,
                external_id=f'consistency_sell_{i:03d}',
                notes=f'一致性测试卖出{i}',
                cost_basis_method='FIFO'
            )
        
        # 验证数据一致性
        result = self.service.validate_data_consistency()
        
        print(f"一致性检查结果: {result['is_consistent']}")
        print(f"检查股票数: {result['symbols_checked']}")
        print(f"发现问题: {result['issues_found']}")
        
        if result['issues']:
            for issue in result['issues']:
                print(f"  问题: {issue['description']}")
        
        # 在正常情况下应该是一致的
        self.assertTrue(result['is_consistent'], "数据应该是一致的")
        self.assertEqual(result['issues_found'], 0, "不应该有数据问题")
        
        # 验证统计信息
        if 'AAPL' in result['statistics']:
            stats = result['statistics']['AAPL']
            print(f"AAPL统计: 买入{stats['buy_transactions']}笔, 卖出{stats['sell_transactions']}笔")
            print(f"持仓批次{stats['position_lots']}个, 活跃{stats['active_lots']}个")
            
            # 验证统计正确性
            self.assertEqual(stats['buy_transactions'], 3, "应该有3笔买入")
            self.assertEqual(stats['sell_transactions'], 2, "应该有2笔卖出")
            self.assertGreater(stats['active_lots'], 0, "应该有活跃批次")
        
        print("✅ 数据一致性验证测试通过")


if __name__ == '__main__':
    unittest.main(verbosity=2)
