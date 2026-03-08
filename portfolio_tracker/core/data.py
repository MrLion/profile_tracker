import yfinance as yf
import pandas as pd


class DataFetcher:
    """Fetches OHLCV data from Yahoo Finance with in-session caching."""

    def __init__(self):
        self._cache: dict[str, pd.DataFrame] = {}

    def fetch(self, ticker: str, period: str = "1y") -> pd.DataFrame | None:
        cache_key = f"{ticker}_{period}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period=period)
            if hist.empty:
                return None
            self._cache[cache_key] = hist
            return hist
        except Exception:
            return None

    def fetch_many(self, tickers: list[str], period: str = "1y",
                   verbose: bool = True) -> dict[str, pd.DataFrame]:
        results = {}
        for ticker in tickers:
            if verbose:
                print(f"    → {ticker}...", end=" ", flush=True)
            df = self.fetch(ticker, period)
            if df is not None:
                results[ticker] = df
                if verbose:
                    price = df['Close'].iloc[-1]
                    prev = df['Close'].iloc[-2] if len(df) > 1 else price
                    chg = ((price - prev) / prev) * 100
                    print(f"${price:.2f}  ({chg:+.1f}%)")
            else:
                if verbose:
                    print("FAILED")
        return results

    def get_latest_price(self, ticker: str) -> float | None:
        df = self.fetch(ticker)
        if df is not None and len(df) > 0:
            return float(df['Close'].iloc[-1])
        return None
