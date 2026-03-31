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


def _nonnegative_int(name: str, value: object) -> int:
    """Parse int and require >= 0 (0 = never run tools_* for that analyst)."""
    try:
        n = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as e:
        raise ValueError(f"{name} must be a non-negative integer, got {value!r}") from e
    if n < 0:
        raise ValueError(f"{name} must be >= 0, got {n}")
    return n


class ConditionalLogic:
    """Handles conditional logic for determining graph flow."""

    def __init__(
        self,
        max_debate_rounds=1,
        max_risk_discuss_rounds=1,
        max_analyst_tool_rounds: int = 32,
        max_analyst_tool_rounds_by_role: dict[str, int] | None = None,
    ):
        """Initialize with configuration parameters."""
        self.max_debate_rounds = max_debate_rounds
        self.max_risk_discuss_rounds = max_risk_discuss_rounds
        self.max_analyst_tool_rounds = _nonnegative_int(
            "max_analyst_tool_rounds", max_analyst_tool_rounds
        )
        raw_overrides = dict(max_analyst_tool_rounds_by_role or {})
        self.max_analyst_tool_rounds_by_role = {
            k: _nonnegative_int(f"max_analyst_tool_rounds_by_role[{k!r}]", v)
            for k, v in raw_overrides.items()
        }

    def _tool_round_cap(self, role: str) -> int:
        """Max completed tools_* visits allowed for this analyst role."""
        if role in self.max_analyst_tool_rounds_by_role:
            return self.max_analyst_tool_rounds_by_role[role]
        return self.max_analyst_tool_rounds

    def _completed_tool_rounds(self, state: AgentState, role: str) -> int:
        ar = state.get("analyst_tool_rounds") or {}
        return int(ar.get(role, 0))

    def _route_analyst_tools(
        self,
        state: AgentState,
        role: str,
        tools_node: str,
        msg_clear_node: str,
        log_label: str,
    ) -> str:
        """Route to tools_* or Msg Clear; enforce per-role tool round cap."""
        messages = state["messages"]
        last_message = messages[-1]
        if not last_message.tool_calls:
            return msg_clear_node
        cap = self._tool_round_cap(role)
        done = self._completed_tool_rounds(state, role)
        if done >= cap:
            logger.warning(
                "%s: tool round cap reached (%s/%s); skipping tools",
                log_label,
                done,
                cap,
            )
            return msg_clear_node
        return tools_node

    def should_continue_market(self, state: AgentState):
        """Determine if market analysis should continue."""
        return self._route_analyst_tools(
            state, "market", "tools_market", "Msg Clear Market", "Market analyst"
        )

    def should_continue_social(self, state: AgentState):
        """Determine if social media analysis should continue."""
        return self._route_analyst_tools(
            state, "social", "tools_social", "Msg Clear Social", "Social analyst"
        )

    def should_continue_news(self, state: AgentState):
        """Determine if news analysis should continue."""
        return self._route_analyst_tools(
            state, "news", "tools_news", "Msg Clear News", "News analyst"
        )

    def should_continue_fundamentals(self, state: AgentState):
        """Determine if fundamentals analysis should continue."""
        return self._route_analyst_tools(
            state,
            "fundamentals",
            "tools_fundamentals",
            "Msg Clear Fundamentals",
            "Fundamentals analyst",
        )

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
