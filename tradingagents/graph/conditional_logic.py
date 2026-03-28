# TradingAgents/graph/conditional_logic.py

from __future__ import annotations

import logging
import re

from tradingagents.agents.utils.agent_states import AgentState

logger = logging.getLogger(__name__)

_AS_OF_MARKER = re.compile(r"(?i)as-of\s*:")

_ANALYST_REPORT_KEYS: dict[str, str] = {
    "market": "market_report",
    "social": "sentiment_report",
    "news": "news_report",
    "fundamentals": "fundamentals_report",
}


def _text_has_as_of_anchor(text: str, trade_date: str) -> bool:
    if _AS_OF_MARKER.search(text):
        return True
    td = (trade_date or "").strip()
    if len(td) >= 10 and td[:10] in text:
        return True
    return False


class ConditionalLogic:
    """Handles conditional logic for determining graph flow."""

    def __init__(self, max_debate_rounds=1, max_risk_discuss_rounds=1):
        """Initialize with configuration parameters."""
        self.max_debate_rounds = max_debate_rounds
        self.max_risk_discuss_rounds = max_risk_discuss_rounds

    def should_continue_market(self, state: AgentState):
        """Determine if market analysis should continue."""
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            return "tools_market"
        return "Msg Clear Market"

    def should_continue_social(self, state: AgentState):
        """Determine if social media analysis should continue."""
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            return "tools_social"
        return "Msg Clear Social"

    def should_continue_news(self, state: AgentState):
        """Determine if news analysis should continue."""
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            return "tools_news"
        return "Msg Clear News"

    def should_continue_fundamentals(self, state: AgentState):
        """Determine if fundamentals analysis should continue."""
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            return "tools_fundamentals"
        return "Msg Clear Fundamentals"

    def should_continue_debate(self, state: AgentState) -> str:
        """Determine if debate should continue."""

        if (
            state["investment_debate_state"]["count"] >= 2 * self.max_debate_rounds
        ):  # 3 rounds of back-and-forth between 2 agents
            return "Research Manager"
        if state["investment_debate_state"]["current_response"].startswith("Bull"):
            return "Bear Researcher"
        return "Bull Researcher"

    def should_continue_risk_analysis(self, state: AgentState) -> str:
        """Determine if risk analysis should continue."""
        if (
            state["risk_debate_state"]["count"] >= 3 * self.max_risk_discuss_rounds
        ):  # 3 rounds of back-and-forth between 3 agents
            return "Risk Judge"
        if state["risk_debate_state"]["latest_speaker"].startswith("Aggressive"):
            return "Conservative Analyst"
        if state["risk_debate_state"]["latest_speaker"].startswith("Conservative"):
            return "Neutral Analyst"
        return "Aggressive Analyst"

    def analyst_reports_include_as_of(
        self,
        state: AgentState,
        analyst_chain: tuple[str, ...],
    ) -> bool:
        """True when each selected analyst's report includes an As-of style anchor."""
        trade_date = state.get("trade_date", "") or ""
        for role in analyst_chain:
            key = _ANALYST_REPORT_KEYS.get(role)
            if not key:
                continue
            blob = (state.get(key) or "").strip()
            if not blob:
                return False
            if not _text_has_as_of_anchor(blob, trade_date):
                return False
        return True

    def log_as_of_gate_bypass(self, analyst_chain: tuple[str, ...]) -> None:
        logger.warning(
            "As-of gate: proceeding to debate without required markers in reports "
            "for chain=%s",
            analyst_chain,
        )
