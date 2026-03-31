"""As-of validation on analyst reports before the debate stage."""
from __future__ import annotations

from tradingagents.graph.conditional_logic import ConditionalLogic
from tradingagents.agents.utils.agent_states import AgentState


def _minimal_state(**kwargs: str) -> AgentState:
    base: AgentState = {
        "messages": [],
        "company_of_interest": "AAPL",
        "trade_date": "2026-01-15",
        "sender": "",
        "market_report": "",
        "sentiment_report": "",
        "news_report": "",
        "fundamentals_report": "",
        "investment_debate_state": {
            "bull_history": "",
            "bear_history": "",
            "history": "",
            "current_response": "",
            "judge_decision": "",
            "count": 0,
        },
        "investment_plan": "",
        "trader_investment_plan": "",
        "risk_debate_state": {
            "aggressive_history": "",
            "conservative_history": "",
            "neutral_history": "",
            "history": "",
            "latest_speaker": "",
            "current_aggressive_response": "",
            "current_conservative_response": "",
            "current_neutral_response": "",
            "judge_decision": "",
            "count": 0,
        },
        "final_trade_decision": "",
    }
    base.update(kwargs)  # type: ignore[arg-type]
    return base


def test_analyst_reports_include_as_of_requires_marker_and_trade_date():
    logic = ConditionalLogic()
    chain = ("market", "news")
    st = _minimal_state(
        market_report="RSI high. No temporal anchor.",
        news_report="Macro calm.",
    )
    assert logic.analyst_reports_include_as_of(st, chain) is False

    st2 = _minimal_state(
        market_report="As-of: 2026-01-15 trend up.",
        news_report="Headlines ok. 2026-01-15 window.",
    )
    assert logic.analyst_reports_include_as_of(st2, chain) is True


def test_analyst_reports_false_if_any_report_empty():
    logic = ConditionalLogic()
    chain = ("market", "fundamentals")
    st = _minimal_state(
        market_report="As-of: 2026-01-15 ok.",
        fundamentals_report="",
    )
    assert logic.analyst_reports_include_as_of(st, chain) is False
