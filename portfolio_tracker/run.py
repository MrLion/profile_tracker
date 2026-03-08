#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║  PORTFOLIO TRACKER  v3.0                                       ║
║  Modular strategy engine with plugin architecture              ║
╚══════════════════════════════════════════════════════════════════╝

USAGE:
    python run.py                                  # Full report, all strategies
    python run.py --pnl                            # P/L only
    python run.py --strategy weinstein             # Single strategy
    python run.py --strategy weinstein rs          # Multiple strategies
    python run.py --watchlist                      # Scan watchlist
    python run.py --csv                            # Export to CSV
    python run.py --list-strategies                # Show available strategies
"""

import argparse
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import Config
from core.data import DataFetcher
from core.portfolio import Portfolio
from strategies import discover_strategies
from strategies.base import Signal
from reports.terminal import TerminalReport
from reports.csv_export import CSVExport


def main():
    parser = argparse.ArgumentParser(description="Portfolio Tracker v3.0")
    parser.add_argument("--pnl", action="store_true", help="P/L only, skip strategy analysis")
    parser.add_argument("--watchlist", action="store_true", help="Scan watchlist for opportunities")
    parser.add_argument("--csv", action="store_true", help="Export to CSV")
    parser.add_argument("--strategy", nargs="*", default=None,
                        help="Run specific strategies by slug (default: all)")
    parser.add_argument("--list-strategies", action="store_true", help="Show available strategies")
    parser.add_argument("--config", default=None, help="Path to portfolio.json")
    args = parser.parse_args()

    # ── Discover strategies ──
    all_strategies = discover_strategies()

    if args.list_strategies:
        print("\n  Available strategies:")
        for slug, strat in all_strategies.items():
            print(f"    {slug:15s}  {strat.name}")
        print(f"\n  Use: python run.py --strategy {' '.join(all_strategies.keys())}")
        return

    # ── Select active strategies ──
    if args.strategy:
        active = {}
        for s in args.strategy:
            if s in all_strategies:
                active[s] = all_strategies[s]
            else:
                print(f"  ⚠️  Unknown strategy '{s}'. Available: {', '.join(all_strategies.keys())}")
        if not active:
            sys.exit(1)
    else:
        active = all_strategies

    # ── Load config ──
    config = Config(path=args.config)

    # ── Print header ──
    print("\n" + "=" * 72)
    print("  📊 PORTFOLIO TRACKER  v3.0")
    print(f"  Report: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Config: {config.path}")
    print("=" * 72)

    report = TerminalReport()
    report.print_header(list(active.values()))

    # ── Fetch data ──
    fetcher = DataFetcher()
    tickers = list(config.portfolio.keys())
    print(f"\n  Fetching data for {len(tickers)} positions...")
    data = fetcher.fetch_many(tickers)

    if not data:
        print("  ❌ No data fetched. Check your internet connection.")
        sys.exit(1)

    # ── Build portfolio ──
    portfolio = Portfolio(config, fetcher)

    # ── P/L Report ──
    report.print_pnl(portfolio)
    report.print_benchmarks(portfolio)

    # ── Strategy Analysis ──
    all_signals: dict[str, list[Signal]] = {}

    if not args.pnl:
        # Special handling: RS strategy needs benchmark data
        if "rs" in active:
            rs_strat = active["rs"]
            bench_df = fetcher.fetch("SPY", period="1y")
            if bench_df is not None:
                rs_strat.set_benchmark_data(bench_df)

        for slug, strategy in active.items():
            signals = strategy.analyze_many(data, portfolio.positions())
            all_signals[slug] = signals
            report.print_strategy(strategy, signals)

        report.print_alerts(all_signals)

    # ── Watchlist ──
    if args.watchlist and not args.pnl:
        watch_tickers = config.watchlist
        print(f"\n  Fetching data for {len(watch_tickers)} watchlist stocks...")
        watch_data = fetcher.fetch_many(watch_tickers)

        # RS strategy needs benchmark for watchlist too
        if "rs" in active:
            rs_strat = active["rs"]
            if rs_strat._bench_df is None:
                bench_df = fetcher.fetch("SPY", period="1y")
                if bench_df is not None:
                    rs_strat.set_benchmark_data(bench_df)

        for slug, strategy in active.items():
            watch_signals = []
            for t, df in watch_data.items():
                sig = strategy.scan_watchlist(t, df)
                if sig is not None:
                    watch_signals.append(sig)
            report.print_watchlist(strategy, watch_signals)

    # ── CSV Export ──
    if args.csv and all_signals:
        CSVExport().export(portfolio, all_signals)

    # ── Footer ──
    print("\n" + "=" * 72)
    print("  Run after 4:00 PM ET on trading days for closing prices.")
    print("  Edit portfolio.json to update positions, cash, watchlist.")
    print("=" * 72 + "\n")


if __name__ == "__main__":
    main()
