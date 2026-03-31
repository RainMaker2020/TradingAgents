"""Canonical tool lists per analyst role — shared by ToolNode and bind_tools (single source of truth)."""

from __future__ import annotations

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
from tradingagents.skills import make_load_agent_playbook_tool


def market_analyst_tools():
    return [
        make_load_agent_playbook_tool("market"),
        get_stock_data,
        get_indicators,
    ]


def social_analyst_tools():
    return [
        make_load_agent_playbook_tool("social"),
        get_news,
    ]


def news_analyst_tools():
    return [
        make_load_agent_playbook_tool("news"),
        get_news,
        get_global_news,
        get_insider_transactions,
    ]


def fundamentals_analyst_tools():
    return [
        make_load_agent_playbook_tool("fundamentals"),
        get_fundamentals,
        get_balance_sheet,
        get_cashflow,
        get_income_statement,
    ]
