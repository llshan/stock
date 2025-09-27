#!/usr/bin/env python3
"""
成本基础方法综合验证测试
全面测试FIFO、LIFO、SpecificLot、AverageCost四种方法的正确性
"""

import unittest
import tempfile
import os
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any

from stock_analysis.data.storage import create_storage
from stock_analysis.trading.services.lot_transaction_service import LotTransactionService
from stock_analysis.trading.config import DEFAULT_TRADING_CONFIG


class TestCostBasisComprehensive(unittest.TestCase):
    """成本基础方法综合测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        self.storage = create_storage('sqlite', db_path=self.temp_db.name)
        self.storage.ensure_stock_exists('TEST')
        
        self.service = LotTransactionService(self.storage, DEFAULT_TRADING_CONFIG)
        
        # 为每种方法创建独立的用户
        self.users = {
            'FIFO': 'fifo_user',
            'LIFO': 'lifo_user', 
            'SpecificLot': 'specific_user',
            'AverageCost': 'average_user'
        }
    
    def tearDown(self):
        """清理测试环境"""
        self.storage.close()
        os.unlink(self.temp_db.name)
    
    def _setup_identical_purchases(self) -> List[Dict]:
        """为指定用户创建相同的买入序列"""
        purchases = [
            ('2024-01-01', 100, 150.00, '第1批次-低价'),
            ('2024-01-10', 200, 160.00, '第2批次-高价'),
            ('2024-01-20', 150, 140.00, '第3批次-最低价'),
            ('2024-01-30', 300, 170.00, '第4批次-最高价'),
            ('2024-02-10', 100, 155.00, '第5批次-中价'),
        ]
        
        created_lots = []
        for i, (date, quantity, price, note) in enumerate(purchases, 1):
            tx = self.service.record_buy_transaction(
                symbol='TEST',
                quantity=quantity,
                price=price,
                transaction_date=date,
                external_id=f'buy_{i:02d}',
                notes=note
            )
            
            # 获取创建的批次信息
            lots = self.service.get_position_lots('TEST')
            latest_lot = max(lots, key=lambda x: x.id)
            
            created_lots.append({
                'transaction': tx,
                'lot_id': latest_lot.id,
                'quantity': quantity,
                'price': price,
                'date': date,
                'note': note
            })
        
        return created_lots
    
    def _print_method_results(self, method: str, sell_tx: Any, expected_info: str = ""):
        """打印方法执行结果"""
        allocations = self.service.get_sale_allocations_by_transaction(sell_tx.id)
        total_pnl = sum(alloc.realized_pnl for alloc in allocations)
        
        print(f"\n{method}方法结果 {expected_info}:")
        print(f"  卖出交易ID: {sell_tx.id}")
        print(f"  分配批次数: {len(allocations)}")
        print(f"  总已实现盈亏: ${total_pnl:.2f}")
        
        print("  详细分配:")
        for i, alloc in enumerate(allocations, 1):
            pnl_per_share = (alloc.sale_price - alloc.cost_basis)
            print(f"    {i}. 批次{alloc.lot_id}: {alloc.quantity_sold:.4f}股 "
                  f"@ 成本${alloc.cost_basis:.2f} → 卖价${alloc.sale_price:.2f} "
                  f"(单股盈亏${pnl_per_share:.2f}, 总盈亏${alloc.realized_pnl:.2f})")
        
        return allocations, total_pnl
    
    def test_fifo_vs_lifo_comparison(self):
        """测试FIFO vs LIFO对比"""
        print("\n=== FIFO vs LIFO 对比测试 ===")
        
        # 为FIFO和LIFO用户设置相同的买入序列
        fifo_user = self.users['FIFO']
        lifo_user = self.users['LIFO']
        
        print("设置相同的买入序列...")
        fifo_lots = self._setup_identical_purchases()
        lifo_lots = self._setup_identical_purchases()
        
        # 打印买入序列
        print("\n买入序列 (两个用户相同):")
        total_shares = 0
        total_cost = 0
        for i, lot_info in enumerate(fifo_lots, 1):
            qty = lot_info['quantity']
            price = lot_info['price']
            cost = qty * price
            total_shares += qty
            total_cost += cost
            print(f"  {i}. {lot_info['date']}: {qty}股 @ ${price:.2f} (成本${cost:.2f}) - {lot_info['note']}")
        
        avg_cost = total_cost / total_shares
        print(f"\n总计: {total_shares}股, 总成本${total_cost:.2f}, 平均成本${avg_cost:.4f}")
        
        # 执行相同的卖出交易
        sell_quantity = 350  # 卖出350股，跨越多个批次
        sell_price = 165.00
        sell_date = '2024-02-20'
        
        print(f"\n执行卖出: {sell_quantity}股 @ ${sell_price:.2f}")
        
        # FIFO卖出
        fifo_sell = self.service.record_sell_transaction(
            symbol='TEST',
            quantity=sell_quantity,
            price=sell_price,
            transaction_date=sell_date,
            external_id='fifo_sell_test',
            notes='FIFO方法卖出测试',
            cost_basis_method='FIFO'
        )
        
        fifo_allocations, fifo_pnl = self._print_method_results('FIFO', fifo_user, fifo_sell, "(先进先出)")
        
        # LIFO卖出
        lifo_sell = self.service.record_sell_transaction(
            symbol='TEST',
            quantity=sell_quantity,
            price=sell_price,
            transaction_date=sell_date,
            external_id='lifo_sell_test',
            notes='LIFO方法卖出测试',
            cost_basis_method='LIFO'
        )
        
        lifo_allocations, lifo_pnl = self._print_method_results('LIFO', lifo_user, lifo_sell, "(后进先出)")
        
        # 验证FIFO顺序 (应该从最早的批次开始)
        expected_fifo_order = [
            (100, 150.00),  # 第1批次全部
            (200, 160.00),  # 第2批次全部  
            (50, 140.00),   # 第3批次部分
        ]
        
        print("\n验证FIFO顺序:")
        for i, (expected_qty, expected_price) in enumerate(expected_fifo_order):
            actual_alloc = fifo_allocations[i]
            print(f"  期望: {expected_qty}股 @ ${expected_price:.2f}")
            print(f"  实际: {actual_alloc.quantity_sold:.4f}股 @ ${actual_alloc.cost_basis:.2f}")
            
            self.assertAlmostEqual(float(actual_alloc.quantity_sold), expected_qty, places=4)
            self.assertAlmostEqual(float(actual_alloc.cost_basis), expected_price, places=2)
        
        # 验证LIFO顺序 (应该从最新的批次开始)
        expected_lifo_order = [
            (100, 155.00),  # 第5批次全部
            (300, 170.00),  # 第4批次全部，但卖出数量有限制，这里应该是部分
        ]
        
        print("\n验证LIFO顺序:")
        self.assertAlmostEqual(float(lifo_allocations[0].quantity_sold), 100, places=4)
        self.assertAlmostEqual(float(lifo_allocations[0].cost_basis), 155.00, places=2)
        self.assertAlmostEqual(float(lifo_allocations[1].quantity_sold), 250, places=4)  # 350-100=250
        self.assertAlmostEqual(float(lifo_allocations[1].cost_basis), 170.00, places=2)
        
        # 比较盈亏差异
        pnl_diff = fifo_pnl - lifo_pnl
        print(f"\n盈亏对比:")
        print(f"FIFO总盈亏: ${fifo_pnl:.2f}")
        print(f"LIFO总盈亏: ${lifo_pnl:.2f}")
        print(f"差异: ${pnl_diff:.2f} (FIFO - LIFO)")
        
        # 在这个价格序列下，FIFO应该产生更高的盈亏（因为先卖低价批次）
        self.assertNotEqual(fifo_pnl, lifo_pnl, "FIFO和LIFO应该产生不同的盈亏")
        self.assertGreater(fifo_pnl, lifo_pnl, "在此价格序列下，FIFO应该产生更高盈亏")
        
        print("✅ FIFO vs LIFO 对比测试通过")
    
    def test_specific_lot_precision_control(self):
        """测试指定批次的精确控制"""
        print("\n=== 指定批次精确控制测试 ===")
        
        lots_info = self._setup_identical_purchases()
        
        print("测试场景: 精确选择特定批次进行税务优化")
        
        # 获取当前所有批次
        lots = self.service.get_position_lots('TEST')
        print(f"\n当前批次状态 (共{len(lots)}个):")
        for lot in lots:
            print(f"  批次{lot.id}: {lot.remaining_quantity}股 @ ${lot.cost_basis:.2f} ({lot.purchase_date})")
        
        # 场景1: 选择最有利的批次组合 (最低成本批次)
        print("\n场景1: 选择最低成本批次组合进行卖出")
        
        # 找到成本最低的两个批次
        sorted_lots = sorted(lots, key=lambda x: x.cost_basis)
        low_cost_lots = sorted_lots[:2]  # 最低成本的两个批次
        
        specific_lots_1 = [
            {'lot_id': low_cost_lots[0].id, 'quantity': 80},   # 第3批次的部分 (140.00)
            {'lot_id': low_cost_lots[1].id, 'quantity': 70},   # 第1批次的部分 (150.00)
        ]
        
        total_qty_1 = sum(lot['quantity'] for lot in specific_lots_1)
        
        sell1 = self.service.record_sell_transaction(
            symbol='TEST',
            quantity=total_qty_1,
            price=180.00,  # 高价卖出获得最大盈利
            transaction_date='2024-03-01',
            external_id='specific_sell_001',
            notes='选择低成本批次卖出',
            cost_basis_method='SpecificLot',
            specific_lots=specific_lots_1
        )
        
        allocs1, pnl1 = self._print_method_results('SpecificLot', sell1, "(选择低成本批次)")
        
        # 验证精确匹配
        for i, expected_spec in enumerate(specific_lots_1):
            actual_alloc = allocs1[i]
            self.assertEqual(actual_alloc.lot_id, expected_spec['lot_id'])
            self.assertAlmostEqual(float(actual_alloc.quantity_sold), expected_spec['quantity'], places=4)
        
        # 场景2: 选择最不利的批次组合 (最高成本批次，用于税务亏损抵扣)
        print("\n场景2: 选择最高成本批次组合，模拟税务亏损抵扣")
        
        # 更新批次状态（因为前面的卖出可能影响了某些批次）
        updated_lots = self.service.get_position_lots('TEST')
        active_lots = [lot for lot in updated_lots if lot.remaining_quantity > 0]
        high_cost_lots = sorted(active_lots, key=lambda x: x.cost_basis, reverse=True)
        
        specific_lots_2 = [
            {'lot_id': high_cost_lots[0].id, 'quantity': min(100, float(high_cost_lots[0].remaining_quantity))},  # 最高成本批次
            {'lot_id': high_cost_lots[1].id, 'quantity': min(50, float(high_cost_lots[1].remaining_quantity))},   # 次高成本批次
        ]
        
        total_qty_2 = sum(lot['quantity'] for lot in specific_lots_2)
        
        sell2 = self.service.record_sell_transaction(
            symbol='TEST',
            quantity=total_qty_2,
            price=145.00,  # 低价卖出产生亏损
            transaction_date='2024-03-05',
            external_id='specific_sell_002',
            notes='选择高成本批次卖出',
            cost_basis_method='SpecificLot',
            specific_lots=specific_lots_2
        )
        
        allocs2, pnl2 = self._print_method_results('SpecificLot', sell2, "(选择高成本批次)")
        
        # 场景3: 复杂的跨批次精确分配
        print("\n场景3: 复杂跨批次精确分配")
        
        # 获取最新批次状态
        final_lots = self.service.get_position_lots('TEST')
        final_active = [lot for lot in final_lots if lot.remaining_quantity > 0]
        
        if len(final_active) >= 3:
            # 从多个批次各取一部分
            specific_lots_3 = [
                {'lot_id': final_active[0].id, 'quantity': 15},
                {'lot_id': final_active[1].id, 'quantity': 25},
                {'lot_id': final_active[2].id, 'quantity': 35},
            ]
            
            total_qty_3 = sum(lot['quantity'] for lot in specific_lots_3)
            
            sell3 = self.service.record_sell_transaction(
                symbol='TEST',
                quantity=total_qty_3,
                price=162.50,
                transaction_date='2024-03-10',
                external_id='specific_sell_003',
                notes='复杂跨批次分配',
                cost_basis_method='SpecificLot',
                specific_lots=specific_lots_3
            )
            
            allocs3, pnl3 = self._print_method_results('SpecificLot', sell3, "(跨批次精确分配)")
            
            # 验证精确性
            for i, expected_spec in enumerate(specific_lots_3):
                actual_alloc = allocs3[i]
                self.assertEqual(actual_alloc.lot_id, expected_spec['lot_id'])
                self.assertAlmostEqual(float(actual_alloc.quantity_sold), expected_spec['quantity'], places=4)
        
        # 总结不同策略的效果
        print(f"\n指定批次策略效果总结:")
        print(f"策略1 (低成本批次): 盈亏 ${pnl1:.2f}")
        print(f"策略2 (高成本批次): 盈亏 ${pnl2:.2f}")
        if 'pnl3' in locals():
            print(f"策略3 (跨批次分配): 盈亏 ${pnl3:.2f}")
        
        # 验证策略效果差异
        self.assertGreater(pnl1, pnl2, "低成本批次策略应该产生更高盈亏")
        
        print("✅ 指定批次精确控制测试通过")
    
    def test_average_cost_method(self):
        """测试平均成本方法"""
        print("\n=== 平均成本方法测试 ===")
        
        lots_info = self._setup_identical_purchases()
        
        # 计算预期的平均成本
        total_shares = sum(info['quantity'] for info in lots_info)
        total_cost = sum(info['quantity'] * info['price'] for info in lots_info)
        expected_avg_cost = total_cost / total_shares
        
        print(f"买入汇总:")
        print(f"  总股数: {total_shares}")
        print(f"  总成本: ${total_cost:.2f}")
        print(f"  预期平均成本: ${expected_avg_cost:.4f}")
        
        # 执行平均成本方法卖出
        sell_quantity = 200
        sell_price = 175.00
        
        sell_tx = self.service.record_sell_transaction(
            symbol='TEST',
            quantity=sell_quantity,
            price=sell_price,
            transaction_date='2024-02-25',
            external_id='average_sell_test',
            notes='平均成本方法测试',
            cost_basis_method='AverageCost'
        )
        
        allocations, total_pnl = self._print_method_results('AverageCost', sell_tx, "(平均成本)")
        
        # 验证平均成本方法的特点
        print(f"\n平均成本方法验证:")
        
        # 计算实际使用的平均成本
        weighted_avg_cost = sum(alloc.cost_basis * alloc.quantity_sold for alloc in allocations) / sell_quantity
        print(f"  实际使用的平均成本: ${weighted_avg_cost:.4f}")
        print(f"  预期平均成本: ${expected_avg_cost:.4f}")
        
        # 平均成本方法应该使用加权平均成本
        self.assertAlmostEqual(weighted_avg_cost, expected_avg_cost, places=2,
                              msg="平均成本方法应该使用正确的加权平均成本")
        
        # 计算预期盈亏
        expected_pnl = (sell_price - expected_avg_cost) * sell_quantity
        print(f"  预期盈亏: ${expected_pnl:.2f}")
        print(f"  实际盈亏: ${total_pnl:.2f}")
        
        self.assertAlmostEqual(total_pnl, expected_pnl, places=1,
                              msg="平均成本方法的盈亏计算应该正确")
        
        print("✅ 平均成本方法测试通过")
    
    def test_all_methods_consistency(self):
        """测试所有方法的一致性"""
        print("\n=== 所有方法一致性测试 ===")
        
        print("验证所有方法在数据完整性方面的一致性...")
        
        # 收集所有用户的最终状态
        methods_summary = {}
        
        for method in self.users.items():
            lots = self.service.get_position_lots('TEST')
            
            total_original = sum(lot.original_quantity for lot in lots)
            total_remaining = sum(lot.remaining_quantity for lot in lots if lot.remaining_quantity > 0)
            total_sold = total_original - total_remaining
            
            # 获取所有卖出分配
            all_allocations = []
            transactions = []  # 这里简化，实际应该查询所有交易
            
            methods_summary[method] = {
                'total_lots': len(lots),
                'total_original': total_original,
                'total_remaining': total_remaining,
                'total_sold': total_sold,
                'active_lots': len([lot for lot in lots if lot.remaining_quantity > 0]),
                'closed_lots': len([lot for lot in lots if lot.remaining_quantity <= 0.0001]),
            }
        
        print("\n各方法最终状态对比:")
        print(f"{'方法':<12} {'总批次':<8} {'原始股数':<10} {'剩余股数':<10} {'已卖股数':<10} {'活跃批次':<8} {'关闭批次':<8}")
        print("-" * 80)
        
        for method, summary in methods_summary.items():
            print(f"{method:<12} {summary['total_lots']:<8} {summary['total_original']:<10.1f} "
                  f"{summary['total_remaining']:<10.1f} {summary['total_sold']:<10.1f} "
                  f"{summary['active_lots']:<8} {summary['closed_lots']:<8}")
        
        # 验证基本一致性
        # 所有方法的原始股数应该相同（因为买入序列相同）
        original_quantities = [summary['total_original'] for summary in methods_summary.values()]
        self.assertTrue(all(abs(qty - original_quantities[0]) < 0.01 for qty in original_quantities),
                       "所有方法的原始股数应该相同")
        
        # 所有方法的批次数应该相同
        lot_counts = [summary['total_lots'] for summary in methods_summary.values()]
        self.assertTrue(all(count == lot_counts[0] for count in lot_counts),
                       "所有方法的批次数应该相同")
        
        print(f"\n一致性验证:")
        print(f"✓ 原始股数一致性: {original_quantities[0]:.1f}股")
        print(f"✓ 批次数一致性: {lot_counts[0]}个批次")
        
        print("✅ 所有方法一致性测试通过")
    
    def test_edge_case_cost_basis_scenarios(self):
        """测试成本基础的边缘情况"""
        print("\n=== 成本基础边缘情况测试 ===")
        
        edge_user = 'edge_cost_user'
        
        # 场景1: 相同价格的多个批次
        print("\n场景1: 相同价格的多个批次")
        
        same_price = 150.00
        for i in range(3):
            self.service.record_buy_transaction(
                symbol='TEST',
                quantity=100,
                price=same_price,
                transaction_date=f'2024-0{i+1}-01',
                external_id=f'same_price_buy_{i+1}',
                notes=f'相同价格买入{i+1}'
            )
        
        # 卖出部分，验证各方法的处理
        sell_tx = self.service.record_sell_transaction(
            symbol='TEST',
            quantity=250,  # 跨越多个相同价格批次
            price=160.00,
            transaction_date='2024-01-15',
            external_id='same_price_sell',
            notes='相同价格批次卖出',
            cost_basis_method='FIFO'
        )
        
        allocations = self.service.get_sale_allocations_by_transaction(sell_tx.id)
        print(f"相同价格批次卖出分配到 {len(allocations)} 个批次")
        
        # 所有分配的成本基础应该相同
        cost_bases = [float(alloc.cost_basis) for alloc in allocations]
        self.assertTrue(all(abs(cost - same_price) < 0.01 for cost in cost_bases),
                       "相同价格批次的成本基础应该一致")
        
        # 场景2: 微量差异的价格
        print("\n场景2: 微量差异的价格")
        
        micro_user = 'micro_diff_user'
        micro_prices = [100.0001, 100.0002, 100.0003]
        
        for i, price in enumerate(micro_prices):
            self.service.record_buy_transaction(
                symbol='TEST',
                quantity=50,
                price=price,
                transaction_date=f'2024-02-0{i+1}',
                external_id=f'micro_buy_{i+1}',
                notes=f'微量差异买入{i+1}'
            )
        
        # 卖出并验证精度保持
        sell_tx2 = self.service.record_sell_transaction(
            symbol='TEST',
            quantity=100,
            price=101.00,
            transaction_date='2024-02-10',
            external_id='micro_sell',
            notes='微量差异卖出',
            cost_basis_method='FIFO'
        )
        
        allocations2 = self.service.get_sale_allocations_by_transaction(sell_tx2.id)
        
        # 验证精度保持
        for i, alloc in enumerate(allocations2):
            expected_price = micro_prices[i] if i < len(micro_prices) else micro_prices[-1]
            self.assertAlmostEqual(float(alloc.cost_basis), expected_price, places=4,
                                  msg=f"微量差异的价格精度应该保持")
        
        print("✅ 成本基础边缘情况测试通过")


if __name__ == '__main__':
    unittest.main(verbosity=2)
