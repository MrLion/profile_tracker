"""
Unit tests — run with: python -m pytest tests/ -v
Or without pytest:     python -m tests.test_all
"""

import sys
import os
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import indicators as ind
from strategies.weinstein import WeinsteinStrategy
from strategies.momentum import MomentumStrategy
from core.portfolio import Position


def _make_df(prices: list[float]) -> pd.DataFrame:
    """Helper: create a minimal OHLCV DataFrame from a list of close prices."""
    n = len(prices)
    dates = pd.date_range(start="2020-01-02", periods=n, freq="B")
    return pd.DataFrame({
        "Open": prices,
        "High": [p * 1.01 for p in prices],
        "Low": [p * 0.99 for p in prices],
        "Close": prices,
        "Volume": [1000000] * n,
    }, index=dates)


def test_sma():
    df = _make_df([10, 20, 30, 40, 50])
    result = ind.sma(df, 3)
    assert abs(result.iloc[-1] - 40.0) < 0.01, f"Expected 40.0, got {result.iloc[-1]}"
    print("  ✅ test_sma passed")


def test_sma_latest():
    df = _make_df([10, 20, 30, 40, 50])
    val = ind.sma_latest(df, 3)
    assert val is not None
    assert abs(val - 40.0) < 0.01
    print("  ✅ test_sma_latest passed")


def test_sma_latest_insufficient():
    df = _make_df([10, 20])
    val = ind.sma_latest(df, 50)
    assert val is None
    print("  ✅ test_sma_latest_insufficient passed")


def test_rsi():
    prices = list(range(100, 150)) + list(range(150, 130, -1))
    df = _make_df(prices)
    val = ind.rsi_latest(df, 14)
    assert val is not None
    assert 0 <= val <= 100, f"RSI out of range: {val}"
    print(f"  ✅ test_rsi passed (RSI={val:.1f})")


def test_rate_of_change():
    df = _make_df([100, 110, 120, 130, 140])
    roc = ind.rate_of_change(df, 4)
    assert roc is not None
    assert abs(roc - 40.0) < 0.01
    print("  ✅ test_rate_of_change passed")


def test_pct_distance():
    assert abs(ind.pct_distance(110, 100) - 10.0) < 0.01
    assert abs(ind.pct_distance(90, 100) - (-10.0)) < 0.01
    assert ind.pct_distance(100, None) is None
    print("  ✅ test_pct_distance passed")


def test_ma_stack_aligned():
    # Prices consistently rising → MAs should be bullish
    prices = list(range(50, 260))  # 210 data points, rising
    df = _make_df(prices)
    result = ind.ma_stack(df, prices[-1], [10, 21, 50, 200])
    assert result["aligned"] is True
    print("  ✅ test_ma_stack_aligned passed")


def test_slope_is_rising():
    prices = list(range(100, 300))  # 200 points, steadily rising
    df = _make_df(prices)
    series = ind.sma(df, 50)
    assert ind.slope_is_rising(series, 20) is True
    print("  ✅ test_slope_is_rising passed")


def test_weinstein_stage2a():
    """Rising prices well above all MAs → Stage 2A. No position = WATCH or BUY."""
    prices = list(range(50, 260))
    df = _make_df(prices)
    strategy = WeinsteinStrategy()
    signal = strategy.analyze("TEST", df)
    assert "2A" in signal.label, f"Expected Stage 2A, got {signal.label}"
    # No position passed → should be WATCH or BUY (not HOLD)
    assert "WATCH" in signal.action or "BUY" in signal.action, \
        f"Expected WATCH or BUY for no-position 2A, got {signal.action}"
    print(f"  ✅ test_weinstein_stage2a passed ({signal.label} → {signal.action})")


def test_weinstein_stage2a_hold():
    """Rising prices, WITH position → HOLD."""
    prices = list(range(50, 260))
    df = _make_df(prices)
    strategy = WeinsteinStrategy()
    fake_pos = Position(
        ticker="TEST", theme="Test", entry_price=100, current_price=259,
        shares=10, invested=1000, current_value=2590, pnl_dollars=1590,
        pnl_pct=159.0, weight=25.0,
    )
    signal = strategy.analyze("TEST", df, position=fake_pos)
    assert "2A" in signal.label, f"Expected Stage 2A, got {signal.label}"
    assert "HOLD" in signal.action, f"Expected HOLD for position in 2A, got {signal.action}"
    print(f"  ✅ test_weinstein_stage2a_hold passed ({signal.label} → {signal.action})")


def test_weinstein_no_position_not_hold():
    """Without a position, Stage 2A should never return HOLD — should be WATCH or BUY."""
    prices = list(range(50, 260))
    df = _make_df(prices)
    strategy = WeinsteinStrategy()
    signal = strategy.analyze("TEST_NO_POS", df, position=None)
    assert "HOLD" not in signal.action, \
        f"HOLD should only appear for existing positions, got {signal.action}"
    assert "WATCH" in signal.action or "BUY" in signal.action, \
        f"Expected WATCH or BUY for no-position, got {signal.action}"
    print(f"  ✅ test_weinstein_no_position_not_hold passed ({signal.action})")


def test_weinstein_watchlist_scan():
    """Watchlist scan should return BUY/WATCH for 2A stocks, None for Stage 4."""
    # Stage 2A stock
    prices_up = list(range(50, 260))
    df_up = _make_df(prices_up)
    strategy = WeinsteinStrategy()
    sig = strategy.scan_watchlist("WINNER", df_up)
    assert sig is not None, "Expected watchlist signal for Stage 2A stock"
    assert "WATCH" in sig.action or "BUY" in sig.action, \
        f"Expected WATCH/BUY, got {sig.action}"

    # Stage 4 stock
    prices_down = [100] * 150 + list(range(100, 70, -1))
    df_down = _make_df(prices_down)
    sig_down = strategy.scan_watchlist("LOSER", df_down)
    assert sig_down is None, f"Expected None for Stage 4 watchlist, got {sig_down}"

    print("  ✅ test_weinstein_watchlist_scan passed")


def test_weinstein_stage4():
    """Long flat period then decline → Stage 4 or 3→4."""
    prices = [100] * 150 + list(range(100, 70, -1))
    df = _make_df(prices)
    strategy = WeinsteinStrategy()
    signal = strategy.analyze("TEST", df)
    assert "4" in signal.label or "3" in signal.label or "SELL" in signal.action, \
        f"Expected Stage 3/4 or SELL, got {signal.label} / {signal.action}"
    print(f"  ✅ test_weinstein_stage4 passed ({signal.label})")


def test_momentum_strong():
    """Consistently rising prices → strong momentum."""
    prices = list(range(100, 260))
    df = _make_df(prices)
    strategy = MomentumStrategy()
    signal = strategy.analyze("TEST", df)
    score = signal.metrics.get("momentum_score")
    assert score is not None and score > 50, f"Expected strong momentum, got {score}"
    print(f"  ✅ test_momentum_strong passed (score={score:.0f})")


def test_momentum_negative():
    """Declining prices → negative momentum."""
    prices = list(range(260, 100, -1))
    df = _make_df(prices)
    strategy = MomentumStrategy()
    signal = strategy.analyze("TEST", df)
    score = signal.metrics.get("momentum_score")
    assert score is not None and score < 50, f"Expected weak momentum, got {score}"
    print(f"  ✅ test_momentum_negative passed (score={score:.0f})")


def test_strategy_columns_and_rows():
    """Ensure columns() and row() return matching lengths."""
    prices = list(range(50, 260))
    df = _make_df(prices)

    for StrategyCls in [WeinsteinStrategy, MomentumStrategy]:
        strategy = StrategyCls()
        signal = strategy.analyze("TEST", df)
        cols = strategy.columns()
        row = strategy.row(signal)
        assert len(cols) == len(row), \
            f"{strategy.slug}: columns({len(cols)}) != row({len(row)})"
    print("  ✅ test_strategy_columns_and_rows passed")


if __name__ == "__main__":
    print("\n  Running tests...\n")
    test_sma()
    test_sma_latest()
    test_sma_latest_insufficient()
    test_rsi()
    test_rate_of_change()
    test_pct_distance()
    test_ma_stack_aligned()
    test_slope_is_rising()
    test_weinstein_stage2a()
    test_weinstein_stage2a_hold()
    test_weinstein_no_position_not_hold()
    test_weinstein_watchlist_scan()
    test_weinstein_stage4()
    test_momentum_strong()
    test_momentum_negative()
    test_strategy_columns_and_rows()
    print(f"\n  ✅ All 16 tests passed!\n")
