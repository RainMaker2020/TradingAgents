"""Built-in SKILL.md registry and playbook tool."""
from __future__ import annotations

import pytest

from tradingagents.skills import (
    clear_skill_caches,
    get_skill,
    list_builtin_skill_ids,
    make_load_agent_playbook_tool,
    playbook_invocation_hint,
)
from pathlib import Path

from tradingagents.skills.loader import load_skill_file
import tradingagents.skills.registry as skills_registry


@pytest.fixture(autouse=True)
def _reset_skill_caches():
    yield
    clear_skill_caches()


def test_list_builtin_includes_core_analysts():
    ids = set(list_builtin_skill_ids())
    assert "market" in ids
    assert "news" in ids
    assert "chief_analyst" in ids


def test_get_skill_parses_frontmatter():
    doc = get_skill("market")
    assert doc is not None
    assert doc.skill_id == "market"
    assert "Market Analyst" in doc.name
    assert doc.body
    assert "Objective" in doc.body


def test_playbook_tool_returns_body():
    tool = make_load_agent_playbook_tool("news")
    assert tool.name == "load_agent_playbook"
    out = tool.invoke({})
    assert "News Analyst" in out or "news" in out.lower()


def test_playbook_invocation_hint_compact_by_default():
    hint = playbook_invocation_hint("fundamentals")
    assert "load_agent_playbook" in hint
    assert "`fundamentals`" in hint
    assert "`market`" in hint or "`news`" in hint
    assert "Available playbooks" not in hint


def test_playbook_invocation_hint_full_catalog_when_flagged():
    hint = playbook_invocation_hint(
        "fundamentals", include_full_playbook_catalog=True
    )
    assert "load_agent_playbook" in hint
    assert "Available playbooks" in hint
    assert "sibling agents" in hint


def test_loader_accepts_minimal_frontmatter(tmp_path):
    p = tmp_path / "SKILL.md"
    p.write_text(
        "---\nname: Test Skill\ndescription: A test.\n---\n\nBody line.\n",
        encoding="utf-8",
    )
    doc = load_skill_file(p, "test")
    assert doc.name == "Test Skill"
    assert doc.body.strip() == "Body line."


def test_builtin_market_skill_file_on_disk():
    root = Path(skills_registry.__file__).resolve().parent / "builtin" / "market" / "SKILL.md"
    assert root.is_file()


@pytest.mark.parametrize(
    "bad_id",
    ["", "..", "../market", "a/b", "a\\b", ".", "\x00x"],
)
def test_get_skill_rejects_unsafe_or_invalid_id(bad_id):
    assert get_skill(bad_id) is None


def test_get_skill_strips_whitespace_id():
    doc = get_skill("  market  ")
    assert doc is not None
    assert doc.skill_id == "market"
