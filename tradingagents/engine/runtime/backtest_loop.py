# tradingagents/engine/runtime/backtest_loop.py
from __future__ import annotations
from collections import deque
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Literal

from tradingagents.engine.contracts.execution import ExecutionSimulator
from tradingagents.engine.contracts.feeds import DataFeed
from tradingagents.engine.contracts.portfolio import Portfolio
from tradingagents.engine.contracts.risk import RiskManager
from tradingagents.engine.contracts.strategy import StrategyAgent
from tradingagents.engine.schemas.config import SimulationConfig
from tradingagents.engine.schemas.market import Bar, MarketState
from tradingagents.engine.schemas.orders import (
    ApprovedOrder, FillResult, RejectionReason,
)
from tradingagents.engine.schemas.portfolio import (
    BacktestEvent, BacktestEventType, BacktestResult, PortfolioState,
)
from tradingagents.engine.schemas.signals import Signal, SignalDirection


_WINDOW_SIZE = 20  # number of bars to include in MarketState.bars_window


def _total_equity(state: PortfolioState, prices: dict[str, Decimal]) -> Decimal:
    position_value = sum(
        qty * prices.get(sym, Decimal("0"))
        for sym, qty in state.positions.items()
    )
    return state.cash + position_value


ForcedExitKind = Literal["stop_loss", "take_profit"]

# Prefix persisted on ``BacktestEvent.detail`` for trace / UI (not an enum to keep JSON stable).
RISK_FORCED_EXIT_DETAIL_PREFIX = "risk_forced_exit:"


def _stop_take_profit_signal(
    symbol: str,
    portfolio: PortfolioState,
    bar: Bar,
    config: SimulationConfig,
) -> tuple[Signal, ForcedExitKind] | None:
    """Return a forced SELL and exit kind when stop-loss or take-profit vs cost basis triggers."""
    qty = portfolio.positions.get(symbol, Decimal("0"))
    if qty <= Decimal("0"):
        return None
    entry = portfolio.cost_basis.get(symbol)
    if entry is None or entry <= Decimal("0"):
        return None
    close = bar.close
    if config.stop_loss_pct is not None:
        floor = entry * (Decimal("1") - config.stop_loss_pct)
        if close <= floor:
            return (
                Signal(
                    symbol=symbol,
                    direction=SignalDirection.SELL,
                    confidence=1.0,
                    reasoning=f"risk: stop_loss (close {close} <= floor {floor})",
                    generated_at=bar.timestamp,
                    source_bar_timestamp=bar.timestamp,
                ),
                "stop_loss",
            )
    if config.take_profit_pct is not None:
        target = entry * (Decimal("1") + config.take_profit_pct)
        if close >= target:
            return (
                Signal(
                    symbol=symbol,
                    direction=SignalDirection.SELL,
                    confidence=1.0,
                    reasoning=f"risk: take_profit (close {close} >= target {target})",
                    generated_at=bar.timestamp,
                    source_bar_timestamp=bar.timestamp,
                ),
                "take_profit",
            )
    return None


class BacktestLoop:
    """Orchestrates the full backtest pipeline.

    Per-bar sequence:
    1. stream_bars → Bar or DATA_SKIPPED
    2. Build MarketState from rolling window; update peak equity for drawdown limits
    3. Optional forced SELL from stop_loss / take_profit vs cost basis; else generate_signal
    4. evaluate → ApprovedOrder (emit ORDER_APPROVED) or ORDER_REJECTED
    5. get next bar for fill
    6. fill → FillResult or ORDER_REJECTED
    7. apply_fill → new PortfolioState; emit FILL_EXECUTED
    """

    def __init__(
        self,
        feed: DataFeed,
        strategy: StrategyAgent,
        risk: RiskManager,
        simulator: ExecutionSimulator,
        portfolio: Portfolio,
        config: SimulationConfig,
    ) -> None:
        self._feed = feed
        self._strategy = strategy
        self._risk = risk
        self._simulator = simulator
        self._portfolio = portfolio
        self._config = config

    def run(self, symbol: str, start: date, end: date) -> BacktestResult:
        events: list[BacktestEvent] = []
        window: deque[Bar] = deque(maxlen=_WINDOW_SIZE)

        # Get first bar timestamp for initial_state as_of
        # We'll set it from the first bar we actually see
        first_bar_ts = None
        portfolio_state: PortfolioState | None = None
        peak_equity: Decimal | None = None
        last_seen_bar: Bar | None = None  # last valid bar seen regardless of fill (for mark-to-market)
        # Deterministic fallback timestamp derived from the run's start date
        start_ts = datetime(start.year, start.month, start.day, tzinfo=timezone.utc)
        current_day = start

        for item in self._feed.stream_bars(symbol, start, end):
            # Use 21:00 UTC (≈ NYSE close) for skipped-day events, matching bar timestamp convention.
            event_ts = datetime(
                current_day.year, current_day.month, current_day.day, 21, 0, 0, tzinfo=timezone.utc
            )
            current_day += timedelta(days=1)
            if isinstance(item, RejectionReason):
                events.append(BacktestEvent(
                    event_type=BacktestEventType.DATA_SKIPPED,
                    timestamp=event_ts,
                    symbol=symbol,
                    rejection=item,
                ))
                continue

            bar: Bar = item
            last_seen_bar = bar  # always track last valid bar for end-of-run mark-to-market

            if first_bar_ts is None:
                first_bar_ts = bar.timestamp
                portfolio_state = type(self._portfolio).initial_state(self._config, as_of=first_bar_ts)

            assert portfolio_state is not None  # set on first bar
            window.append(bar)
            market_state = MarketState(
                symbol=symbol,
                as_of=bar.timestamp,
                latest_bar=bar,
                bars_window=tuple(window),
            )

            mark_prices = {symbol: bar.close}
            eq = _total_equity(portfolio_state, mark_prices)
            # Peak is updated with same-bar mark *before* risk evaluates this bar's
            # orders. A new equity high on the signal bar raises the peak immediately,
            # so drawdown vs peak is slightly more lenient than "prior bar only" peak.
            peak_equity = eq if peak_equity is None else max(peak_equity, eq)

            forced_pair = _stop_take_profit_signal(symbol, portfolio_state, bar, self._config)
            forced_detail: str | None = None
            if forced_pair is not None:
                signal_result, forced_kind = forced_pair
                forced_detail = f"{RISK_FORCED_EXIT_DETAIL_PREFIX}{forced_kind}"
            else:
                signal_result = self._strategy.generate_signal(
                    market_state, portfolio_state
                )
            if isinstance(signal_result, RejectionReason):
                events.append(BacktestEvent(
                    event_type=BacktestEventType.SIGNAL_REJECTED,
                    timestamp=bar.timestamp,
                    symbol=symbol,
                    rejection=signal_result,
                ))
                continue

            signal: Signal = signal_result

            # Skip HOLD signals — no order needed
            if signal.direction == SignalDirection.HOLD:
                events.append(BacktestEvent(
                    event_type=BacktestEventType.SIGNAL_GENERATED,
                    timestamp=bar.timestamp,
                    symbol=symbol,
                    detail=forced_detail,
                    signal=signal,
                ))
                continue

            events.append(BacktestEvent(
                event_type=BacktestEventType.SIGNAL_GENERATED,
                timestamp=bar.timestamp,
                symbol=symbol,
                detail=forced_detail,
                signal=signal,
            ))

            # Risk
            current_prices = {symbol: bar.close}
            risk_result = self._risk.evaluate(
                signal,
                portfolio_state,
                current_prices,
                self._config,
                peak_equity_for_drawdown=peak_equity,
            )
            if isinstance(risk_result, RejectionReason):
                events.append(BacktestEvent(
                    event_type=BacktestEventType.ORDER_REJECTED,
                    timestamp=bar.timestamp,
                    symbol=symbol,
                    rejection=risk_result,
                ))
                continue

            order: ApprovedOrder = risk_result
            events.append(BacktestEvent(
                event_type=BacktestEventType.ORDER_APPROVED,
                timestamp=bar.timestamp,
                symbol=symbol,
                order=order,
            ))

            # Get next bar for execution
            next_date = self._feed.calendar.next_trading_day(bar.timestamp.date())
            next_bar_result = self._feed.get_bar(symbol, next_date)
            next_bar = next_bar_result if isinstance(next_bar_result, Bar) else None

            # Execution
            fill_result = self._simulator.fill(
                order, next_bar, self._feed.calendar, self._config
            )
            if isinstance(fill_result, RejectionReason):
                events.append(BacktestEvent(
                    event_type=BacktestEventType.ORDER_REJECTED,
                    timestamp=bar.timestamp,
                    symbol=symbol,
                    rejection=fill_result,
                ))
                continue

            fill: FillResult = fill_result
            portfolio_state = self._portfolio.apply_fill(portfolio_state, fill)
            events.append(BacktestEvent(
                event_type=BacktestEventType.FILL_EXECUTED,
                timestamp=fill.filled_at,
                symbol=symbol,
                fill=fill,
            ))

        if portfolio_state is None:
            # No bars were processed — return empty result with deterministic timestamp
            portfolio_state = type(self._portfolio).initial_state(self._config, as_of=start_ts)

        initial_state = type(self._portfolio).initial_state(self._config, as_of=first_bar_ts or portfolio_state.as_of)
        current_prices = {symbol: last_seen_bar.close} if last_seen_bar is not None else {}
        metrics = self._portfolio.mark_to_market(portfolio_state, current_prices)

        return BacktestResult(
            symbol=symbol,
            start=start,
            end=end,
            initial_state=initial_state,
            final_state=portfolio_state,
            events=tuple(events),
            metrics=metrics,
        )


