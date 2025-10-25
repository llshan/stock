#!/usr/bin/env python3
"""
交易管理 CLI - Stock Trading Manager

提供交易记录、持仓浏览、盈亏计算与组合摘要等命令。

示例 Examples:

  # 记录买入/卖出
  stock-trading buy -s AAPL -q 100 -p 150.5 -d 2024-01-15
  stock-trading sell -s AAPL -q 20 -p 160.0 -d 2024-02-01
  
  # 批次级别卖出
  stock-trading sell -s AAPL -q 30 -p 160.0 -d 2024-02-01 --basis fifo
  stock-trading sell -s AAPL -q 30 -p 160.0 -d 2024-02-01 --basis specific --specific-lots "lot=1:20,lot=2:10"

  # 查看持仓和批次
  stock-trading positions
  stock-trading lots -s AAPL
  stock-trading sales -s AAPL

  # 计算盈亏（当日/历史/每日）
  stock-trading calculate-pnl --date 2024-02-20
  stock-trading batch-calculate --start-date 2024-01-01 --end-date 2024-02-29
  stock-trading daily # 按今日计算所有持仓盈亏

  # 高级分析功能
  stock-trading portfolio --as-of-date 2024-02-29
  stock-trading tax-report --start-date 2024-01-01 --end-date 2024-12-31
  stock-trading rebalance-simulate -s AAPL -q 50 -p 180.0
"""

import argparse
import logging
from datetime import date
from typing import List, Optional

from stock_analysis.data.storage import create_storage, StorageError
from stock_analysis.utils.logging_utils import setup_logging
from stock_analysis.trading import TransactionService, PortfolioService, PnLCalculator, LotTransactionService
from stock_analysis.trading.config import DEFAULT_TRADING_CONFIG, PriceSource


def get_daily_pnl(symbol: str, shares: int) -> float:
    """计算股票的当天盈亏"""
    try:
        from stock_analysis.data.storage import create_storage
        storage = create_storage('sqlite')

        # 获取最近两个交易日的价格
        query = """
        SELECT close, date FROM stock_prices
        WHERE symbol = ?
        ORDER BY date DESC
        LIMIT 2
        """
        results = storage.cursor.execute(query, (symbol,)).fetchall()

        if len(results) >= 2:
            current_price = results[0][0]  # 今天的收盘价
            previous_price = results[1][0]  # 昨天的收盘价
            daily_change = (current_price - previous_price) * shares
            return daily_change
        else:
            return 0.0
    except Exception:
        return 0.0


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
            symbol=args.symbol.upper(),
            quantity=args.quantity,
            price=args.price,
            transaction_date=args.date,
            external_id=args.external_id,
            notes=args.notes
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
                print("\n批次分配明细:")
                print(f"{'批次ID':>8} {'卖出数量':>12} {'成本基础':>12} {'已实现盈亏':>15}")
                print("-" * 70)
                total_realized = 0.0
                for alloc in allocations:
                    print(f"{alloc.lot_id:>8} {alloc.quantity_sold:>12.4f} {svc.config.format_price(alloc.cost_basis):>12} "
                          f"{svc.config.format_amount(alloc.realized_pnl):>15}")
                    total_realized += alloc.realized_pnl
                print("-" * 70)
                print(f"{'总计':>8} {args.quantity:>12.4f} {'':>12} {svc.config.format_amount(total_realized):>15}")
                
        
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
    positions = svc.get_current_positions()
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
            calc.calculate_daily_pnl(sym.upper(), args.date)
    else:
        # 对所有持仓计算
        calc.calculate_all_positions_pnl(args.date)
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
    calc.calculate_all_positions_pnl(today)
    storage.close()
    return 0


def cmd_portfolio(args: argparse.Namespace) -> int:
    setup_logging('INFO' if args.verbose else 'WARNING')
    storage = _storage_from_args(args)
    config = DEFAULT_TRADING_CONFIG
    portfolio = PortfolioService(storage, config)
    summary = portfolio.get_portfolio_summary(args.as_of_date)
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
            mv = p.get('market_value')
            mv_str = f"{mv:,.2f}" if mv is not None else "N/A"
            unreal = p.get('unrealized_pnl')
            unreal_str = f"{unreal:,.2f}" if unreal is not None else "N/A"
            print(
                f"  {p['symbol']:8s} qty={p['quantity']:,.4f} avg={p['avg_cost']:,.4f} "
                f"mv={mv_str} unreal={unreal_str}"
            )
    storage.close()
    return 0


def cmd_enhanced_portfolio(args: argparse.Namespace) -> int:
    """增强版投资组合分析"""
    setup_logging('INFO' if args.verbose else 'WARNING')
    storage = _storage_from_args(args)
    config = DEFAULT_TRADING_CONFIG
    portfolio = PortfolioService(storage, config)
    
    # 获取增强分析
    analysis = portfolio.get_enhanced_portfolio_analysis(args.as_of_date)
    
    # 打印中文格式的分析报告
    _print_enhanced_analysis_chinese(analysis)
    
    storage.close()
    return 0


def display_width(text):
    """计算文本的实际显示宽度（中文=2，英文=1）"""
    width = 0
    for char in text:
        if ord(char) > 127:  # 中文字符
            width += 2
        else:  # 英文字符
            width += 1
    return width

def pad_to_width(text, target_width):
    """按显示宽度填充到指定宽度"""
    current_width = display_width(text)
    padding = target_width - current_width
    return text + ' ' * max(0, padding)

def _print_enhanced_analysis_chinese(analysis: dict):
    """打印中文格式的增强投资组合分析"""
    basic = analysis['basic_summary']
    
    print("="*80)
    print(f"📊 增强版投资组合分析 ({analysis['analysis_date']})")
    print("="*80)
    
    # 基础摘要
    budget_total = 1000000  # 100万预算
    remaining_cash = budget_total - basic['total_cost']
    
    print("\n📈 组合概览:")
    print(f"  投资预算:   ${budget_total:,.2f}")
    print(f"  已投资:     ${basic['total_cost']:,.2f}")
    print(f"  剩余现金:   ${remaining_cash:,.2f}")
    print(f"  当前市值:   ${basic['total_market_value']:,.2f}")
    print(f"  总盈亏:     ${basic['total_unrealized_pnl']:,.2f}")
    print(f"  收益率:     {basic['total_unrealized_pnl_pct']:.2f}%")
    print(f"  持仓数量:   {basic['total_positions']} 只")
    
    # 专业格式的持仓分析表格
    print("\n🏢 按公司类型持仓分解")
    print()
    sector_analysis = analysis['sector_analysis']
    
    if 'etf_analysis' in sector_analysis:
        etf = sector_analysis['etf_analysis']
        etf_pct = (etf['total_cost'] / basic['total_cost'] * 100) if basic['total_cost'] > 0 else 0
        print(f"  📊 ETF基金 (交易所交易基金) - 占投资组合 {etf_pct:.1f}%")
        print()
        ticker_header = pad_to_width('代码', 8)
        name_header = pad_to_width('名称', 30)
        shares_header = pad_to_width('股数', 7)
        cost_header = pad_to_width('成本基础', 10)
        value_header = pad_to_width('当前市值', 10)
        daily_pnl_header = pad_to_width('当天盈亏', 10)
        pnl_header = pad_to_width('总盈亏', 10)
        return_header = pad_to_width('收益率', 7)
        weight_header = pad_to_width('投资额', 7)
        print(f"  | {ticker_header} | {name_header} | {shares_header} | {cost_header} | {value_header} | {daily_pnl_header} | {pnl_header} | {return_header} | {weight_header} |")
        print("  |----------|--------------------------------|---------|------------|------------|------------|------------|---------|---------|")
        
        etf_total_shares = 0
        etf_total_cost = 0
        etf_total_value = 0
        etf_total_pnl = 0
        etf_total_daily_pnl = 0

        for pos in etf['positions']:
            shares = pos.get('quantity', 0)
            cost_basis = pos.get('total_cost', 0)
            market_value = pos.get('market_value', 0)
            pnl = pos.get('unrealized_pnl', 0)
            pnl_pct = pos.get('unrealized_pnl_pct', 0)
            name = pos.get('category', pos['symbol'])[:30]

            # 计算当天盈亏
            daily_pnl = get_daily_pnl(pos['symbol'], shares)

            etf_total_shares += shares
            etf_total_cost += cost_basis
            # Only add if market_value and pnl are not None
            if market_value is not None:
                etf_total_value += market_value
            if pnl is not None:
                etf_total_pnl += pnl
            etf_total_daily_pnl += daily_pnl
            
            # 格式化当天盈亏
            if daily_pnl >= 0:
                daily_pnl_str = f"$+{daily_pnl:8,.0f}"
            else:
                daily_pnl_str = f"$-{abs(daily_pnl):8,.0f}"

            # 格式化总盈亏
            if pnl >= 0:
                pnl_str = f"$+{pnl:8,.0f}"
            else:
                pnl_str = f"$-{abs(pnl):8.0f}"

            # 格式化Return
            if pnl_pct >= 0:
                return_str = f"+{pnl_pct:.2f}%"
            else:
                return_str = f"{pnl_pct:.2f}%"

            # 计算占100万预算的百分比
            budget_total = 1000000
            weight_pct = (cost_basis / budget_total * 100)
            weight_str = f"{weight_pct:.2f}%"

            padded_name = pad_to_width(name, 30)
            print(f"  | {pos['symbol']:8s} | {padded_name} | {shares:7.0f} | ${cost_basis:9,.0f} | ${market_value:9,.0f} | {daily_pnl_str:>9s} | {pnl_str:>9s} | {return_str:>7s} | {weight_str:>7s} |")
        
        # ETF小计
        etf_total_return = (etf_total_pnl / etf_total_cost * 100) if etf_total_cost > 0 else 0

        # 格式化ETF总当天盈亏
        if etf_total_daily_pnl >= 0:
            etf_daily_pnl_str = f"$+{etf_total_daily_pnl:8,.0f}"
        else:
            etf_daily_pnl_str = f"$-{abs(etf_total_daily_pnl):8,.0f}"

        # 格式化ETF总盈亏
        if etf_total_pnl >= 0:
            etf_pnl_str = f"$+{etf_total_pnl:8,.0f}"
        else:
            etf_pnl_str = f"$-{abs(etf_total_pnl):8,.0f}"

        if etf_total_return >= 0:
            etf_return_str = f"+{etf_total_return:.2f}%"
        else:
            etf_return_str = f"{etf_total_return:.2f}%"

        # ETF小计占100万预算的百分比
        budget_total = 1000000
        etf_weight_pct = (etf_total_cost / budget_total * 100)
        etf_weight_str = f"{etf_weight_pct:.2f}%"

        print("  |----------|--------------------------------|---------|------------|------------|------------|------------|---------|---------|")
        subtotal_name = pad_to_width('', 30)
        print(f"  |   总计   | {subtotal_name} | {etf_total_shares:7.0f} | ${etf_total_cost:9,.0f} | ${etf_total_value:9,.0f} | {etf_daily_pnl_str:>8s} | {etf_pnl_str:>8s} | {etf_return_str:>7s} | {etf_weight_str:>7s} |")
    
    if 'stock_analysis' in sector_analysis:
        stock = sector_analysis['stock_analysis']
        stock_pct = (stock['total_cost'] / basic['total_cost'] * 100) if basic['total_cost'] > 0 else 0
        print()
        print(f"  🏭 个股投资 - 占投资组合 {stock_pct:.1f}%")
        print()
        stock_ticker_header = pad_to_width('代码', 8)
        company_header = pad_to_width('公司', 19)
        sector_header = pad_to_width('行业', 8)
        stock_shares_header = pad_to_width('股数', 7)
        stock_cost_header = pad_to_width('成本基础', 10)
        stock_value_header = pad_to_width('当前市值', 10)
        stock_daily_pnl_header = pad_to_width('当天盈亏', 10)
        stock_pnl_header = pad_to_width('总盈亏', 10)
        stock_return_header = pad_to_width('收益率', 7)
        stock_weight_header = pad_to_width('投资额', 7)
        print(f"  | {stock_ticker_header} | {company_header} | {sector_header} | {stock_shares_header} | {stock_cost_header} | {stock_value_header} | {stock_daily_pnl_header} | {stock_pnl_header} | {stock_return_header} | {stock_weight_header} |")
        print("  |----------|---------------------|----------|---------|------------|------------|------------|------------|---------|---------|")

        stock_total_shares = 0
        stock_total_cost = 0
        stock_total_value = 0
        stock_total_pnl = 0
        stock_total_daily_pnl = 0
        
        for pos in stock['positions']:
            shares = pos.get('quantity', 0)
            cost_basis = pos.get('total_cost', 0)
            market_value = pos.get('market_value', 0)
            pnl = pos.get('unrealized_pnl', 0)
            pnl_pct = pos.get('unrealized_pnl_pct', 0)
            company = pos.get('category', pos['symbol'])[:19]
            sector = pos.get('sector', '未知')[:8]

            # 计算当天盈亏
            daily_pnl = get_daily_pnl(pos['symbol'], shares)

            stock_total_shares += shares
            stock_total_cost += cost_basis
            # Only add if market_value and pnl are not None
            if market_value is not None:
                stock_total_value += market_value
            if pnl is not None:
                stock_total_pnl += pnl
            stock_total_daily_pnl += daily_pnl

            # 格式化当天盈亏
            if daily_pnl >= 0:
                daily_pnl_str = f"$+{daily_pnl:8,.0f}"
            else:
                daily_pnl_str = f"$-{abs(daily_pnl):8,.0f}"

            # 格式化总盈亏
            if pnl is not None:
                if pnl >= 0:
                    pnl_str = f"$+{pnl:8,.0f}"
                else:
                    pnl_str = f"$-{abs(pnl):8,.0f}"
            else:
                pnl_str = "N/A"

            # 格式化Return
            if pnl_pct is not None:
                if pnl_pct >= 0:
                    return_str = f"+{pnl_pct:.2f}%"
                else:
                    return_str = f"{pnl_pct:.2f}%"
            else:
                return_str = "N/A"

            # 计算占100万预算的百分比
            budget_total = 1000000
            stock_weight_pct = (cost_basis / budget_total * 100)
            stock_weight_str = f"{stock_weight_pct:.2f}%"

            # 格式化市值
            if market_value is not None:
                mv_str = f"${market_value:9,.0f}"
            else:
                mv_str = "N/A"

            padded_company = pad_to_width(company, 19)
            padded_sector = pad_to_width(sector, 8)
            print(f"  | {pos['symbol']:8s} | {padded_company} | {padded_sector} | {shares:7.0f} | ${cost_basis:9,.0f} | {mv_str:>10s} | {daily_pnl_str:>8s} | {pnl_str:>9s} | {return_str:>7s} | {stock_weight_str:>7s} |")
        
        # 个股小计
        stock_total_return = (stock_total_pnl / stock_total_cost * 100) if stock_total_cost > 0 else 0

        # 格式化个股总当天盈亏
        if stock_total_daily_pnl >= 0:
            stock_daily_pnl_str = f"$+{stock_total_daily_pnl:8,.0f}"
        else:
            stock_daily_pnl_str = f"$-{abs(stock_total_daily_pnl):8,.0f}"

        # 格式化个股总盈亏
        if stock_total_pnl >= 0:
            stock_pnl_str = f"$+{stock_total_pnl:8,.0f}"
        else:
            stock_pnl_str = f"$-{abs(stock_total_pnl):8,.0f}"

        if stock_total_return >= 0:
            stock_return_str = f"+{stock_total_return:.2f}%"
        else:
            stock_return_str = f"{stock_total_return:.2f}%"

        # 个股小计占100万预算的百分比
        budget_total = 1000000
        stock_subtotal_weight_pct = (stock_total_cost / budget_total * 100)
        stock_subtotal_weight_str = f"{stock_subtotal_weight_pct:.2f}%"

        print("  |----------|---------------------|----------|---------|------------|------------|------------|------------|---------|---------|")
        subtotal_company = pad_to_width('', 19)
        subtotal_sector = pad_to_width('', 8) 
        print(f"  |   总计   | {subtotal_company} | {subtotal_sector} | {stock_total_shares:7.0f} | ${stock_total_cost:9,.0f} | ${stock_total_value:9,.0f} | {stock_daily_pnl_str:>8s} | {stock_pnl_str:>7s} | {stock_return_str:>7s} | {stock_subtotal_weight_str:>7s} |")
    
    # 平台分析
    print("\n🏦 平台分布:")
    platform_analysis = analysis['platform_analysis']
    for platform, data in platform_analysis.items():
        if isinstance(data, dict) and 'total_investment' in data:
            pnl_symbol = "📈" if data['pnl'] >= 0 else "📉"
            print(f"  {platform}平台:")
            print(f"    投资: ${data['total_investment']:,.2f}")
            print(f"    市值: ${data['current_value']:,.2f}")
            print(f"    盈亏: ${data['pnl']:,.2f} ({data['return_pct']:+.2f}%) {pnl_symbol}")
            print(f"    股票: {', '.join(data['symbols'])}")
    
    # 风险分析与集中度
    print("\n⚖️ 详细风险分析:")
    risk = analysis['risk_metrics']
    if 'message' not in risk:
        print(f"  🎯 集中度分析:")
        print(f"    最大持仓: {risk['max_position']['symbol']} ({risk['max_position']['concentration']:.1%})")
        print(f"    前三大占比: {risk['top3_concentration']:.1%}")
        print(f"    持仓数量: {risk['position_count']}只 (分散化程度: {risk['diversification_score']})")
        
        if 'sector_analysis' in risk:
            sector_info = risk['sector_analysis']
            print(f"    最大行业: {sector_info['max_sector']} ({sector_info['max_sector_concentration']:.1%})")
            print(f"    行业分布: {sector_info['sector_count']}个行业")
        
        if 'volatility_analysis' in risk:
            vol_info = risk['volatility_analysis']
            print(f"    波动性评分: {vol_info['portfolio_volatility_score']:.2f} (风险级别: {vol_info['volatility_level']})")
        
        print(f"    综合风险等级: {risk['risk_level']}")
        
        # 风险评级颜色
        risk_color = "🟢" if risk['risk_level'] == '低' else "🟡" if risk['risk_level'] == '中' else "🔴"
        print(f"    风险状态: {risk_color} {risk['risk_level']}风险投资组合")
    
    # 表现分析
    print("\n📊 表现分析:")
    perf = analysis['performance_analysis']
    if 'message' not in perf:
        print(f"  盈利股票: {perf['winners']}只")
        print(f"  亏损股票: {perf['losers']}只")
        print(f"  胜率:     {perf['winner_ratio']:.1%}")
        print(f"  最佳:     {perf['best_performer']['symbol']} (+{perf['best_performer']['return_pct']:.2f}%)")
        print(f"  最差:     {perf['worst_performer']['symbol']} ({perf['worst_performer']['return_pct']:+.2f}%)")
    
    # 股价表现专业表格
    if 'historical_performance' in analysis:
        hist_perf = analysis['historical_performance']
        if hist_perf:
            # 动态获取日期范围
            from datetime import datetime
            today = datetime.now().strftime('%b %-d')
            print(f"\n📅 股价表现分析 (9月5日 - {today}, 2025)")
            print()
            stock_header = pad_to_width('股票', 5)
            date_header = pad_to_width('入场日期', 13)
            entry_header = pad_to_width('入场价格', 12)
            cost_header = pad_to_width('成本基础', 12)
            current_header = pad_to_width('当前价格', 12)
            change_header = pad_to_width('价格变化', 12)
            print(f"  | {stock_header} | {date_header} | {entry_header} | {cost_header} | {current_header} | {change_header} |")
            print("  |-------|---------------|--------------|--------------|--------------|--------------|")
            
            # 按涨幅排序（从高到低）
            sorted_symbols = sorted(hist_perf.items(), key=lambda x: x[1].get('price_change_pct', 0), reverse=True)

            # 获取持仓数据以便获取成本基础（总投入金额）
            positions_data = {}
            if 'basic_summary' in analysis and 'positions' in analysis['basic_summary']:
                for pos in analysis['basic_summary']['positions']:
                    positions_data[pos['symbol']] = pos.get('total_cost', 0)

            for symbol, data in sorted_symbols:
                entry_date = data.get('entry_date', '未知')
                first_price = data.get('first_price', 0)
                current_price = data.get('current_price', 0)
                price_change = data.get('price_change_pct', 0) / 100

                # 获取成本基础（总投入金额）
                total_cost = positions_data.get(symbol, 0)

                # 格式化日期 (从 YYYY-MM-DD 转换为 Sep 5 格式)
                if entry_date and entry_date != '未知':
                    try:
                        from datetime import datetime
                        date_obj = datetime.strptime(entry_date, '%Y-%m-%d')
                        formatted_date = date_obj.strftime('%Y-%m-%d')
                    except:
                        formatted_date = entry_date
                else:
                    formatted_date = '未知'

                # 确定趋势符号和颜色
                trend_symbol = "🟢" if price_change >= 0 else "🔴"
                price_change_sign = "+" if price_change >= 0 else ""

                entry_price_display = f"${first_price:11,.2f}"
                cost_basis_display = f"${total_cost:11,.0f}"

                padded_date = pad_to_width(formatted_date, 13)
                current_price_str = f"${current_price:11,.2f}"
                padded_current = pad_to_width(current_price_str, 12)
                price_change_str = f"{trend_symbol}  {price_change_sign}{price_change:.2%}"
                padded_change = pad_to_width(price_change_str, 12)
                print(f"  | {symbol:5s} | {padded_date} | {entry_price_display:12s} | {cost_basis_display:12s} | {padded_current} | {padded_change} |")

    # 投资策略洞察
    if 'strategy_insights' in analysis:
        insights = analysis['strategy_insights']
        print(f"\n🎯 投资策略洞察:")
        print(f"  投资组合评级: {insights.get('grade', 'N/A')} ({insights.get('overall_score', 0):.0f}分)")
        print(f"  总体评价: {insights.get('summary', '无评价')}")
        
        print(f"\n  ✅ 投资组合优势:")
        for strength in insights.get('strengths', []):
            print(f"    • {strength}")
        
        print(f"\n  ⚠️  需要改进:")
        for improvement in insights.get('improvements', []):
            print(f"    • {improvement}")
        
        print(f"\n  📋 具体建议:")
        for rec in insights.get('recommendations', []):
            print(f"    • {rec}")

    # 原有投资建议
    print("\n💡 系统建议:")
    for i, rec in enumerate(analysis['recommendations'], 1):
        print(f"  {i}. {rec}")
    
    print("\n" + "="*80)


def cmd_tax_report(args: argparse.Namespace) -> int:
    """生成税务申报所需的成本基础明细"""
    setup_logging('INFO' if args.verbose else 'WARNING')
    storage = _storage_from_args(args)
    config = DEFAULT_TRADING_CONFIG
    svc = LotTransactionService(storage, config)
    
    try:
        # 获取用户的所有卖出分配记录
        allocations = svc.get_sale_allocations()
        
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
        lots = svc.get_position_lots(args.symbol.upper() if args.symbol else None)
        
        if not lots:
            print("(no position lots for simulation)")
            storage.close()
            return 0
        
        print("=== REBALANCE SIMULATION ===")
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
    lots = svc.get_position_lots(symbol)
    
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
    allocations = svc.get_sale_allocations(symbol)
    
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
    pos.add_argument('-v', '--verbose', action='store_true')
    pos.set_defaults(func=cmd_positions)

    # calculate-pnl
    calc = sub.add_parser('calculate-pnl', help='计算指定日期的盈亏')
    calc.add_argument('--date', required=True, help='YYYY-MM-DD')
    calc.add_argument('--symbols', nargs='+', help='可选，指定股票列表')
    calc.add_argument('--price-source', choices=['adj_close', 'close'], default='adj_close')
    calc.add_argument('--only-trading-days', action='store_true', help='只按交易日计算')
    calc.add_argument('-v', '--verbose', action='store_true')
    calc.set_defaults(func=cmd_calculate_pnl)

    # batch-calculate
    bcalc = sub.add_parser('batch-calculate', help='批量计算历史盈亏')
    bcalc.add_argument('--start-date', required=True)
    bcalc.add_argument('--end-date', required=True)
    bcalc.add_argument('--symbols', nargs='+', help='可选，指定股票列表')
    bcalc.add_argument('--price-source', choices=['adj_close', 'close'], default='adj_close')
    bcalc.add_argument('--only-trading-days', action='store_true', help='只按交易日计算')
    bcalc.add_argument('-v', '--verbose', action='store_true')
    bcalc.set_defaults(func=cmd_batch_calculate)

    # daily
    daily = sub.add_parser('daily', help='计算今日所有持仓的盈亏（便于 cron 调度）')
    daily.add_argument('--price-source', choices=['adj_close', 'close'], default='adj_close')
    daily.add_argument('--only-trading-days', action='store_true', help='只按交易日计算')
    daily.add_argument('-v', '--verbose', action='store_true')
    daily.set_defaults(func=cmd_daily)

    # portfolio
    port = sub.add_parser('portfolio', help='查看投资组合摘要')
    port.add_argument('--as-of-date', help='YYYY-MM-DD，默认今天')
    port.add_argument('-v', '--verbose', action='store_true')
    port.set_defaults(func=cmd_portfolio)

    # enhanced-portfolio
    eport = sub.add_parser('enhanced-portfolio', help='增强版投资组合分析（中文）')
    eport.add_argument('--as-of-date', help='YYYY-MM-DD，默认今天')
    eport.add_argument('-v', '--verbose', action='store_true')
    eport.set_defaults(func=cmd_enhanced_portfolio)

    # tax-report - 新增高级功能
    tax = sub.add_parser('tax-report', help='生成税务申报所需的成本基础明细')
    tax.add_argument('--start-date', help='开始日期 YYYY-MM-DD')
    tax.add_argument('--end-date', help='结束日期 YYYY-MM-DD')
    tax.add_argument('-v', '--verbose', action='store_true')
    tax.set_defaults(func=cmd_tax_report)

    # rebalance-simulate - 新增高级功能
    rebalance = sub.add_parser('rebalance-simulate', help='模拟不同成本基础方法的税负影响')
    rebalance.add_argument('-s', '--symbol', help='可选，指定股票代码')
    rebalance.add_argument('-q', '--quantity', type=float, required=True, help='模拟卖出数量')
    rebalance.add_argument('-p', '--price', type=float, required=True, help='模拟卖出价格')
    rebalance.add_argument('-v', '--verbose', action='store_true')
    rebalance.set_defaults(func=cmd_rebalance_simulate)

    # lots - 查看持仓批次
    lots = sub.add_parser('lots', help='查看持仓批次')
    lots.add_argument('-s', '--symbol', help='可选，指定股票代码')
    lots.add_argument('-v', '--verbose', action='store_true')
    lots.set_defaults(func=cmd_lots)

    # sales - 查看卖出分配记录
    sales = sub.add_parser('sales', help='查看卖出分配记录')
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
