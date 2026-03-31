#!/usr/bin/env python
# run_backtest.py
"""BacktestLoop runner — LangGraph multi-agent strategy against cached CSV data.

Usage:
    python run_backtest.py                                   # AAPL, 3 trading days
    python run_backtest.py --symbol AAPL --start 2024-01-02 --end 2024-01-05
    python run_backtest.py --toy                             # MA-crossover (no LLM)

Optional risk flags (same units as API SimulationConfigSchema): --stop-loss-pct,
--take-profit-pct, --max-drawdown-pct (percents); --max-position-shares; --min-confidence;
--fee-bps.

Defaults to a 3-day window to keep LLM costs low during plumbing tests.
Use --toy to run without any LLM calls (fast, free).

Reproducibility / CI
--------------------
--toy runs are long-only by default (long_only=True). This is the canonical
regression baseline: deterministic, no LLM calls, no short-selling.

WARNING: --no-long-only is EXPERIMENTAL.
ConcreteRiskManager was designed for long-only portfolios. Its cash-cap and
position-limit checks are direction-blind, so SELL signals can open unintended
short positions and produce unrealistic P&L. Do not use --no-long-only for
benchmarking or CI until a direction-aware risk manager is implemented.
"""
from __future__ import annotations
import argparse
from datetime import date
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
load_dotenv()

from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.engine.adapters.csv_feed import CsvDataFeed
from tradingagents.engine.adapters.langgraph_strategy import LangGraphStrategyAdapter
from tradingagents.engine.adapters.toy_strategy import MovingAverageCrossStrategy
from tradingagents.engine.runtime.backtest_loop import BacktestLoop
from tradingagents.engine.runtime.paper_portfolio import InMemoryPortfolio
from tradingagents.engine.runtime.simulator import ConcreteExecutionSimulator
from tradingagents.engine.runtime.risk_manager import ConcreteRiskManager
from tradingagents.engine.schemas.config import SimulationConfig
from tradingagents.engine.schemas.config_input import SimulationConfigInput
from tradingagents.engine.schemas.portfolio import BacktestEventType


def _adapter_confidence_for_risk_gate(sim_cfg: SimulationConfig) -> float:
    """Align LangGraph signal confidence with ``min_confidence_threshold`` (see RunService)."""
    t = float(sim_cfg.min_confidence_threshold)
    return min(1.0, max(0.8, t))


def _simulation_config_input_kwargs(
    *,
    initial_cash: float,
    slippage_bps: float,
    fee_per_trade: float,
    max_position_pct: float,
    stop_loss_percentage: float | None = None,
    take_profit_target: float | None = None,
    max_drawdown_limit: float | None = None,
    max_position_size: float | None = None,
    min_confidence_threshold: float | None = None,
    fee_bps: float | None = None,
) -> dict[str, Any]:
    """Build kwargs for ``SimulationConfigInput`` (same percent/share semantics as the API)."""
    kw: dict[str, Any] = {
        "initial_cash": initial_cash,
        "slippage_bps": slippage_bps,
        "fee_per_trade": fee_per_trade,
        "max_position_pct": max_position_pct,
    }
    if stop_loss_percentage is not None:
        kw["stop_loss_percentage"] = stop_loss_percentage
    if take_profit_target is not None:
        kw["take_profit_target"] = take_profit_target
    if max_drawdown_limit is not None:
        kw["max_drawdown_limit"] = max_drawdown_limit
    if max_position_size is not None:
        kw["max_position_size"] = max_position_size
    if min_confidence_threshold is not None:
        kw["min_confidence_threshold"] = min_confidence_threshold
    if fee_bps is not None:
        kw["fee_bps"] = fee_bps
    return kw


def run(
    symbol: str,
    start: date,
    end: date,
    toy: bool = False,
    long_only: bool = True,
    initial_cash: float = 100_000,
    slippage_bps: float = 5,
    fee_per_trade: float = 1.0,
    max_position_pct: float = 10,  # percent, e.g. 10 = 10%
    *,
    stop_loss_percentage: float | None = None,
    take_profit_target: float | None = None,
    max_drawdown_limit: float | None = None,
    max_position_size: float | None = None,
    min_confidence_threshold: float | None = None,
    fee_bps: float | None = None,
) -> None:
    config = SimulationConfigInput(
        **_simulation_config_input_kwargs(
            initial_cash=initial_cash,
            slippage_bps=slippage_bps,
            fee_per_trade=fee_per_trade,
            max_position_pct=max_position_pct,
            stop_loss_percentage=stop_loss_percentage,
            take_profit_target=take_profit_target,
            max_drawdown_limit=max_drawdown_limit,
            max_position_size=max_position_size,
            min_confidence_threshold=min_confidence_threshold,
            fee_bps=fee_bps,
        )
    ).to_simulation_config()

    try:
        feed = CsvDataFeed(symbol)
    except FileNotFoundError as exc:
        print(f"Error: {exc}")
        return

    if toy:
        strategy = MovingAverageCrossStrategy(
            short_window=5, long_window=20, confidence=0.8, long_only=long_only
        )
        mode = "long-only" if long_only else "long/short"
        print(f"Strategy: MA-crossover (toy, no LLM, {mode})")
    else:
        graph_config = dict(DEFAULT_CONFIG)
        graph_config.update({
            "project_dir": str(Path(__file__).resolve().parent),
            "results_dir": "./results",
            "llm_provider": "deepseek",
            "deep_think_llm": "deepseek-chat",
            "quick_think_llm": "deepseek-chat",
        })
        strategy = LangGraphStrategyAdapter(
            selected_analysts=["market", "fundamentals"],
            config=graph_config,
            confidence=_adapter_confidence_for_risk_gate(config),
        )
        print("Strategy: LangGraphStrategyAdapter (market + fundamentals analysts)")
    risk = ConcreteRiskManager()
    simulator = ConcreteExecutionSimulator()
    portfolio = InMemoryPortfolio()

    print(f"\nRunning backtest: {symbol}  {start} to {end}")
    risk_bits: list[str] = []
    if config.stop_loss_pct is not None:
        risk_bits.append(f"stop={float(config.stop_loss_pct):.2%}")
    if config.take_profit_pct is not None:
        risk_bits.append(f"tp={float(config.take_profit_pct):.2%}")
    if config.max_drawdown_limit is not None:
        risk_bits.append(f"max_dd={float(config.max_drawdown_limit):.2%}")
    if config.max_position_size is not None:
        risk_bits.append(f"max_shares={config.max_position_size}")
    risk_suffix = f"  [{' '.join(risk_bits)}]" if risk_bits else ""
    print(
        f"Config: cash=${float(config.initial_cash):,.0f}  "
        f"slippage={config.slippage_bps}bps  fee=${config.fee_per_trade}/trade  "
        f"max_pos={float(config.max_position_pct):.0%}"
        f"{risk_suffix}\n"
    )

    try:
        result = BacktestLoop(feed, strategy, risk, simulator, portfolio, config).run(
            symbol, start, end
        )
    finally:
        close = getattr(strategy, "close", None)
        if callable(close):
            close()

    # ── Event summary ────────────────────────────────────────────────────────
    counts: dict = {}
    for e in result.events:
        counts[e.event_type] = counts.get(e.event_type, 0) + 1
    print("Event counts:")
    for et, n in sorted(counts.items(), key=lambda x: x[0].value):
        print(f"  {et.value:<32} {n:>5}")

    # ── Rejection breakdown ───────────────────────────────────────────────────
    rejection_codes: dict = {}
    for e in result.events:
        if e.event_type in (BacktestEventType.ORDER_REJECTED, BacktestEventType.SIGNAL_REJECTED):
            code = e.rejection.code.value if e.rejection else "UNKNOWN"
            rejection_codes[code] = rejection_codes.get(code, 0) + 1
    if rejection_codes:
        print("\nRejection codes:")
        for code, n in sorted(rejection_codes.items()):
            print(f"  {code:<32} {n:>5}")

    cache_stats_fn = getattr(strategy, "get_cache_stats", None)
    if callable(cache_stats_fn):
        cache_stats = cache_stats_fn()
        print(
            "\nSignal cache: "
            f"hits={cache_stats.get('hits', 0)}  "
            f"misses={cache_stats.get('misses', 0)}  "
            f"read_errors={cache_stats.get('read_errors', 0)}  "
            f"write_errors={cache_stats.get('write_errors', 0)}"
        )

    # ── Fills ────────────────────────────────────────────────────────────────
    fills = [e.fill for e in result.events if e.fill is not None]
    print(f"\nTotal fills: {len(fills)}")
    if fills:
        print("Last 5 fills:")
        for f in fills[-5:]:
            print(
                f"  {f.filled_at.date()}  {f.direction.value:4s}"
                f"  qty={float(f.filled_quantity):.4f}"
                f"  @ ${float(f.fill_price):>9.4f}"
                f"  fees=${float(f.fees):.2f}"
            )


    # ── Metrics ──────────────────────────────────────────────────────────────
    m = result.metrics
    pnl = float(m.total_equity) - float(config.initial_cash)
    pnl_pct = pnl / float(config.initial_cash) * 100
    print(f"\nInitial cash:   ${float(config.initial_cash):>12,.2f}")
    print(f"Final equity:   ${float(m.total_equity):>12,.2f}  ({pnl_pct:+.2f}%)")
    print(f"Unrealized PnL: ${float(m.unrealized_pnl):>12,.2f}")
    if result.final_state.positions:
        print(f"Open positions: {dict(result.final_state.positions)}")
    else:
        print("Open positions: none")


def main() -> None:
    parser = argparse.ArgumentParser(description="BacktestLoop runner")
    parser.add_argument("--symbol", default="AAPL")
    parser.add_argument("--start", default="2024-01-02",
                        help="Start date (default: 2024-01-02)")
    parser.add_argument("--end", default="2024-01-05",
                        help="End date (default: 2024-01-05, ~3 trading days)")
    parser.add_argument("--toy", action="store_true",
                        help="Use MA-crossover strategy instead of LangGraph (no LLM calls)")
    parser.add_argument("--long-only", dest="long_only", action="store_true", default=True,
                        help="Long-only mode: never emit SELL (default: True)")
    parser.add_argument("--no-long-only", dest="long_only", action="store_false",
                        help="[EXPERIMENTAL] Allow SELL signals. ConcreteRiskManager is "
                             "direction-blind; short positions produce unreliable P&L until "
                             "direction-aware risk logic is implemented.")
    parser.add_argument("--initial-cash", dest="initial_cash", type=float, default=100_000,
                        help="Starting cash in USD (default: 100000)")
    parser.add_argument("--slippage-bps", dest="slippage_bps", type=float, default=5,
                        help="Slippage in basis points per fill (default: 5)")
    parser.add_argument("--fee-per-trade", dest="fee_per_trade", type=float, default=1.0,
                        help="Flat fee in USD per trade (default: 1.0)")
    parser.add_argument("--max-position-pct", dest="max_position_pct", type=float, default=10,
                        help="Max position size as percent of equity (default: 10 = 10%%)")
    parser.add_argument(
        "--stop-loss-pct",
        dest="stop_loss_percentage",
        type=float,
        default=None,
        help="Stop loss vs avg entry, percent (e.g. 5 = 5%%). Same as API stop_loss_percentage.",
    )
    parser.add_argument(
        "--take-profit-pct",
        dest="take_profit_target",
        type=float,
        default=None,
        help="Take-profit vs avg entry, percent. Same as API take_profit_target.",
    )
    parser.add_argument(
        "--max-drawdown-pct",
        dest="max_drawdown_limit",
        type=float,
        default=None,
        help="Max drawdown from peak equity, percent. Same as API max_drawdown_limit.",
    )
    parser.add_argument(
        "--max-position-shares",
        dest="max_position_size",
        type=float,
        default=None,
        help="Hard cap on shares per symbol. Same as API max_position_size.",
    )
    parser.add_argument(
        "--min-confidence",
        dest="min_confidence_threshold",
        type=float,
        default=None,
        help="Risk gate threshold 0–1 (default from SimulationConfigInput: 0.5).",
    )
    parser.add_argument(
        "--fee-bps",
        dest="fee_bps",
        type=float,
        default=None,
        help="Optional fee on notional in basis points (additive with --fee-per-trade).",
    )
    args = parser.parse_args()
    start_d = date.fromisoformat(args.start)
    end_d = date.fromisoformat(args.end)
    if end_d < start_d:
        parser.error("--end must be on or after --start")
    run(
        symbol=args.symbol.upper(),
        start=start_d,
        end=end_d,
        toy=args.toy,
        long_only=args.long_only,
        initial_cash=args.initial_cash,
        slippage_bps=args.slippage_bps,
        fee_per_trade=args.fee_per_trade,
        max_position_pct=args.max_position_pct,
        stop_loss_percentage=args.stop_loss_percentage,
        take_profit_target=args.take_profit_target,
        max_drawdown_limit=args.max_drawdown_limit,
        max_position_size=args.max_position_size,
        min_confidence_threshold=args.min_confidence_threshold,
        fee_bps=args.fee_bps,
    )


if __name__ == "__main__":
    main()
