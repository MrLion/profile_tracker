import pandas as pd

from strategies.base import Strategy, Signal
from core.portfolio import Position
from core import indicators as ind


class WeinsteinStrategy(Strategy):
    """
    Weinstein Stage Analysis.
    Classifies stocks into Stages 1-4 based on price vs 30-week SMA,
    MA alignment, and 30-week SMA slope.

    Actions:
        🟢 BUY        — Stage 2 breakout: above rising 30w, MAs aligned, volume confirms
        🟢 HOLD       — In position, Stage 2A intact
        ⚪ WATCH      — Setting up but not ready (Stage 1→2, or 2A without volume)
        🟡 CAUTION    — Stage 2B, trend weakening
        🟠 TIGHT STOP — Stage 2C, below 30w but 30w still rising
        🔴 SELL       — Stage 3→4 or 4, below falling 30w
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
        stack = ind.ma_stack(df, price, [10, 21, 50, 200])
        vol_ratio = ind.volume_ratio(df, lookback=5, avg_period=50)
        high_info = ind.near_high(df, lookback=252)

        has_position = position is not None
        action, severity = self._determine_action(stage, has_position, mas, stack, vol_ratio)

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
                "vol_ratio": vol_ratio,
                "pct_from_52w_high": high_info["pct_from_high"],
            },
        )

    def scan_watchlist(self, ticker: str, df: pd.DataFrame) -> Signal | None:
        signal = self.analyze(ticker, df)
        if "BUY" in signal.action or "WATCH" in signal.action:
            return signal
        if "2A" in signal.label:
            return Signal(
                ticker=signal.ticker, action="⚪ WATCH", severity="blue",
                label=signal.label, detail=signal.detail, metrics=signal.metrics,
            )
        return None

    def columns(self) -> list[str]:
        return ["Price", "50d SMA", "Dist 50d", "30w SMA",
                "Dist 30w", "30w↕", "Stage", "MAs", "Vol", "Action"]

    def row(self, signal: Signal) -> list[str]:
        m = signal.metrics
        vol = m.get('vol_ratio')
        vol_str = f"{vol:.1f}x" if vol is not None else "N/A"
        if vol and vol >= 2.0:
            vol_str += " 🔥"
        elif vol and vol >= 1.5:
            vol_str += " ⬆"

        return [
            f"${m['price']:.2f}",
            f"${m['sma_50d']:.2f}" if m.get('sma_50d') else "N/A",
            f"{m['dist_50d']:+.1f}%" if m.get('dist_50d') is not None else "N/A",
            f"${m['sma_30w']:.2f}" if m.get('sma_30w') else "N/A",
            f"{m['dist_30w']:+.1f}%" if m.get('dist_30w') is not None else "N/A",
            "↑" if m.get('sma_30w_rising') else ("↓" if m.get('sma_30w_rising') is False else "?"),
            signal.label,
            "✅" if m.get('ma_aligned') else "❌",
            vol_str,
            signal.action,
        ]

    # ── Private ──

    def _compute_mas(self, df: pd.DataFrame) -> dict:
        mas = {}
        for label, period in [("10d", 10), ("21d", 21), ("50d", 50), ("200d", 200)]:
            mas[label] = ind.sma_latest(df, period)
        mas["30w"] = ind.sma_latest(df, 150)

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

    def _determine_action(self, stage: str, has_position: bool,
                          mas: dict, stack: dict, vol_ratio: float | None) -> tuple[str, str]:
        """
        BUY criteria (not in position):
          - Stage 2A + MAs aligned + 30w rising + volume ratio >= 1.5

        WATCH criteria:
          - Stage 1→2 (basing, potential breakout coming)
          - Stage 2A but volume not confirming yet
          - Stage 2B pullback near support (potential re-entry)

        HOLD/CAUTION/SELL for existing positions based on stage.
        """
        # ── SELL ──
        if "4" in stage or "3→4" in stage:
            return "🔴 SELL", "red"

        # ── TIGHT STOP ──
        if "2C" in stage:
            return "🟠 TIGHT STOP", "orange"

        # ── Stage 1→2: always WATCH ──
        if "1→2" in stage:
            return "⚪ WATCH", "blue"

        # ── Stage 2B ──
        if "2B" in stage:
            if has_position:
                return "🟡 CAUTION", "yellow"
            # Not in position — watch for bounce off support
            if mas.get("30w_rising"):
                return "⚪ WATCH", "blue"
            return "🟡 CAUTION", "yellow"

        # ── Stage 2A — the money zone ──
        if "2A" in stage:
            if has_position:
                return "🟢 HOLD", "green"
            # Not in position — check BUY conditions
            aligned = stack.get("aligned", False)
            rising = mas.get("30w_rising", False)
            strong_vol = vol_ratio is not None and vol_ratio >= 1.5
            if aligned and rising and strong_vol:
                return "🟢 BUY", "green"
            if aligned and rising:
                return "⚪ WATCH", "blue"
            return "⚪ WATCH", "blue"

        return "—", "gray"
