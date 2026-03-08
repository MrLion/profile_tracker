# Portfolio Tracker v3.0

Modular stock portfolio tracker with pluggable strategy architecture.
Built for Weinstein Stage Analysis but extensible to any technical strategy.

## Quick Start

```bash
# 1. Install dependencies
pip install yfinance pandas tabulate

# 2. Run full report (all strategies)
python run.py

# 3. Run specific strategy
python run.py --strategy weinstein

# 4. Run multiple strategies
python run.py --strategy weinstein rs momentum

# 5. Scan watchlist for opportunities
python run.py --watchlist

# 6. P/L only (no strategy analysis)
python run.py --pnl

# 7. Export to CSV
python run.py --csv

# 8. List available strategies
python run.py --list-strategies

# 9. Run tests
python -m tests.test_all
```

## Configuration

Edit `portfolio.json` to manage your portfolio:

```json
{
    "starting_value": 10000,
    "cash": 700,
    "portfolio": {
        "VRT": {"entry_price": 200.00, "dollars": 1800, "theme": "AI Infrastructure"},
        "NVDA": {"entry_price": 190.00, "dollars": 1700, "theme": "Semiconductors"}
    },
    "watchlist": ["XOM", "CVX", "LMT", "AMAT"],
    "benchmarks": ["SPY", "QQQ", "DIA"],
    "closed_trades": []
}
```

## Strategies

| Strategy | Slug | What it does |
|---|---|---|
| Weinstein Stage Analysis | `weinstein` | Classifies stocks into Stages 1-4 via 30-week SMA |
| Relative Strength | `rs` | Ranks stocks by return vs SPY over 1/3/6/12 months |
| Momentum Score | `momentum` | Composite of ROC(20/60/125) + RSI |

## Adding a New Strategy

1. Create a file in `strategies/` (e.g., `strategies/my_strategy.py`)
2. Inherit from `Strategy` base class
3. Implement `analyze()`, `scan_watchlist()`, `columns()`, `row()`
4. Done — the runner auto-discovers it

```python
from strategies.base import Strategy, Signal

class MyStrategy(Strategy):
    name = "My Custom Strategy"
    slug = "custom"

    def analyze(self, ticker, df, position=None) -> Signal:
        # Your analysis logic here
        return Signal(ticker=ticker, action="🟢 HOLD", ...)

    def scan_watchlist(self, ticker, df) -> Signal | None:
        ...

    def columns(self) -> list[str]:
        return ["Col1", "Col2"]

    def row(self, signal) -> list[str]:
        return ["val1", "val2"]
```

## Project Structure

```
portfolio_tracker/
├── run.py                  # CLI entry point
├── portfolio.json          # Your portfolio config
├── core/
│   ├── config.py           # Load/save portfolio.json
│   ├── data.py             # Fetch & cache price data
│   ├── indicators.py       # SMA, EMA, RSI, ATR, Bollinger, etc.
│   └── portfolio.py        # Position P/L calculations
├── strategies/
│   ├── base.py             # Abstract Strategy + Signal classes
│   ├── weinstein.py        # Weinstein Stage Analysis
│   ├── relative_strength.py # RS ranking vs SPY
│   └── momentum.py         # Momentum scoring
├── reports/
│   ├── terminal.py         # Pretty terminal output
│   └── csv_export.py       # CSV export
└── tests/
    └── test_all.py         # Unit tests
```
