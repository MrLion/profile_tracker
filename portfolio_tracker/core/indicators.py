"""
Pure technical indicator functions.
All take a DataFrame or Series, return a Series or scalar. No side effects.
"""

import pandas as pd
import numpy as np


def sma(df: pd.DataFrame, period: int, col: str = "Close") -> pd.Series:
    return df[col].rolling(window=period).mean()


def ema(df: pd.DataFrame, period: int, col: str = "Close") -> pd.Series:
    return df[col].ewm(span=period, adjust=False).mean()


def rsi(df: pd.DataFrame, period: int = 14, col: str = "Close") -> pd.Series:
    delta = df[col].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df['High']
    low = df['Low']
    close = df['Close'].shift(1)
    tr = pd.concat([high - low, (high - close).abs(), (low - close).abs()], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


def bollinger_bands(df: pd.DataFrame, period: int = 20, std_dev: float = 2.0,
                    col: str = "Close") -> dict:
    middle = sma(df, period, col)
    rolling_std = df[col].rolling(window=period).std()
    return {
        "upper": middle + (rolling_std * std_dev),
        "middle": middle,
        "lower": middle - (rolling_std * std_dev),
    }


def slope(series: pd.Series, lookback: int = 20) -> float | None:
    """Returns the slope direction: positive = rising, negative = falling."""
    if len(series) < lookback:
        return None
    current = series.iloc[-1]
    previous = series.iloc[-lookback]
    if pd.isna(current) or pd.isna(previous):
        return None
    return current - previous


def slope_is_rising(series: pd.Series, lookback: int = 20) -> bool | None:
    s = slope(series, lookback)
    if s is None:
        return None
    return bool(s > 0)


def sma_latest(df: pd.DataFrame, period: int, col: str = "Close") -> float | None:
    s = sma(df, period, col)
    if len(s) >= period and not pd.isna(s.iloc[-1]):
        return float(s.iloc[-1])
    return None


def ema_latest(df: pd.DataFrame, period: int, col: str = "Close") -> float | None:
    s = ema(df, period, col)
    if len(s) > 0 and not pd.isna(s.iloc[-1]):
        return float(s.iloc[-1])
    return None


def rsi_latest(df: pd.DataFrame, period: int = 14) -> float | None:
    s = rsi(df, period)
    if len(s) > 0 and not pd.isna(s.iloc[-1]):
        return float(s.iloc[-1])
    return None


def ma_stack(df: pd.DataFrame, price: float, periods: list[int]) -> dict:
    """Check if MAs are stacked in bullish order: price > shortest > ... > longest."""
    values = [price]
    labels = ["Price"]
    for p in sorted(periods):
        val = sma_latest(df, p)
        if val is not None:
            values.append(val)
            labels.append(f"{p}d")
    aligned = all(values[i] >= values[i + 1] for i in range(len(values) - 1))
    return {"aligned": aligned, "labels": labels, "values": values}


def pct_distance(price: float, level: float) -> float | None:
    if level is None or level == 0:
        return None
    return ((price - level) / level) * 100


def rate_of_change(df: pd.DataFrame, period: int, col: str = "Close") -> float | None:
    if len(df) < period + 1:
        return None
    current = df[col].iloc[-1]
    previous = df[col].iloc[-(period + 1)]
    if previous == 0:
        return None
    return ((current - previous) / previous) * 100
