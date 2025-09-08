import os
import pandas as pd

from analysis_service.pipeline.context import AnalysisContext
from analysis_service.operators.fin_ratios import FinancialRatioOperator
from analysis_service.operators.fin_health import FinancialHealthOperator


class DummyCfg:
    pass


def make_price_df():
    idx = pd.date_range("2023-01-01", periods=10, freq="D")
    close = [100.0 + i for i in range(10)]
    df = pd.DataFrame({
        'Open': close,
        'High': [c + 1 for c in close],
        'Low': [c - 1 for c in close],
        'Close': close,
        'Volume': [1000] * 10,
    }, index=idx)
    return df


def setup_fin_db(tmp_path):
    db_path = os.path.join(tmp_path, 'fin_test.db')
    from data_service.database import StockDatabase
    db = StockDatabase(db_path)
    # Insert minimal financial statements for symbol ZZZ
    statements = {
        'income_statement': {
            'periods': ['2023-12-31', '2022-12-31'],
            'items': {
                'Total Revenue': [1_000_000, 900_000],
                'Net Income': [100_000, 80_000],
            }
        },
        'balance_sheet': {
            'periods': ['2023-12-31', '2022-12-31'],
            'items': {
                'Total Stockholder Equity': [500_000, 480_000],
                'Total Assets': [2_000_000, 1_800_000],
                'Total Liab': [800_000, 750_000],
                'Common Shares Outstanding': [50_000, 50_000],
            }
        }
    }
    db.store_financial_statements('ZZZ', {'financial_statements': statements})
    db.close()
    return db_path


def test_financial_ratio_and_health(tmp_path):
    db_path = setup_fin_db(tmp_path)
    ctx = AnalysisContext(symbol='ZZZ', data=make_price_df(), config=DummyCfg())
    fin_op = FinancialRatioOperator(db_path=db_path)
    ratios = fin_op.run(ctx)
    assert 'net_profit_margin' in ratios
    assert 'roe' in ratios
    # feed into health operator
    ctx.extras['fin_ratios'] = ratios
    health = FinancialHealthOperator().run(ctx)
    assert 'health_score' in health and 'grade' in health
