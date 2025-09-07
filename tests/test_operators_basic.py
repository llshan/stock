import pandas as pd

from analyzer.pipeline.context import AnalysisContext
from analyzer.operators.ma import MovingAverageOperator
from analyzer.operators.rsi import RSIOperator
from analyzer.operators.drop_alert import DropAlertOperator


class DummyCfg:
    class technical:
        ma_windows = [5, 10]
        rsi_period = 14
        rsi_overbought = 70
        rsi_oversold = 30


def make_price_df(n=50, start=100.0, step=0.5):
    idx = pd.date_range("2022-01-01", periods=n, freq="D")
    prices = [start + i * step for i in range(n)]
    df = pd.DataFrame({
        'Open': prices,
        'High': [p + 1 for p in prices],
        'Low': [p - 1 for p in prices],
        'Close': prices,
        'Volume': [1000] * n,
    }, index=idx)
    return df


def test_ma_operator():
    df = make_price_df()
    ctx = AnalysisContext(symbol='TEST', data=df, config=DummyCfg())
    op = MovingAverageOperator()
    res = op.run(ctx)
    assert 'ma_5' in res and 'ma_10' in res


def test_rsi_operator():
    df = make_price_df()
    ctx = AnalysisContext(symbol='TEST', data=df, config=DummyCfg())
    # ensure MA runs first to populate extras path (not required but ok)
    MovingAverageOperator().run(ctx)
    res = RSIOperator().run(ctx)
    assert 'rsi' in res and 'signal' in res


def test_drop_alert_operator():
    # Create series with a recent drop > 15%
    df = make_price_df()
    df.iloc[-1, df.columns.get_loc('Close')] = df['Close'].iloc[-2] * 0.7
    ctx = AnalysisContext(symbol='TEST', data=df, config=DummyCfg())
    res = DropAlertOperator(days=1, threshold_percent=15.0).run(ctx)
    assert res.get('is_alert') is True

