#!/usr/bin/env python3
"""
交易管理 CLI - Stock Trading Manager

提供交易记录、持仓浏览、盈亏计算与组合摘要等命令。

示例 Examples:

  # 记录买入/卖出
  stock-trading buy --user-id u1 -s AAPL -q 100 -p 150.5 -d 2024-01-15
  stock-trading sell --user-id u1 -s AAPL -q 20 -p 160.0 -d 2024-02-01
  
  # 批次级别卖出
  stock-trading sell --user-id u1 -s AAPL -q 30 -p 160.0 -d 2024-02-01 --basis fifo
  stock-trading sell --user-id u1 -s AAPL -q 30 -p 160.0 -d 2024-02-01 --basis specific --specific-lots "lot=1:20,lot=2:10"

  # 查看持仓和批次
  stock-trading positions --user-id u1
  stock-trading lots --user-id u1 -s AAPL
  stock-trading sales --user-id u1 -s AAPL

  # 计算盈亏（当日/历史/每日）
  stock-trading calculate-pnl --user-id u1 --date 2024-02-20
  stock-trading batch-calculate --user-id u1 --start-date 2024-01-01 --end-date 2024-02-29
  stock-trading daily --user-id u1                           # 按今日计算所有持仓盈亏

  # 高级分析功能
  stock-trading portfolio --user-id u1 --as-of-date 2024-02-29
  stock-trading tax-report --user-id u1 --start-date 2024-01-01 --end-date 2024-12-31
  stock-trading rebalance-simulate --user-id u1 -s AAPL -q 50 -p 180.0
"""

import argparse
import logging
from datetime import date
from typing import List, Optional

from stock_analysis.data.storage import create_storage, StorageError
from stock_analysis.utils.logging_utils import setup_logging
from stock_analysis.trading import TransactionService, PortfolioService, PnLCalculator, LotTransactionService
from stock_analysis.trading.config import DEFAULT_TRADING_CONFIG, PriceSource


def _storage_from_args(args: argparse.Namespace):
    return create_storage('sqlite', db_path=str(args.db_path))


def _parse_specific_lots(specific_lots_str: str) -> List[dict]:
    """
    解析specific_lots字符串，格式如: "lot=1:30,lot=2:20"
    返回: [{'lot_id': 1, 'quantity': 30}, {'lot_id': 2, 'quantity': 20}]
    """
    lots = []
    for item in specific_lots_str.split(','):
        item = item.strip()
        if '=' in item and ':' in item:
            prefix, value = item.split('=', 1)
            id_part, qty_part = value.split(':', 1)
            
            # 仅支持 lot= 前缀
            if prefix.lower() == 'lot':
                lots.append({
                    'lot_id': int(id_part),
                    'quantity': float(qty_part)
                })
    
    if not lots:
        raise ValueError(f"无法解析specific_lots参数: {specific_lots_str}")
    
    return lots


def cmd_buy(args: argparse.Namespace) -> int:
    setup_logging('INFO' if args.verbose else 'WARNING')
    storage = _storage_from_args(args)
    config = DEFAULT_TRADING_CONFIG
    svc = TransactionService(storage, config)
    
    try:
        transaction = svc.record_buy_transaction(
            user_id=args.user_id,
            symbol=args.symbol.upper(),
            quantity=args.quantity,
            price=args.price,
            transaction_date=args.date,
            external_id=args.external_id,
            notes=args.notes,
        )
        
        # 成功提示
        if args.external_id:
            print(f"✅ 买入交易记录成功 (ID: {transaction.id}, External ID: {args.external_id})")
        else:
            print(f"✅ 买入交易记录成功 (ID: {transaction.id})")
            
    except ValueError as e:
        print(f"❌ 输入参数错误: {e}")
        return 1
    except StorageError as e:
        # 捕获数据库唯一约束冲突
        if "UNIQUE constraint failed" in str(e) and args.external_id:
            print(f"⚠️  交易 {args.external_id} 已存在，跳过重复记录")
            return 0  # 幂等操作，不视为错误
        else:
            print(f"❌ 数据库错误: {e}")
            return 2
    except Exception as e:
        print(f"❌ 未知错误: {e}")
        return 3
    finally:
        storage.close()
    
    return 0


def cmd_sell(args: argparse.Namespace) -> int:
    setup_logging('INFO' if args.verbose else 'WARNING')
    storage = _storage_from_args(args)
    config = DEFAULT_TRADING_CONFIG
    
    try:
        # 如果指定了批次相关参数，使用LotTransactionService
        if hasattr(args, 'basis') or hasattr(args, 'specific_lots'):
            svc = LotTransactionService(storage, config)
            
            # 解析specific_lots参数
            specific_lots = None
            if hasattr(args, 'specific_lots') and args.specific_lots:
                specific_lots = _parse_specific_lots(args.specific_lots)
            
            # 记录卖出交易
            transaction = svc.record_sell_transaction(
                user_id=args.user_id,
                symbol=args.symbol.upper(),
                quantity=args.quantity,
                price=args.price,
                transaction_date=args.date,
                    external_id=args.external_id,
                notes=args.notes,
                cost_basis_method=getattr(args, 'basis', 'FIFO').upper(),
                specific_lots=specific_lots
            )
            
            # 显示执行回显 - 批次匹配明细
            print(f"✅ 卖出交易记录成功: ID={transaction.id}")
            print(f"📊 交易明细: {args.symbol} {args.quantity}股 @ ${svc.config.format_price(args.price)}")
            print(f"🔍 使用方法: {getattr(args, 'basis', 'FIFO').upper()}")
            
            # 获取刚创建的分配记录以显示明细
            allocations = svc.get_sale_allocations(sale_transaction_id=transaction.id)
            if allocations:
                print(f"\n💰 批次分配明细:")
                print(f"{'批次ID':>8} {'卖出数量':>12} {'成本基础':>12} {'已实现盈亏':>15} {'佣金分摊':>12}")
                print("-" * 70)
                total_realized = 0.0
                for alloc in allocations:
                    print(f"{alloc.lot_id:>8} {alloc.quantity_sold:>12.4f} {svc.config.format_price(alloc.cost_basis):>12} "
                          f"{svc.config.format_amount(alloc.realized_pnl):>15}")
                    total_realized += alloc.realized_pnl
                print("-" * 70)
                print(f"{'总计':>8} {args.quantity:>12.4f} {'':>12} {svc.config.format_amount(total_realized):>15}")
                
        else:
            raise ValueError("批次追踪表未初始化，请先运行迁移脚本")
        
    except ValueError as e:
        print(f"❌ 输入参数错误: {e}")
        return 1
    except StorageError as e:
        if "UNIQUE constraint failed" in str(e) and getattr(args, 'external_id', None):
            print(f"⚠️  交易 {args.external_id} 已存在，跳过重复记录")
            return 0  # 幂等操作，不视为错误
        else:
            print(f"❌ 数据库错误: {e}")
            return 2
    except Exception as e:
        # 捕获其他在service层校验的value error，例如持仓不足
        if "insufficient" in str(e).lower() or "不足" in str(e):
            print(f"❌ 持仓数量不足: {e}")
            return 1
        else:
            print(f"❌ 未知错误: {e}")
            return 3
    finally:
        storage.close()
    
    return 0


def cmd_positions(args: argparse.Namespace) -> int:
    setup_logging('INFO' if args.verbose else 'WARNING')
    storage = _storage_from_args(args)
    config = DEFAULT_TRADING_CONFIG
    svc = TransactionService(storage, config)
    positions = svc.get_current_positions(args.user_id)
    if not positions:
        print("(no positions)")
        storage.close()
        return 0

    for p in positions:
        print(
            f"{p.symbol:8s} qty={p.quantity:,.4f} avg={p.avg_cost:,.4f} "
            f"total_cost={p.total_cost:,.2f} first={p.first_buy_date} last={p.last_transaction_date}"
        )
    storage.close()
    return 0


def _price_source_from_args(ps: Optional[str]) -> str:
    if not ps:
        return PriceSource.ADJ_CLOSE.value
    psn = ps.lower()
    if psn not in (PriceSource.ADJ_CLOSE.value, PriceSource.CLOSE.value):
        raise SystemExit(f"Invalid --price-source: {ps}. Use adj_close|close")
    return psn


def cmd_calculate_pnl(args: argparse.Namespace) -> int:
    setup_logging('INFO' if args.verbose else 'WARNING')
    storage = _storage_from_args(args)
    config = DEFAULT_TRADING_CONFIG
    calc = PnLCalculator(
        storage=storage,
        config=config,
        price_field=_price_source_from_args(args.price_source),
        only_trading_days=args.only_trading_days,
    )
    if args.symbols:
        # 针对指定股票逐一计算
        for sym in args.symbols:
            calc.calculate_daily_pnl(args.user_id, sym.upper(), args.date)
    else:
        # 对所有持仓计算
        calc.calculate_all_positions_pnl(args.user_id, args.date)
    storage.close()
    return 0


def cmd_batch_calculate(args: argparse.Namespace) -> int:
    setup_logging('INFO' if args.verbose else 'WARNING')
    storage = _storage_from_args(args)
    config = DEFAULT_TRADING_CONFIG
    calc = PnLCalculator(
        storage=storage,
        config=config,
        price_field=_price_source_from_args(args.price_source),
        only_trading_days=args.only_trading_days,
    )
    symbols = [s.upper() for s in args.symbols] if args.symbols else None
    res = calc.batch_calculate_historical_pnl(
        user_id=args.user_id,
        start_date=args.start_date,
        end_date=args.end_date,
        symbols=symbols,
    )
    print(res)
    storage.close()
    return 0


def cmd_daily(args: argparse.Namespace) -> int:
    setup_logging('INFO' if args.verbose else 'WARNING')
    storage = _storage_from_args(args)
    config = DEFAULT_TRADING_CONFIG
    today = date.today().strftime('%Y-%m-%d')
    calc = PnLCalculator(
        storage=storage,
        config=config,
        price_field=_price_source_from_args(args.price_source),
        only_trading_days=args.only_trading_days,
    )
    calc.calculate_all_positions_pnl(args.user_id, today)
    storage.close()
    return 0


def cmd_portfolio(args: argparse.Namespace) -> int:
    setup_logging('INFO' if args.verbose else 'WARNING')
    storage = _storage_from_args(args)
    config = DEFAULT_TRADING_CONFIG
    portfolio = PortfolioService(storage, config)
    summary = portfolio.get_portfolio_summary(args.user_id, args.as_of_date)
    # 简单打印摘要
    header = summary.copy()
    positions = header.pop('positions', [])
    print("Summary:")
    for k, v in header.items():
        print(f"  {k}: {v}")
    print("\nPositions:")
    if not positions:
        print("  (none)")
    else:
        for p in positions:
            print(
                f"  {p['symbol']:8s} qty={p['quantity']:,.4f} avg={p['avg_cost']:,.4f} "
                f"mv={p.get('market_value', 0):,.2f} unreal={p.get('unrealized_pnl', 0):,.2f}"
            )
    storage.close()
    return 0


def cmd_tax_report(args: argparse.Namespace) -> int:
    """生成税务申报所需的成本基础明细"""
    setup_logging('INFO' if args.verbose else 'WARNING')
    storage = _storage_from_args(args)
    config = DEFAULT_TRADING_CONFIG
    svc = LotTransactionService(storage, config)
    
    try:
        # 获取用户的所有卖出分配记录
        allocations = svc.get_sale_allocations(args.user_id)
        
        if not allocations:
            print("(no sales found)")
            storage.close()
            return 0
        
        # 按日期过滤（如果提供了日期范围）
        if hasattr(args, 'start_date') and args.start_date:
            allocations = [a for a in allocations if a.sale_date >= args.start_date]
        
        if hasattr(args, 'end_date') and args.end_date:
            allocations = [a for a in allocations if a.sale_date <= args.end_date]
        
        if not allocations:
            print("(no sales in specified period)")
            storage.close()
            return 0
        
        print("=== TAX REPORT: REALIZED GAINS/LOSSES ===")
        print(f"User ID: {args.user_id}")
        if hasattr(args, 'start_date') and args.start_date:
            print(f"Period: {args.start_date} to {getattr(args, 'end_date', 'present')}")
        print()
        
        print(f"{'Sale Date':>12} {'Symbol':>8} {'Qty Sold':>10} {'Sale Price':>12} {'Cost Basis':>12} "
              f"{'Gross Proceeds':>15} {'Cost':>12} {'Gain/Loss':>12} {'Commission':>10}")
        print("-" * 120)
        
        total_proceeds = 0.0
        total_cost = 0.0
        total_gain_loss = 0.0
        
        for alloc in sorted(allocations, key=lambda x: x.sale_date):
            gross_proceeds = alloc.sale_price * alloc.quantity_sold
            cost = alloc.cost_basis * alloc.quantity_sold
            
            print(f"{alloc.sale_date:>12} {alloc.symbol:>8} {alloc.quantity_sold:>10.4f} "
                  f"{alloc.sale_price:>12.4f} {alloc.cost_basis:>12.4f} "
                  f"{gross_proceeds:>15.2f} {cost:>12.2f} {alloc.realized_pnl:>12.2f}")
            
            total_proceeds += gross_proceeds
            total_cost += cost
            total_gain_loss += alloc.realized_pnl
        
        print("-" * 120)
        print(f"{'TOTAL':>12} {'':>8} {'':>10} {'':>12} {'':>12} "
              f"{total_proceeds:>15.2f} {total_cost:>12.2f} {total_gain_loss:>12.2f}")
        
        print(f"\n=== SUMMARY ===")
        print(f"Total Gross Proceeds: ${total_proceeds:,.2f}")
        print(f"Total Cost Basis: ${total_cost:,.2f}")
        print(f"Net Realized Gain/Loss: ${total_gain_loss:,.2f}")
        
    except Exception as e:
        print(f"❌ 生成税务报告失败: {e}")
        return 1
    finally:
        storage.close()
    
    return 0


def cmd_rebalance_simulate(args: argparse.Namespace) -> int:
    """模拟不同成本基础方法的税负影响"""
    setup_logging('INFO' if args.verbose else 'WARNING')
    storage = _storage_from_args(args)
    config = DEFAULT_TRADING_CONFIG
    svc = LotTransactionService(storage, config)
    
    try:
        # 获取当前持仓批次
        lots = svc.get_position_lots(args.user_id, args.symbol.upper() if args.symbol else None)
        
        if not lots:
            print("(no position lots for simulation)")
            storage.close()
            return 0
        
        print("=== REBALANCE SIMULATION ===")
        print(f"User ID: {args.user_id}")
        if args.symbol:
            print(f"Symbol: {args.symbol.upper()}")
        print(f"Simulation Sale Quantity: {args.quantity}")
        print(f"Simulation Sale Price: ${args.price:.4f}")
        print()
        
        # 模拟不同成本基础方法
        methods = ['FIFO', 'LIFO']
        if args.symbol:  # 只有单个股票时才能模拟SpecificLot
            methods.append('SpecificLot')
        
        results = {}
        
        for method in methods:
            print(f"--- {method} Method ---")
            
            try:
                # 调用内部方法模拟批次匹配（不实际执行卖出）
                if method == 'SpecificLot' and args.symbol:
                    # 为SpecificLot选择最优批次（最低成本基础）
                    symbol_lots = [lot for lot in lots if lot.symbol == args.symbol.upper()]
                    if symbol_lots:
                        best_lot = min(symbol_lots, key=lambda x: x.cost_basis)
                        sim_quantity = min(args.quantity, best_lot.remaining_quantity)
                        
                        # 计算模拟结果
                        lot_realized = (args.price - best_lot.cost_basis) * sim_quantity
                        lot_proceeds = args.price * sim_quantity
                        lot_cost = best_lot.cost_basis * sim_quantity
                        
                        print(f"  Lot {best_lot.id}: {sim_quantity:.4f} shares @ ${best_lot.cost_basis:.4f} = ${lot_realized:+.2f}")
                        
                        results[method] = {
                            'realized_pnl': lot_realized,
                            'proceeds': lot_proceeds,
                            'cost': lot_cost
                        }
                else:
                    # 对于FIFO/LIFO，简化模拟
                    symbol_lots = [lot for lot in lots if lot.symbol == (args.symbol.upper() if args.symbol else lot.symbol)]
                    
                    if method == 'FIFO':
                        sorted_lots = sorted(symbol_lots, key=lambda x: x.purchase_date)
                    else:  # LIFO
                        sorted_lots = sorted(symbol_lots, key=lambda x: x.purchase_date, reverse=True)
                    
                    remaining_qty = args.quantity
                    total_realized = 0.0
                    total_proceeds = 0.0
                    total_cost = 0.0
                    
                    for lot in sorted_lots:
                        if remaining_qty <= 0:
                            break
                        
                        qty_to_sell = min(remaining_qty, lot.remaining_quantity)
                        lot_realized = (args.price - lot.cost_basis) * qty_to_sell
                        lot_proceeds = args.price * qty_to_sell
                        lot_cost = lot.cost_basis * qty_to_sell
                        
                        total_realized += lot_realized
                        total_proceeds += lot_proceeds
                        total_cost += lot_cost
                        remaining_qty -= qty_to_sell
                        
                        print(f"  Lot {lot.id}: {qty_to_sell:.4f} shares @ ${lot.cost_basis:.4f} = ${lot_realized:+.2f}")
                    
                    results[method] = {
                        'realized_pnl': total_realized,
                        'proceeds': total_proceeds,
                        'cost': total_cost
                    }
                
                print(f"  Total Realized P&L: ${results[method]['realized_pnl']:+,.2f}")
                print()
                
            except Exception as method_error:
                print(f"  Error simulating {method}: {method_error}")
                print()
        
        # 比较结果
        if len(results) > 1:
            print("=== COMPARISON ===")
            best_method = max(results.keys(), key=lambda m: results[m]['realized_pnl'])
            worst_method = min(results.keys(), key=lambda m: results[m]['realized_pnl'])
            
            print(f"Best method (highest gain/lowest loss): {best_method} (${results[best_method]['realized_pnl']:+,.2f})")
            print(f"Worst method (lowest gain/highest loss): {worst_method} (${results[worst_method]['realized_pnl']:+,.2f})")
            
            if best_method != worst_method:
                difference = results[best_method]['realized_pnl'] - results[worst_method]['realized_pnl']
                print(f"Tax impact difference: ${difference:+,.2f}")
        
    except Exception as e:
        print(f"❌ 模拟失败: {e}")
        return 1
    finally:
        storage.close()
    
    return 0


def cmd_lots(args: argparse.Namespace) -> int:
    """查看持仓批次"""
    setup_logging('INFO' if args.verbose else 'WARNING')
    storage = _storage_from_args(args)
    config = DEFAULT_TRADING_CONFIG
    svc = LotTransactionService(storage, config)
    
    symbol = args.symbol.upper() if args.symbol else None
    lots = svc.get_position_lots(args.user_id, symbol)
    
    if not lots:
        print("(no active lots)")
        storage.close()
        return 0
    
    print(f"{'ID':>6} {'Symbol':>8} {'Original':>10} {'Remaining':>10} {'Cost Basis':>12} {'Purchase Date':>12} {'Status':>8}")
    print("-" * 80)
    
    for lot in lots:
        status = "CLOSED" if lot.is_closed else "OPEN"
        print(f"{lot.id:>6} {lot.symbol:>8} {lot.original_quantity:>10.4f} {lot.remaining_quantity:>10.4f} "
              f"{lot.cost_basis:>12.4f} {lot.purchase_date:>12} {status:>8}")
    
    storage.close()
    return 0


def cmd_sales(args: argparse.Namespace) -> int:
    """查看卖出分配记录"""
    setup_logging('INFO' if args.verbose else 'WARNING')
    storage = _storage_from_args(args)
    config = DEFAULT_TRADING_CONFIG
    svc = LotTransactionService(storage, config)
    
    symbol = args.symbol.upper() if args.symbol else None
    allocations = svc.get_sale_allocations(args.user_id, symbol)
    
    if not allocations:
        print("(no sale allocations)")
        storage.close()
        return 0
    
    print(f"{'ID':>6} {'Sale TxnID':>10} {'Lot ID':>8} {'Qty Sold':>10} {'Cost Basis':>12} "
          f"{'Sale Price':>12} {'Realized PnL':>12}")
    print("-" * 90)
    
    for alloc in allocations:
        print(f"{alloc.id:>6} {alloc.sale_transaction_id:>10} {alloc.lot_id:>8} {alloc.quantity_sold:>10.4f} "
              f"{alloc.cost_basis:>12.4f} {alloc.sale_price:>12.4f} {alloc.realized_pnl:>12.2f}")
    
    storage.close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description='交易管理 CLI')
    p.add_argument('--db-path', default='database/stock_data.db', help='数据库路径')
    sub = p.add_subparsers(dest='command', required=True)

    # buy
    buy = sub.add_parser('buy', help='记录买入交易')
    buy.add_argument('--user-id', required=True)
    buy.add_argument('-s', '--symbol', required=True)
    buy.add_argument('-q', '--quantity', type=float, required=True)
    buy.add_argument('-p', '--price', type=float, required=True)
    buy.add_argument('-d', '--date', required=True, help='YYYY-MM-DD')
    buy.add_argument('--external-id', help='外部业务ID，用于去重')
    buy.add_argument('--notes')
    buy.add_argument('-v', '--verbose', action='store_true')
    buy.set_defaults(func=cmd_buy)

    # sell
    sell = sub.add_parser('sell', help='记录卖出交易')
    sell.add_argument('--user-id', required=True)
    sell.add_argument('-s', '--symbol', required=True)
    sell.add_argument('-q', '--quantity', type=float, required=True)
    sell.add_argument('-p', '--price', type=float, required=True)
    sell.add_argument('-d', '--date', required=True, help='YYYY-MM-DD')
    sell.add_argument('--external-id', help='外部业务ID，用于去重')
    sell.add_argument('--notes')
    sell.add_argument('--basis', choices=['fifo', 'lifo', 'specific', 'average'], 
                     help='成本基础方法 (默认FIFO)')
    sell.add_argument('--specific-lots', type=str, 
                     help='指定批次格式: "lot=1:30,lot=2:20"')
    sell.add_argument('-v', '--verbose', action='store_true')
    sell.set_defaults(func=cmd_sell)

    # positions
    pos = sub.add_parser('positions', help='查看当前持仓')
    pos.add_argument('--user-id', required=True)
    pos.add_argument('-v', '--verbose', action='store_true')
    pos.set_defaults(func=cmd_positions)

    # calculate-pnl
    calc = sub.add_parser('calculate-pnl', help='计算指定日期的盈亏')
    calc.add_argument('--user-id', required=True)
    calc.add_argument('--date', required=True, help='YYYY-MM-DD')
    calc.add_argument('--symbols', nargs='+', help='可选，指定股票列表')
    calc.add_argument('--price-source', choices=['adj_close', 'close'], default='adj_close')
    calc.add_argument('--only-trading-days', action='store_true', help='只按交易日计算')
    calc.add_argument('-v', '--verbose', action='store_true')
    calc.set_defaults(func=cmd_calculate_pnl)

    # batch-calculate
    bcalc = sub.add_parser('batch-calculate', help='批量计算历史盈亏')
    bcalc.add_argument('--user-id', required=True)
    bcalc.add_argument('--start-date', required=True)
    bcalc.add_argument('--end-date', required=True)
    bcalc.add_argument('--symbols', nargs='+', help='可选，指定股票列表')
    bcalc.add_argument('--price-source', choices=['adj_close', 'close'], default='adj_close')
    bcalc.add_argument('--only-trading-days', action='store_true', help='只按交易日计算')
    bcalc.add_argument('-v', '--verbose', action='store_true')
    bcalc.set_defaults(func=cmd_batch_calculate)

    # daily
    daily = sub.add_parser('daily', help='计算今日所有持仓的盈亏（便于 cron 调度）')
    daily.add_argument('--user-id', required=True)
    daily.add_argument('--price-source', choices=['adj_close', 'close'], default='adj_close')
    daily.add_argument('--only-trading-days', action='store_true', help='只按交易日计算')
    daily.add_argument('-v', '--verbose', action='store_true')
    daily.set_defaults(func=cmd_daily)

    # portfolio
    port = sub.add_parser('portfolio', help='查看投资组合摘要')
    port.add_argument('--user-id', required=True)
    port.add_argument('--as-of-date', help='YYYY-MM-DD，默认今天')
    port.add_argument('-v', '--verbose', action='store_true')
    port.set_defaults(func=cmd_portfolio)

    # tax-report - 新增高级功能
    tax = sub.add_parser('tax-report', help='生成税务申报所需的成本基础明细')
    tax.add_argument('--user-id', required=True)
    tax.add_argument('--start-date', help='开始日期 YYYY-MM-DD')
    tax.add_argument('--end-date', help='结束日期 YYYY-MM-DD')
    tax.add_argument('-v', '--verbose', action='store_true')
    tax.set_defaults(func=cmd_tax_report)

    # rebalance-simulate - 新增高级功能
    rebalance = sub.add_parser('rebalance-simulate', help='模拟不同成本基础方法的税负影响')
    rebalance.add_argument('--user-id', required=True)
    rebalance.add_argument('-s', '--symbol', help='可选，指定股票代码')
    rebalance.add_argument('-q', '--quantity', type=float, required=True, help='模拟卖出数量')
    rebalance.add_argument('-p', '--price', type=float, required=True, help='模拟卖出价格')
    rebalance.add_argument('-v', '--verbose', action='store_true')
    rebalance.set_defaults(func=cmd_rebalance_simulate)

    # lots - 查看持仓批次
    lots = sub.add_parser('lots', help='查看持仓批次')
    lots.add_argument('--user-id', required=True)
    lots.add_argument('-s', '--symbol', help='可选，指定股票代码')
    lots.add_argument('-v', '--verbose', action='store_true')
    lots.set_defaults(func=cmd_lots)

    # sales - 查看卖出分配记录
    sales = sub.add_parser('sales', help='查看卖出分配记录')
    sales.add_argument('--user-id', required=True)
    sales.add_argument('-s', '--symbol', help='可选，指定股票代码')
    sales.add_argument('-v', '--verbose', action='store_true')
    sales.set_defaults(func=cmd_sales)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == '__main__':
    raise SystemExit(main())