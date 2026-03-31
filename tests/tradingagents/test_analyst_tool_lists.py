"""Contract tests: `analyst_tool_lists` is the only place that defines per-role tool sets.

`ToolNode` in `trading_graph._create_tool_nodes` and `llm.bind_tools` in `create_*_analyst`
must both call the same `*_analyst_tools()` functions so tools stay aligned.
"""

from __future__ import annotations

import pytest

from tradingagents.agents.utils import analyst_tool_lists as atl
from tradingagents.agents.utils.core_stock_tools import get_stock_data
from tradingagents.agents.utils.fundamental_data_tools import (
    get_balance_sheet,
    get_cashflow,
    get_fundamentals,
    get_income_statement,
)
from tradingagents.agents.utils.news_data_tools import (
    get_global_news,
    get_insider_transactions,
    get_news,
)
from tradingagents.agents.utils.technical_indicators_tools import get_indicators


@pytest.mark.parametrize(
    "fn",
    [
        atl.market_analyst_tools,
        atl.social_analyst_tools,
        atl.news_analyst_tools,
        atl.fundamentals_analyst_tools,
    ],
)
def test_each_role_returns_non_empty_tool_list(fn):
    tools = fn()
    assert len(tools) >= 1
    assert all(getattr(t, "name", None) for t in tools)


def test_two_calls_same_tool_names_same_order():
    """Playbook tool may be a new instance each call; names must still match."""
    for fn in (
        atl.market_analyst_tools,
        atl.social_analyst_tools,
        atl.news_analyst_tools,
        atl.fundamentals_analyst_tools,
    ):
        a, b = fn(), fn()
        assert [t.name for t in a] == [t.name for t in b]


def test_market_tool_callables_use_module_singletons():
    """Non-playbook tools are shared module callables — same object for graph vs analyst."""
    a, b = atl.market_analyst_tools(), atl.market_analyst_tools()
    assert a[1] is b[1] is get_stock_data
    assert a[2] is b[2] is get_indicators


def test_social_tool_callables_use_module_singletons():
    a, b = atl.social_analyst_tools(), atl.social_analyst_tools()
    assert a[1] is b[1] is get_news


def test_news_tool_callables_use_module_singletons():
    a, b = atl.news_analyst_tools(), atl.news_analyst_tools()
    assert a[1] is b[1] is get_news
    assert a[2] is b[2] is get_global_news
    assert a[3] is b[3] is get_insider_transactions


def test_fundamentals_tool_callables_use_module_singletons():
    a, b = atl.fundamentals_analyst_tools(), atl.fundamentals_analyst_tools()
    assert a[1] is b[1] is get_fundamentals
    assert a[2] is b[2] is get_balance_sheet
    assert a[3] is b[3] is get_cashflow
    assert a[4] is b[4] is get_income_statement
