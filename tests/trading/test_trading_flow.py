#!/usr/bin/env python3
import math

from stock_analysis.data.storage import SQLiteStorage
from stock_analysis.data.models.price_models import PriceData
from stock_analysis.trading.services.transaction_service import TransactionService
from stock_analysis.trading.calculators.pnl_calculator import PnLCalculator


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


def test_realized_pnl_updates_daily_record():
    storage = SQLiteStorage(":memory:")
    try:
        symbol = "AAPL"
        # 价格：买入日150，次日160
        seed_prices(storage, symbol, [("2024-01-10", 150.0), ("2024-01-11", 160.0)])

        svc = TransactionService(storage)
        svc.record_buy_transaction(symbol, quantity=10, price=150.0, transaction_date="2024-01-10")

        # 先计算卖出当日的日度盈亏记录（未实现部分）
        calc = PnLCalculator(storage=storage)
        calc.calculate_daily_pnl(symbol, "2024-01-11")

        # 卖出5股@160，预期已实现盈亏 = (160-150)*5 = 50
        svc.record_sell_transaction(symbol, quantity=5, price=160.0, transaction_date="2024-01-11")

        records = storage.get_daily_pnl(symbol, "2024-01-11", "2024-01-11")
        assert records, "expected a daily_pnl record for the sell date"
        rec = records[0]
        assert math.isclose(float(rec.get("realized_pnl", 0.0)), 50.0, rel_tol=1e-6)
        # 百分比口径以 total_cost 归一（此处为 50 / 1500 * 100）
        expected_pct = 50.0 / float(rec["total_cost"]) * 100 if rec["total_cost"] else 0.0
        assert math.isclose(float(rec.get("realized_pnl_pct", 0.0)), expected_pct, rel_tol=1e-6)
    finally:
        storage.close()


def test_full_sell_removes_position():
    storage = SQLiteStorage(":memory:")
    try:
        symbol = "MSFT"
        seed_prices(storage, symbol, [("2024-01-10", 100.0), ("2024-01-11", 101.0)])
        svc = TransactionService(storage)
        svc.record_buy_transaction(symbol, quantity=10, price=100.0, transaction_date="2024-01-10")
        # 全部卖出
        svc.record_sell_transaction(symbol, quantity=10, price=101.0, transaction_date="2024-01-11")
        positions = svc.get_current_positions()
        assert all(p.symbol != symbol for p in positions), "position should be removed after full sell"
    finally:
        storage.close()

