#!/usr/bin/env python3
"""
交互式交易流程测试
模拟真实的交易模式，包括逐步建仓、分批减仓、混合操作等
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


class TestInteractiveTradingFlows(unittest.TestCase):
    """交互式交易流程测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        self.storage = create_storage('sqlite', db_path=self.temp_db.name)
        
        # 确保测试股票存在
        for symbol in ['AAPL', 'MSFT', 'GOOGL']:
            self.storage.ensure_stock_exists(symbol)
        
        self.service = LotTransactionService(self.storage, DEFAULT_TRADING_CONFIG)
    
    def tearDown(self):
        """清理测试环境"""
        self.storage.close()
        os.unlink(self.temp_db.name)
    
    def _print_portfolio_status(self, title: str):
        """打印当前投资组合状态"""
        print(f"\n--- {title} ---")
        for symbol in ['AAPL', 'MSFT', 'GOOGL']:
            lots = self.service.get_position_lots(symbol)
            active_lots = [lot for lot in lots if lot.remaining_quantity > 0]
            total_shares = sum(lot.remaining_quantity for lot in active_lots)
            
            if total_shares > 0:
                avg_cost = sum(lot.remaining_quantity * lot.cost_basis for lot in active_lots) / total_shares
                print(f"{symbol}: {total_shares:.4f}股，平均成本${avg_cost:.4f}，{len(active_lots)}个批次")
            else:
                print(f"{symbol}: 无持仓")
    
    def test_progressive_position_building(self):
        """
        测试渐进式建仓策略
        模拟投资者逐步建仓AAPL的过程
        """
        print("\n=== 渐进式建仓策略测试 ===")
        
        # 第一阶段：小额试探性买入
        print("\n第一阶段：小额试探性买入")
        
        transactions = []
        
        # 试探性买入
        tx1 = self.service.record_buy_transaction(
            symbol='AAPL',
            quantity=10,
            price=150.00,
            transaction_date='2024-01-02',
            external_id='progressive_001',
            notes='试探性小额买入'
        )
        transactions.append(('BUY', tx1))
        
        self._print_portfolio_status("试探性买入后")
        
        # 第二阶段：价格上涨，继续加仓
        print("\n第二阶段：价格上涨，继续加仓")
        
        tx2 = self.service.record_buy_transaction(
            symbol='AAPL',
            quantity=25,
            price=155.50,
            transaction_date='2024-01-10',
            external_id='progressive_002',
            notes='价格上涨，小幅加仓'
        )
        transactions.append(('BUY', tx2))
        
        tx3 = self.service.record_buy_transaction(
            symbol='AAPL',
            quantity=40,
            price=158.75,
            transaction_date='2024-01-18',
            external_id='progressive_003',
            notes='趋势确认，继续加仓'
        )
        transactions.append(('BUY', tx3))
        
        self._print_portfolio_status("上涨期加仓后")
        
        # 第三阶段：价格回调，大额加仓
        print("\n第三阶段：价格回调，大额加仓")
        
        tx4 = self.service.record_buy_transaction(
            symbol='AAPL',
            quantity=60,
            price=145.25,
            transaction_date='2024-01-25',
            external_id='progressive_004',
            notes='回调买入机会'
        )
        transactions.append(('BUY', tx4))
        
        tx5 = self.service.record_buy_transaction(
            symbol='AAPL',
            quantity=80,
            price=142.80,
            transaction_date='2024-02-02',
            external_id='progressive_005',
            notes='深度回调，大额买入'
        )
        transactions.append(('BUY', tx5))
        
        self._print_portfolio_status("回调加仓后")
        
        # 第四阶段：价格反弹，部分获利了结
        print("\n第四阶段：价格反弹，部分获利了结")
        
        # 先小额获利了结
        sell1 = self.service.record_sell_transaction(
            symbol='AAPL',
            quantity=30,
            price=162.40,
            transaction_date='2024-02-12',
            external_id='progressive_sell_001',
            notes='小额获利了结',
            cost_basis_method='FIFO'
        )
        transactions.append(('SELL', sell1))
        
        self._print_portfolio_status("小额获利了结后")
        
        # 继续上涨，再次获利了结
        sell2 = self.service.record_sell_transaction(
            symbol='AAPL',
            quantity=50,
            price=168.90,
            transaction_date='2024-02-20',
            external_id='progressive_sell_002',
            notes='继续获利了结',
            cost_basis_method='FIFO'
        )
        transactions.append(('SELL', sell2))
        
        self._print_portfolio_status("二次获利了结后")
        
        # 第五阶段：高位震荡，灵活操作
        print("\n第五阶段：高位震荡，灵活操作")
        
        # 高位小额减仓
        sell3 = self.service.record_sell_transaction(
            symbol='AAPL',
            quantity=25,
            price=171.20,
            transaction_date='2024-03-01',
            external_id='progressive_sell_003',
            notes='高位减仓',
            cost_basis_method='LIFO'  # 改用LIFO
        )
        transactions.append(('SELL', sell3))
        
        # 回调时重新买入
        tx6 = self.service.record_buy_transaction(
            symbol='AAPL',
            quantity=35,
            price=164.75,
            transaction_date='2024-03-08',
            external_id='progressive_006',
            notes='回调重新买入'
        )
        transactions.append(('BUY', tx6))
        
        self._print_portfolio_status("灵活操作后最终状态")
        
        # 验证交易历史
        print(f"\n总交易笔数: {len(transactions)}")
        buy_count = sum(1 for action, _ in transactions if action == 'BUY')
        sell_count = sum(1 for action, _ in transactions if action == 'SELL')
        print(f"买入交易: {buy_count}笔")
        print(f"卖出交易: {sell_count}笔")
        
        # 验证最终持仓
        final_lots = self.service.get_position_lots('AAPL')
        active_lots = [lot for lot in final_lots if lot.remaining_quantity > 0]
        total_remaining = sum(lot.remaining_quantity for lot in active_lots)
        
        self.assertGreater(total_remaining, 0, "应该还有剩余持仓")
        self.assertGreater(len(active_lots), 0, "应该有活跃批次")
        
        print(f"最终持仓: {total_remaining:.4f}股，{len(active_lots)}个活跃批次")
        
        print("\n=== 渐进式建仓策略测试完成 ===")
    
    def test_multi_stock_portfolio_management(self):
        """
        测试多股票投资组合管理
        同时管理AAPL、MSFT、GOOGL三只股票
        """
        print("\n=== 多股票投资组合管理测试 ===")
        
        # 第一阶段：分散建仓
        print("\n第一阶段：分散建仓三只股票")
        
        # AAPL 建仓
        self.service.record_buy_transaction(
            symbol='AAPL',
            quantity=100,
            price=150.00,
            transaction_date='2024-01-05',
            external_id='multi_aapl_001',
            notes='AAPL初始建仓'
        )
        
        # MSFT 建仓
        self.service.record_buy_transaction(
            symbol='MSFT',
            quantity=80,
            price=380.00,
            transaction_date='2024-01-08',
            external_id='multi_msft_001',
            notes='MSFT初始建仓'
        )
        
        # GOOGL 建仓
        self.service.record_buy_transaction(
            symbol='GOOGL',
            quantity=50,
            price=140.00,
            transaction_date='2024-01-12',
            external_id='multi_googl_001',
            notes='GOOGL初始建仓'
        )
        
        self._print_portfolio_status("分散建仓后")
        
        # 第二阶段：根据市场表现调整
        print("\n第二阶段：根据市场表现调整仓位")
        
        # AAPL 表现好，加仓
        self.service.record_buy_transaction(
            symbol='AAPL',
            quantity=50,
            price=160.00,
            transaction_date='2024-01-20',
            external_id='multi_aapl_002',
            notes='AAPL表现强劲，加仓'
        )
        
        # MSFT 表现一般，小幅加仓
        self.service.record_buy_transaction(
            symbol='MSFT',
            quantity=20,
            price=385.00,
            transaction_date='2024-01-25',
            external_id='multi_msft_002',
            notes='MSFT小幅加仓'
        )
        
        # GOOGL 表现不佳，减仓
        self.service.record_sell_transaction(
            symbol='GOOGL',
            quantity=20,
            price=135.00,
            transaction_date='2024-01-30',
            external_id='multi_googl_sell_001',
            notes='GOOGL表现不佳，减仓',
            cost_basis_method='FIFO'
        )
        
        self._print_portfolio_status("市场表现调整后")
        
        # 第三阶段：扇形操作（轮换投资）
        print("\n第三阶段：扇形操作")
        
        # 从MSFT获利了结，加仓AAPL
        self.service.record_sell_transaction(
            symbol='MSFT',
            quantity=30,
            price=395.00,
            transaction_date='2024-02-05',
            external_id='multi_msft_sell_001',
            notes='MSFT获利了结',
            cost_basis_method='FIFO'
        )
        
        self.service.record_buy_transaction(
            symbol='AAPL',
            quantity=75,
            price=158.00,
            transaction_date='2024-02-07',
            external_id='multi_aapl_003',
            notes='用MSFT利润加仓AAPL'
        )
        
        # 重新建仓GOOGL
        self.service.record_buy_transaction(
            symbol='GOOGL',
            quantity=40,
            price=130.00,
            transaction_date='2024-02-12',
            external_id='multi_googl_002',
            notes='GOOGL低位重新建仓'
        )
        
        self._print_portfolio_status("扇形操作后")
        
        # 第四阶段：整体减仓
        print("\n第四阶段：牛市高点整体减仓")
        
        # 各股票都部分获利了结
        self.service.record_sell_transaction(
            symbol='AAPL',
            quantity=60,
            price=175.00,
            transaction_date='2024-02-20',
            external_id='multi_aapl_sell_001',
            notes='牛市高点AAPL减仓',
            cost_basis_method='LIFO'
        )
        
        self.service.record_sell_transaction(
            symbol='MSFT',
            quantity=25,
            price=410.00,
            transaction_date='2024-02-22',
            external_id='multi_msft_sell_002',
            notes='牛市高点MSFT减仓',
            cost_basis_method='LIFO'
        )
        
        self.service.record_sell_transaction(
            symbol='GOOGL',
            quantity=15,
            price=145.00,
            transaction_date='2024-02-25',
            external_id='multi_googl_sell_002',
            notes='牛市高点GOOGL减仓',
            cost_basis_method='FIFO'
        )
        
        self._print_portfolio_status("整体减仓后最终状态")
        
        # 验证多股票组合
        portfolio_summary = {}
        total_portfolio_value = 0
        
        for symbol in ['AAPL', 'MSFT', 'GOOGL']:
            lots = self.service.get_position_lots(symbol)
            active_lots = [lot for lot in lots if lot.remaining_quantity > 0]
            
            if active_lots:
                total_shares = sum(lot.remaining_quantity for lot in active_lots)
                total_cost = sum(lot.remaining_quantity * lot.cost_basis for lot in active_lots)
                avg_cost = total_cost / total_shares if total_shares > 0 else 0
                
                portfolio_summary[symbol] = {
                    'shares': total_shares,
                    'avg_cost': avg_cost,
                    'total_cost': total_cost,
                    'lots_count': len(active_lots)
                }
                total_portfolio_value += total_cost
        
        print(f"\n投资组合汇总:")
        for symbol, data in portfolio_summary.items():
            weight = (data['total_cost'] / total_portfolio_value) * 100 if total_portfolio_value > 0 else 0
            print(f"{symbol}: {data['shares']:.4f}股，成本${data['total_cost']:.2f}，权重{weight:.1f}%")
        
        print(f"总投资组合价值: ${total_portfolio_value:.2f}")
        
        # 验证至少持有两只股票
        self.assertGreaterEqual(len(portfolio_summary), 2, "应该持有至少两只股票")
        
        print("\n=== 多股票投资组合管理测试完成 ===")
    
    def test_tactical_trading_with_mixed_methods(self):
        """
        测试战术性交易：混合使用不同成本基础方法
        模拟精明投资者根据税务和投资策略选择最优卖出方法
        """
        print("\n=== 战术性交易混合方法测试 ===")
        
        # 建立多个不同成本的批次
        print("\n建立多个不同成本的批次")
        
        batch_data = [
            ('2024-01-02', 100, 140.00, '低价批次1'),
            ('2024-01-15', 100, 160.00, '高价批次1'),
            ('2024-01-25', 100, 135.00, '低价批次2'),
            ('2024-02-05', 100, 170.00, '高价批次2'),
            ('2024-02-15', 100, 145.00, '中价批次1'),
            ('2024-02-25', 100, 165.00, '高价批次3'),
            ('2024-03-05', 100, 130.00, '低价批次3'),
            ('2024-03-15', 100, 175.00, '最高价批次'),
        ]
        
        for i, (date, quantity, price, note) in enumerate(batch_data, 1):
            self.service.record_buy_transaction(
                symbol='AAPL',
                quantity=quantity,
                price=price,
                transaction_date=date,
                external_id=f'tactical_buy_{i:02d}',
                notes=note
            )
        
        # 显示所有批次
        lots = self.service.get_position_lots('AAPL')
        print("\n所有批次详情:")
        for lot in lots:
            print(f"批次{lot.id}: {lot.remaining_quantity}股 @ ${lot.cost_basis:.2f} ({lot.purchase_date}) - {lot.purchase_date}")
        
        # 战术1：牛市中期，使用FIFO获利了结（卖掉最早的低成本批次）
        print("\n战术1: 牛市中期使用FIFO获利了结")
        
        sell1 = self.service.record_sell_transaction(
            symbol='AAPL',
            quantity=150,
            price=180.00,
            transaction_date='2024-03-20',
            external_id='tactical_sell_001',
            notes='牛市FIFO获利了结',
            cost_basis_method='FIFO'
        )
        
        allocations1 = self.service.get_sale_allocations_by_transaction(sell1.id)
        pnl1 = sum(alloc.realized_pnl for alloc in allocations1)
        print(f"FIFO卖出结果: 已实现盈亏${pnl1:.2f}")
        
        # 战术2：年底税务筹划，使用LIFO抵消收益（卖掉高成本批次）
        print("\n战术2: 年底税务筹划使用LIFO")
        
        sell2 = self.service.record_sell_transaction(
            symbol='AAPL',
            quantity=120,
            price=155.00,  # 较低价格
            transaction_date='2024-12-15',
            external_id='tactical_sell_002',
            notes='年底税务筹划LIFO',
            cost_basis_method='LIFO'
        )
        
        allocations2 = self.service.get_sale_allocations_by_transaction(sell2.id)
        pnl2 = sum(alloc.realized_pnl for alloc in allocations2)
        print(f"LIFO卖出结果: 已实现盈亏${pnl2:.2f}")
        
        # 战术3：精确控制，使用SpecificLot选择特定批次
        print("\n战术3: 精确控制使用SpecificLot")
        
        # 获取当前剩余批次
        current_lots = self.service.get_position_lots('AAPL')
        active_lots = [lot for lot in current_lots if lot.remaining_quantity > 0]
        
        print("当前剩余批次:")
        for lot in active_lots:
            print(f"  批次{lot.id}: {lot.remaining_quantity}股 @ ${lot.cost_basis:.2f}")
        
        # 选择特定的中等成本批次
        if len(active_lots) >= 2:
            # 选择第二和第三个批次
            specific_lots = [
                {'lot_id': active_lots[1].id, 'quantity': min(50, float(active_lots[1].remaining_quantity))},
                {'lot_id': active_lots[2].id, 'quantity': min(40, float(active_lots[2].remaining_quantity))},
            ]
            
            total_specific_qty = sum(lot['quantity'] for lot in specific_lots)
            
            sell3 = self.service.record_sell_transaction(
                symbol='AAPL',
                quantity=total_specific_qty,
                price=162.00,
                transaction_date='2024-12-20',
                external_id='tactical_sell_003',
                notes='精确控制特定批次',
                cost_basis_method='SpecificLot',
                specific_lots=specific_lots
            )
            
            allocations3 = self.service.get_sale_allocations_by_transaction(sell3.id)
            pnl3 = sum(alloc.realized_pnl for alloc in allocations3)
            print(f"SpecificLot卖出结果: 已实现盈亏${pnl3:.2f}")
        
        # 分析战术效果
        print("\n=== 战术效果分析 ===")
        print(f"FIFO策略盈亏: ${pnl1:.2f}")
        print(f"LIFO策略盈亏: ${pnl2:.2f}")
        if 'pnl3' in locals():
            print(f"SpecificLot策略盈亏: ${pnl3:.2f}")
            total_realized = pnl1 + pnl2 + pnl3
        else:
            total_realized = pnl1 + pnl2
        
        print(f"总已实现盈亏: ${total_realized:.2f}")
        
        # 验证剩余持仓
        final_lots = self.service.get_position_lots('AAPL')
        final_active = [lot for lot in final_lots if lot.remaining_quantity > 0]
        final_shares = sum(lot.remaining_quantity for lot in final_active)
        
        print(f"最终剩余持仓: {final_shares:.4f}股，{len(final_active)}个活跃批次")
        
        # 验证不同方法产生的效果确实不同
        self.assertNotEqual(pnl1, pnl2, "FIFO和LIFO应该产生不同的盈亏结果")
        
        # 验证交易逻辑正确性
        self.assertGreater(final_shares, 0, "应该还有剩余持仓")
        
        print("\n=== 战术性交易混合方法测试完成 ===")


if __name__ == '__main__':
    unittest.main(verbosity=2)