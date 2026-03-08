import pandas as pd

from strategies.base import Strategy, Signal
from core.portfolio import Position
from core import indicators as ind


class WeinsteinStrategy(Strategy):
    """
    Weinstein Stage Analysis.
    Classifies stocks into Stages 1-4 based on price vs 30-week SMA,
    MA alignment, and 30-week SMA slope.
    """

    @property
    def name(self) -> str:
        return "Weinstein Stage Analysis"

    @property
    def slug(self) -> str:
        return "weinstein"

    def analyze(self, ticker: str, df: pd.DataFrame,
                position: Position | None = None) -> Signal:
        price = float(df['Close'].iloc[-1])
        mas = self._compute_mas(df)
        stage, note = self._determine_stage(price, mas)
        action = self._stage_to_action(stage)
        severity = self._action_to_severity(action)
        stack = ind.ma_stack(df, price, [10, 21, 50, 200])

        return Signal(
            ticker=ticker,
            action=action,
            severity=severity,
            label=stage,
            detail=note,
            metrics={
                "price": price,
                "sma_10d": mas.get("10d"),
                "sma_21d": mas.get("21d"),
                "sma_50d": mas.get("50d"),
                "sma_200d": mas.get("200d"),
                "sma_30w": mas.get("30w"),
                "sma_30w_rising": mas.get("30w_rising"),
                "dist_50d": ind.pct_distance(price, mas.get("50d")),
                "dist_30w": ind.pct_distance(price, mas.get("30w")),
                "ma_aligned": stack["aligned"],
            },
        )

    def scan_watchlist(self, ticker: str, df: pd.DataFrame) -> Signal | None:
        signal = self.analyze(ticker, df)
        if "2" in signal.label:
            return signal
        return None

    def columns(self) -> list[str]:
        return ["Price", "50d SMA", "Dist 50d", "30w SMA",
                "Dist 30w", "30w Slope", "Stage", "MA Order", "Action"]

    def row(self, signal: Signal) -> list[str]:
        m = signal.metrics
        return [
            f"${m['price']:.2f}",
            f"${m['sma_50d']:.2f}" if m.get('sma_50d') else "N/A",
            f"{m['dist_50d']:+.1f}%" if m.get('dist_50d') is not None else "N/A",
            f"${m['sma_30w']:.2f}" if m.get('sma_30w') else "N/A",
            f"{m['dist_30w']:+.1f}%" if m.get('dist_30w') is not None else "N/A",
            "↑" if m.get('sma_30w_rising') else ("↓" if m.get('sma_30w_rising') is False else "?"),
            signal.label,
            "✅" if m.get('ma_aligned') else "❌",
            signal.action,
        ]

    # ── Private ──

    def _compute_mas(self, df: pd.DataFrame) -> dict:
        mas = {}
        for label, period in [("10d", 10), ("21d", 21), ("50d", 50), ("200d", 200)]:
            mas[label] = ind.sma_latest(df, period)
        mas["30w"] = ind.sma_latest(df, 150)  # 30 weeks ≈ 150 trading days

        sma_series = ind.sma(df, 150)
        mas["30w_rising"] = ind.slope_is_rising(sma_series, lookback=20)
        return mas

    def _determine_stage(self, price: float, mas: dict) -> tuple[str, str]:
        sma30w = mas.get("30w")
        sma50d = mas.get("50d")
        sma200d = mas.get("200d")
        rising = mas.get("30w_rising")

        if sma30w is None:
            return "N/A", "Insufficient data"

        if price > sma30w:
            if rising is False:
                return "1→2 ❓", "Above flattening 30w — early Stage 2 or late Stage 1"
            if sma50d and sma200d and sma50d > sma200d:
                if price > sma50d:
                    return "2A ⬆️", "Strong uptrend — above all MAs, 30w rising"
                else:
                    return "2B ⚠️", "Above 30w but below 50d — pullback or weakening"
            else:
                return "2B ⚠️", "Above 30w but MA alignment mixed"
        else:
            pct_below = ((sma30w - price) / sma30w) * 100
            if rising is True:
                return "2C ⚠️", f"Pullback below 30w (still rising) — {pct_below:.1f}% below"
            if pct_below > 10:
                return "4 ⬇️", f"Stage 4 decline — {pct_below:.1f}% below 30w SMA"
            else:
                return "3→4 ⚠️", f"Breaking down — {pct_below:.1f}% below 30w SMA"

    def _stage_to_action(self, stage: str) -> str:
        if "4" in stage or "3→4" in stage:
            return "🔴 SELL"
        if "2C" in stage:
            return "🟠 TIGHT STOP"
        if "2B" in stage:
            return "🟡 CAUTION"
        if "2A" in stage:
            return "🟢 HOLD"
        return "—"

    def _action_to_severity(self, action: str) -> str:
        if "SELL" in action:
            return "red"
        if "TIGHT" in action:
            return "orange"
        if "CAUTION" in action:
            return "yellow"
        if "HOLD" in action:
            return "green"
        return "gray"
