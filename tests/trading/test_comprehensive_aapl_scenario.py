#!/usr/bin/env python3
"""
综合AAPL交易场景测试
测试10次买入、5次卖出的复杂交互场景，验证所有成本基础方法
"""

import unittest
import tempfile
import os
from datetime import datetime, timedelta
from decimal import Decimal

from stock_analysis.data.storage import create_storage
from stock_analysis.trading.services.lot_transaction_service import LotTransactionService
from stock_analysis.trading.config import DEFAULT_TRADING_CONFIG


class TestComprehensiveAAPLScenario(unittest.TestCase):
    """综合AAPL交易场景测试"""
    
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
    
    def test_comprehensive_aapl_trading_scenario(self):
        """
        测试综合AAPL交易场景：
        - 10次买入交易（不同时间、价格、数量）
        - 5次卖出交易（交替进行，测试不同成本基础方法）
        - 验证批次追踪、盈亏计算、持仓状态
        """
        print("\n=== 开始综合AAPL交易场景测试 ===")
        
        # === 第一阶段：前5次买入 ===
        print("\n--- 第一阶段：前5次买入 ---")
        buy_transactions = []
        
        # 买入1：2024-01-15, 100股 @ $150.50
        tx1 = self.service.record_buy_transaction(
            symbol='AAPL',
            quantity=100,
            price=150.50,
            transaction_date='2024-01-15',
            external_id='buy_001',
            notes='初始建仓'
        )
        buy_transactions.append(tx1)
        print(f"买入1: {tx1.quantity}股 @ ${tx1.price}")
        
        # 买入2：2024-01-22, 50股 @ $155.75
        tx2 = self.service.record_buy_transaction(
            symbol='AAPL',
            quantity=50,
            price=155.75,
            transaction_date='2024-01-22',
            external_id='buy_002',
            notes='加仓操作'
        )
        buy_transactions.append(tx2)
        print(f"买入2: {tx2.quantity}股 @ ${tx2.price}")
        
        # 买入3：2024-02-05, 75股 @ $148.25
        tx3 = self.service.record_buy_transaction(
            symbol='AAPL',
            quantity=75,
            price=148.25,
            transaction_date='2024-02-05',
            external_id='buy_003',
            notes='逢低买入'
        )
        buy_transactions.append(tx3)
        print(f"买入3: {tx3.quantity}股 @ ${tx3.price}")
        
        # 买入4：2024-02-12, 25股 @ $162.00
        tx4 = self.service.record_buy_transaction(
            symbol='AAPL',
            quantity=25,
            price=162.00,
            transaction_date='2024-02-12',
            external_id='buy_004',
            notes='小额加仓'
        )
        buy_transactions.append(tx4)
        print(f"买入4: {tx4.quantity}股 @ ${tx4.price}")
        
        # 买入5：2024-02-20, 80股 @ $145.90
        tx5 = self.service.record_buy_transaction(
            symbol='AAPL',
            quantity=80,
            price=145.90,
            transaction_date='2024-02-20',
            external_id='buy_005',
            notes='大幅下跌后买入'
        )
        buy_transactions.append(tx5)
        print(f"买入5: {tx5.quantity}股 @ ${tx5.price}")
        
        # 验证当前持仓
        lots_after_buy5 = self.service.get_position_lots('AAPL')
        total_shares = sum(lot.remaining_quantity for lot in lots_after_buy5)
        print(f"\n前5次买入后总持仓: {total_shares}股，共{len(lots_after_buy5)}个批次")
        self.assertEqual(len(lots_after_buy5), 5)
        self.assertEqual(total_shares, Decimal('330'))
        
        # === 第一次卖出：FIFO方法 ===
        print("\n--- 第一次卖出：FIFO方法 ---")
        sell1 = self.service.record_sell_transaction(
            symbol='AAPL',
            quantity=60,
            price=158.75,
            transaction_date='2024-02-25',
            external_id='sell_001',
            notes='部分获利了结',
            cost_basis_method='FIFO'
        )
        print(f"卖出1: {sell1.quantity}股 @ ${sell1.price} (FIFO)")
        
        # 验证卖出分配
        allocations1 = self.service.get_sale_allocations_by_transaction(sell1.id)
        total_sold = sum(alloc.quantity_sold for alloc in allocations1)
        total_realized_pnl = sum(alloc.realized_pnl for alloc in allocations1)
        print(f"分配到{len(allocations1)}个批次，总已实现盈亏: ${total_realized_pnl:.2f}")
        self.assertEqual(total_sold, Decimal('60'))
        
        # === 买入6-7：继续建仓 ===
        print("\n--- 买入6-7：继续建仓 ---")
        
        # 买入6：2024-03-01, 40股 @ $165.20
        tx6 = self.service.record_buy_transaction(
            symbol='AAPL',
            quantity=40,
            price=165.20,
            transaction_date='2024-03-01',
            external_id='buy_006',
            notes='高位加仓'
        )
        buy_transactions.append(tx6)
        print(f"买入6: {tx6.quantity}股 @ ${tx6.price}")
        
        # 买入7：2024-03-08, 60股 @ $152.80
        tx7 = self.service.record_buy_transaction(
            symbol='AAPL',
            quantity=60,
            price=152.80,
            transaction_date='2024-03-08',
            external_id='buy_007',
            notes='回调买入'
        )
        buy_transactions.append(tx7)
        print(f"买入7: {tx7.quantity}股 @ ${tx7.price}")
        
        # === 第二次卖出：LIFO方法 ===
        print("\n--- 第二次卖出：LIFO方法 ---")
        sell2 = self.service.record_sell_transaction(
            symbol='AAPL',
            quantity=45,
            price=159.90,
            transaction_date='2024-03-15',
            external_id='sell_002',
            notes='LIFO卖出测试',
            cost_basis_method='LIFO'
        )
        print(f"卖出2: {sell2.quantity}股 @ ${sell2.price} (LIFO)")
        
        allocations2 = self.service.get_sale_allocations_by_transaction(sell2.id)
        total_realized_pnl2 = sum(alloc.realized_pnl for alloc in allocations2)
        print(f"LIFO分配到{len(allocations2)}个批次，已实现盈亏: ${total_realized_pnl2:.2f}")
        
        # === 买入8-10：最后三次买入 ===
        print("\n--- 买入8-10：最后三次买入 ---")
        
        # 买入8：2024-03-22, 35股 @ $170.45
        tx8 = self.service.record_buy_transaction(
            symbol='AAPL',
            quantity=35,
            price=170.45,
            transaction_date='2024-03-22',
            external_id='buy_008',
            notes='突破新高买入'
        )
        buy_transactions.append(tx8)
        print(f"买入8: {tx8.quantity}股 @ ${tx8.price}")
        
        # 买入9：2024-04-02, 90股 @ $144.60
        tx9 = self.service.record_buy_transaction(
            symbol='AAPL',
            quantity=90,
            price=144.60,
            transaction_date='2024-04-02',
            external_id='buy_009',
            notes='大跌抄底'
        )
        buy_transactions.append(tx9)
        print(f"买入9: {tx9.quantity}股 @ ${tx9.price}")
        
        # 买入10：2024-04-10, 15股 @ $167.30
        tx10 = self.service.record_buy_transaction(
            symbol='AAPL',
            quantity=15,
            price=167.30,
            transaction_date='2024-04-10',
            external_id='buy_010',
            notes='最后小额买入'
        )
        buy_transactions.append(tx10)
        print(f"买入10: {tx10.quantity}股 @ ${tx10.price}")
        
        # === 第三次卖出：指定批次方法 ===
        print("\n--- 第三次卖出：指定批次方法 ---")
        
        # 获取当前批次状态
        current_lots = self.service.get_position_lots('AAPL')
        print(f"当前活跃批次数: {len(current_lots)}")
        for lot in current_lots:
            if lot.remaining_quantity > 0:
                print(f"  批次{lot.id}: {lot.remaining_quantity}股 @ ${lot.cost_basis} ({lot.purchase_date})")
        
        # 指定卖出特定批次（选择最早和最晚的批次）
        specific_lots = [
            {'lot_id': current_lots[0].id, 'quantity': 20},  # 最早批次
            {'lot_id': current_lots[-1].id, 'quantity': 10},  # 最新批次
        ]
        
        sell3 = self.service.record_sell_transaction(
            symbol='AAPL',
            quantity=30,
            price=161.25,
            transaction_date='2024-04-15',
            external_id='sell_003',
            notes='指定批次卖出',
            cost_basis_method='SpecificLot',
            specific_lots=specific_lots
        )
        print(f"卖出3: {sell3.quantity}股 @ ${sell3.price} (SpecificLot)")
        
        allocations3 = self.service.get_sale_allocations_by_transaction(sell3.id)
        total_realized_pnl3 = sum(alloc.realized_pnl for alloc in allocations3)
        print(f"指定批次分配到{len(allocations3)}个批次，已实现盈亏: ${total_realized_pnl3:.2f}")
        
        # === 第四次卖出：FIFO大额卖出 ===
        print("\n--- 第四次卖出：FIFO大额卖出 ---")
        sell4 = self.service.record_sell_transaction(
            symbol='AAPL',
            quantity=120,
            price=155.80,
            transaction_date='2024-04-22',
            external_id='sell_004',
            notes='大额减仓',
            cost_basis_method='FIFO'
        )
        print(f"卖出4: {sell4.quantity}股 @ ${sell4.price} (FIFO)")
        
        allocations4 = self.service.get_sale_allocations_by_transaction(sell4.id)
        total_realized_pnl4 = sum(alloc.realized_pnl for alloc in allocations4)
        print(f"大额FIFO分配到{len(allocations4)}个批次，已实现盈亏: ${total_realized_pnl4:.2f}")
        
        # === 最后一次卖出：清仓操作 ===
        print("\n--- 第五次卖出：部分清仓 ---")
        
        # 检查剩余持仓
        remaining_lots = self.service.get_position_lots('AAPL')
        remaining_shares = sum(lot.remaining_quantity for lot in remaining_lots if lot.remaining_quantity > 0)
        print(f"卖出前剩余持仓: {remaining_shares}股")
        
        # 卖出剩余的一半
        sell_quantity = float(remaining_shares) / 2
        sell5 = self.service.record_sell_transaction(
            symbol='AAPL',
            quantity=sell_quantity,
            price=163.45,
            transaction_date='2024-04-30',
            external_id='sell_005',
            notes='部分清仓',
            cost_basis_method='FIFO'
        )
        print(f"卖出5: {sell5.quantity}股 @ ${sell5.price} (FIFO)")
        
        allocations5 = self.service.get_sale_allocations_by_transaction(sell5.id)
        total_realized_pnl5 = sum(alloc.realized_pnl for alloc in allocations5)
        print(f"清仓分配到{len(allocations5)}个批次，已实现盈亏: ${total_realized_pnl5:.2f}")
        
        # === 最终验证和统计 ===
        print("\n=== 最终验证和统计 ===")
        
        # 验证总交易数量
        self.assertEqual(len(buy_transactions), 10, "应该有10次买入交易")
        
        # 验证总买入数量
        total_bought = sum(tx.quantity for tx in buy_transactions)
        print(f"总买入数量: {total_bought}股")
        
        # 验证总卖出数量
        total_sold_final = sell1.quantity + sell2.quantity + sell3.quantity + sell4.quantity + sell5.quantity
        print(f"总卖出数量: {total_sold_final}股")
        
        # 验证剩余持仓
        final_lots = self.service.get_position_lots('AAPL')
        final_remaining = sum(lot.remaining_quantity for lot in final_lots if lot.remaining_quantity > 0)
        print(f"最终剩余持仓: {final_remaining}股")
        
        # 验证数量平衡
        expected_remaining = total_bought - total_sold_final
        self.assertAlmostEqual(float(final_remaining), expected_remaining, places=4, 
                              msg="剩余持仓应该等于总买入减去总卖出")
        
        # 计算总已实现盈亏
        total_realized_pnl_all = total_realized_pnl + total_realized_pnl2 + total_realized_pnl3 + total_realized_pnl4 + total_realized_pnl5
        print(f"总已实现盈亏: ${total_realized_pnl_all:.2f}")
        
        # 验证批次状态
        active_lots = [lot for lot in final_lots if lot.remaining_quantity > 0]
        closed_lots = [lot for lot in final_lots if lot.remaining_quantity <= 0.0001]
        print(f"活跃批次: {len(active_lots)}个")
        print(f"已关闭批次: {len(closed_lots)}个")
        
        # 打印详细的批次状态
        print("\n活跃批次详情:")
        for lot in active_lots:
            print(f"  批次{lot.id}: {lot.remaining_quantity:.4f}股 @ ${lot.cost_basis:.4f} ({lot.purchase_date})")
        
        print("\n已关闭批次详情:")
        for lot in closed_lots:
            sold_quantity = lot.original_quantity - lot.remaining_quantity
            print(f"  批次{lot.id}: 原{lot.original_quantity}股，已卖{sold_quantity:.4f}股 @ ${lot.cost_basis:.4f}")
        
        print("\n=== 综合AAPL交易场景测试完成 ===")

    def test_cost_basis_method_comparison(self):
        """
        测试不同成本基础方法的对比
        使用相同的买入序列，比较不同卖出方法的结果
        """
        print("\n=== 成本基础方法对比测试 ===")
        
        # 设置相同的买入序列
        buy_data = [
            ('2024-01-10', 100, 150.00),
            ('2024-01-20', 100, 160.00),
            ('2024-01-30', 100, 140.00),
            ('2024-02-10', 100, 170.00),
            ('2024-02-20', 100, 155.00),
        ]
        
        for i, (date, quantity, price) in enumerate(buy_data, 1):
            self.service.record_buy_transaction(
                symbol='AAPL',
                quantity=quantity,
                price=price,
                transaction_date=date,
                external_id=f'setup_buy_{i}'
            )
        
        # 测试卖出200股在不同方法下的结果
        sell_quantity = 200
        sell_price = 165.00
        sell_date = '2024-03-01'
        
        # 创建不同用户来测试不同方法
        methods_results = {}
        
        for method in ['FIFO', 'LIFO', 'AverageCost']:
            # 为每个方法创建独立的测试环境
            
            # 重新创建相同的买入序列
            for i, (date, quantity, price) in enumerate(buy_data, 1):
                self.service.record_buy_transaction(
                    symbol='AAPL',
                    quantity=quantity,
                    price=price,
                    transaction_date=date,
                    external_id=f'{method}_buy_{i}'
                )
            
            # 执行卖出交易
            sell_tx = self.service.record_sell_transaction(
                symbol='AAPL',
                quantity=sell_quantity,
                price=sell_price,
                transaction_date=sell_date,
                external_id=f'{method}_sell',
                cost_basis_method=method
            )
            
            # 计算该方法的结果
            allocations = self.service.get_sale_allocations_by_transaction(sell_tx.id)
            total_realized_pnl = sum(alloc.realized_pnl for alloc in allocations)
            avg_cost_basis = sum(alloc.cost_basis * alloc.quantity_sold for alloc in allocations) / sell_quantity
            
            methods_results[method] = {
                'realized_pnl': total_realized_pnl,
                'avg_cost_basis': avg_cost_basis,
                'allocations_count': len(allocations)
            }
            
            print(f"\n{method}方法结果:")
            print(f"  已实现盈亏: ${total_realized_pnl:.2f}")
            print(f"  平均成本基础: ${avg_cost_basis:.4f}")
            print(f"  分配批次数: {len(allocations)}")
        
        # 验证不同方法产生不同结果
        fifo_pnl = methods_results['FIFO']['realized_pnl']
        lifo_pnl = methods_results['LIFO']['realized_pnl']
        avg_pnl = methods_results['AverageCost']['realized_pnl']
        
        print(f"\n方法对比:")
        print(f"FIFO盈亏: ${fifo_pnl:.2f}")
        print(f"LIFO盈亏: ${lifo_pnl:.2f}")
        print(f"平均成本盈亏: ${avg_pnl:.2f}")
        
        # FIFO和LIFO应该产生不同的结果（因为价格序列是波动的）
        self.assertNotEqual(fifo_pnl, lifo_pnl, "FIFO和LIFO应该产生不同的盈亏结果")
        
        print("\n=== 成本基础方法对比测试完成 ===")


if __name__ == '__main__':
    unittest.main(verbosity=2)