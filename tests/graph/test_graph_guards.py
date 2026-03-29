"""Tests for LangGraph recursion config wiring and per-analyst tool round caps."""

import pytest
from langchain_core.messages import AIMessage

from tradingagents.agents.utils.agent_states import merge_analyst_tool_rounds
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.conditional_logic import ConditionalLogic
from tradingagents.graph.propagation import Propagator


def _msg_with_tools():
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": "get_stock_data",
                "args": {"ticker": "X"},
                "id": "call_1",
                "type": "tool_call",
            }
        ],
    )


def test_propagator_passes_recursion_limit_to_graph_args():
    """Propagator(max_recur_limit=...) drives LangGraph config (no full graph init — needs API keys)."""
    p = Propagator(max_recur_limit=41)
    assert p.max_recur_limit == 41
    args = p.get_graph_args(thread_id="t1")
    assert args["config"]["recursion_limit"] == 41


def test_default_config_has_max_recur_limit():
    assert int(DEFAULT_CONFIG["max_recur_limit"]) >= 1


@pytest.mark.parametrize(
    "method,tools_dest,clear_dest,role",
    [
        ("should_continue_market", "tools_market", "Msg Clear Market", "market"),
        ("should_continue_social", "tools_social", "Msg Clear Social", "social"),
        ("should_continue_news", "tools_news", "Msg Clear News", "news"),
        (
            "should_continue_fundamentals",
            "tools_fundamentals",
            "Msg Clear Fundamentals",
            "fundamentals",
        ),
    ],
)
def test_analyst_tool_cap_exhausted_routes_to_clear(method, tools_dest, clear_dest, role):
    logic = ConditionalLogic(max_analyst_tool_rounds=2)
    fn = getattr(logic, method)
    state = {
        "messages": [_msg_with_tools()],
        "analyst_tool_rounds": {role: 2},
    }
    assert fn(state) == clear_dest


@pytest.mark.parametrize(
    "method,tools_dest,role",
    [
        ("should_continue_market", "tools_market", "market"),
        ("should_continue_social", "tools_social", "social"),
        ("should_continue_news", "tools_news", "news"),
        ("should_continue_fundamentals", "tools_fundamentals", "fundamentals"),
    ],
)
def test_analyst_tool_cap_allows_tools_when_under_cap(method, tools_dest, role):
    logic = ConditionalLogic(max_analyst_tool_rounds=2)
    fn = getattr(logic, method)
    state = {
        "messages": [_msg_with_tools()],
        "analyst_tool_rounds": {role: 1},
    }
    assert fn(state) == tools_dest


def test_cap_zero_skips_tools_immediately():
    logic = ConditionalLogic(max_analyst_tool_rounds=0)
    state = {"messages": [_msg_with_tools()], "analyst_tool_rounds": {}}
    assert logic.should_continue_market(state) == "Msg Clear Market"


def test_negative_max_analyst_tool_rounds_raises():
    with pytest.raises(ValueError, match=">= 0"):
        ConditionalLogic(max_analyst_tool_rounds=-1)


def test_negative_override_raises():
    with pytest.raises(ValueError, match="max_analyst_tool_rounds_by_role"):
        ConditionalLogic(
            max_analyst_tool_rounds=5,
            max_analyst_tool_rounds_by_role={"news": -2},
        )


def test_per_role_override_cap():
    logic = ConditionalLogic(
        max_analyst_tool_rounds=2,
        max_analyst_tool_rounds_by_role={"news": 5},
    )
    assert logic._tool_round_cap("news") == 5
    assert logic._tool_round_cap("market") == 2


def test_merge_analyst_tool_rounds():
    assert merge_analyst_tool_rounds(None, None) == {}
    assert merge_analyst_tool_rounds({"market": 1}, {"news": 2}) == {
        "market": 1,
        "news": 2,
    }
    assert merge_analyst_tool_rounds({"market": 1}, {"market": 3}) == {"market": 3}


def test_propagator_initial_state_has_analyst_tool_rounds():
    p = Propagator(max_recur_limit=100)
    s = p.create_initial_state("ACME", "2024-01-02")
    assert s["analyst_tool_rounds"] == {}


def test_analyst_tool_lists_match_tool_names():
    from tradingagents.agents.utils import analyst_tool_lists as atl

    for fn in (
        atl.market_analyst_tools,
        atl.social_analyst_tools,
        atl.news_analyst_tools,
        atl.fundamentals_analyst_tools,
    ):
        tools = fn()
        names = [t.name for t in tools]
        assert len(names) == len(set(names)), f"duplicate tool name in {fn.__name__}"
