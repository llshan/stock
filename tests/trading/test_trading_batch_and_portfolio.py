#!/usr/bin/env python3
import math

from stock_analysis.data.storage import SQLiteStorage
from stock_analysis.data.models.price_models import PriceData
from stock_analysis.trading.services.transaction_service import TransactionService
from stock_analysis.trading.calculators.pnl_calculator import PnLCalculator
from stock_analysis.trading.services.portfolio_service import PortfolioService
from stock_analysis.trading.config import TradingConfig


def seed_prices(storage: SQLiteStorage, symbol: str, dates_prices: list[tuple[str, float]]):
    dates = [d for d, _ in dates_prices]
    closes = [p for _, p in dates_prices]
    price_data = PriceData(
        dates=dates,
        open=closes,
        high=closes,
        low=closes,
        close=closes,
        volume=[1] * len(dates),
        adj_close=closes,
    )
    storage.ensure_stock_exists(symbol)
    storage._store_price_data_batch(symbol, price_data)


def test_batch_calculate_trading_vs_natural_days():
    storage = SQLiteStorage(":memory:")
    try:
        user_id = "u3"
        symbol = "IBM"
        # 价格在周五与下周一，范围包含周末
        seed_prices(storage, symbol, [("2024-01-05", 100.0), ("2024-01-08", 102.0)])

        svc = TransactionService(storage)
        svc.record_buy_transaction(user_id, symbol, quantity=10, price=99.0, transaction_date="2024-01-04")

        # only_trading_days = True → 仅两天（1/05, 1/08）
        calc = PnLCalculator(storage=storage, only_trading_days=True)
        res_trading = calc.batch_calculate_historical_pnl(user_id, "2024-01-05", "2024-01-08", [symbol])
        assert res_trading['total_days'] == 2

        # only_trading_days = False → 自然日四天（5,6,7,8）
        calc2 = PnLCalculator(storage=storage, only_trading_days=False)
        res_natural = calc2.batch_calculate_historical_pnl(user_id, "2024-01-05", "2024-01-08", [symbol])
        assert res_natural['total_days'] == 4
        # 自然日模式会对周末进行回填计算，记录数应不少于交易日模式
        assert res_natural['calculated_records'] >= res_trading['calculated_records']
    finally:
        storage.close()


def test_portfolio_summary_values():
    storage = SQLiteStorage(":memory:")
    try:
        user_id = "u4"
        symbol = "AAPL"
        # as_of_date 价格150
        seed_prices(storage, symbol, [("2024-01-10", 150.0)])
        svc = TransactionService(storage)
        svc.record_buy_transaction(user_id, symbol, quantity=10, price=100.0, transaction_date="2024-01-09")

        portfolio = PortfolioService(storage)
        summary = portfolio.get_portfolio_summary(user_id, as_of_date="2024-01-10")

        assert summary['total_positions'] == 1
        assert math.isclose(summary['total_cost'], 1000.0, rel_tol=1e-6)
        assert math.isclose(summary['total_market_value'], 1500.0, rel_tol=1e-6)
        assert math.isclose(summary['total_unrealized_pnl'], 500.0, rel_tol=1e-6)
    finally:
        storage.close()


def test_transaction_validation_excessive_commission_raises():
    storage = SQLiteStorage(":memory:")
    try:
        user_id = "u5"
        symbol = "TSLA"
        seed_prices(storage, symbol, [("2024-01-10", 200.0)])
        # 配置佣金上限1%
        cfg = TradingConfig(max_commission_rate=0.01)
        svc = TransactionService(storage, config=cfg)

        # 交易金额 2000，上限佣金20，尝试传入 30 应触发异常
        try:
            svc.record_buy_transaction(user_id, symbol, quantity=10, price=200.0, transaction_date="2024-01-10", commission=30.0)
        except ValueError as e:
            assert "佣金" in str(e)
        else:
            assert False, "expected ValueError for excessive commission"
    finally:
        storage.close()


def test_batch_calculate_symbols_filter():
    storage = SQLiteStorage(":memory:")
    try:
        user_id = "u6"
        s1, s2 = "AAA", "BBB"
        seed_prices(storage, s1, [("2024-02-01", 10.0), ("2024-02-02", 11.0)])
        seed_prices(storage, s2, [("2024-02-01", 20.0), ("2024-02-02", 21.0)])
        svc = TransactionService(storage)
        svc.record_buy_transaction(user_id, s1, quantity=1, price=10.0, transaction_date="2024-02-01")
        svc.record_buy_transaction(user_id, s2, quantity=1, price=20.0, transaction_date="2024-02-01")

        calc = PnLCalculator(storage=storage)
        res = calc.batch_calculate_historical_pnl(user_id, "2024-02-01", "2024-02-02", symbols=[s1])
        assert res['symbols_processed'] == 1

        # 检查 daily_pnl 仅对 s1 写入
        rows_s1 = storage.get_daily_pnl(user_id, s1, "2024-02-01", "2024-02-02")
        rows_s2 = storage.get_daily_pnl(user_id, s2, "2024-02-01", "2024-02-02")
        assert len(rows_s1) > 0
        assert len(rows_s2) == 0
    finally:
        storage.close()

