# tradingagents/engine/runtime/backtest_loop.py
from __future__ import annotations
from collections import deque
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Union

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


class BacktestLoop:
    """Orchestrates the full backtest pipeline.

    Per-bar sequence:
    1. stream_bars → Bar or DATA_SKIPPED
    2. Build MarketState from rolling window
    3. generate_signal → Signal or SIGNAL_REJECTED
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
        last_seen_bar: Bar | None = None  # last valid bar seen regardless of fill (for mark-to-market)
        # Deterministic fallback timestamp derived from the run's start date
        start_ts = datetime(start.year, start.month, start.day, tzinfo=timezone.utc)
        current_ts = start_ts

        for item in self._feed.stream_bars(symbol, start, end):
            if isinstance(item, RejectionReason):
                events.append(BacktestEvent(
                    event_type=BacktestEventType.DATA_SKIPPED,
                    timestamp=current_ts,
                    symbol=symbol,
                    rejection=item,
                ))
                continue

            bar: Bar = item
            current_ts = bar.timestamp
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

            # Strategy
            signal_result = self._strategy.generate_signal(market_state)
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
                ))
                continue

            events.append(BacktestEvent(
                event_type=BacktestEventType.SIGNAL_GENERATED,
                timestamp=bar.timestamp,
                symbol=symbol,
            ))

            # Risk
            current_prices = {symbol: bar.close}
            risk_result = self._risk.evaluate(
                signal, portfolio_state, current_prices, self._config
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


