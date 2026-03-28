"""LangChain tool: load this node's dedicated SKILL.md body into context."""
from __future__ import annotations

from langchain_core.tools import StructuredTool

from tradingagents.skills.registry import (
    catalog_lines_for_prompt,
    get_skill,
    list_builtin_skill_ids,
)


def make_load_agent_playbook_tool(skill_id: str) -> StructuredTool:
    """Return a zero-arg tool bound to one skill (each graph node gets its own instance)."""
    meta = get_skill(skill_id)
    desc = (
        meta.description
        if meta
        else "Load your dedicated workflow playbook for this analyst role."
    )

    def _load() -> str:
        doc = get_skill(skill_id)
        if doc is None:
            return (
                f"[Playbook `{skill_id}` not found on disk. "
                "Proceed using your default instructions.]"
            )
        return f"# {doc.name}\n\n{doc.body}"
    return StructuredTool.from_function(
        name="load_agent_playbook",
        description=(
            "Load your full workflow playbook (SKILL) for this role. "
            "Call at most once at the start of your analysis turn, then follow it "
            "when choosing tools and writing your report. "
            f"{desc}"
        ),
        func=_load,
    )


def playbook_invocation_hint(
    skill_id: str,
    *,
    include_full_playbook_catalog: bool = False,
) -> str:
    """Point analysts at ``load_agent_playbook`` without embedding every SKILL body.

    By default uses a **compact catalog** (playbook IDs + your title only) to save
    tokens. Set ``include_full_playbook_catalog=True`` for the legacy verbose
    catalog (name + description per skill), e.g. debugging or admin prompts.
    """
    doc = get_skill(skill_id)
    norm = doc.skill_id if doc else skill_id.strip()
    title = doc.name if doc else norm
    all_ids = list_builtin_skill_ids()
    peer_ids = sorted(x for x in all_ids if x != norm)
    peer_labels = ", ".join(f"`{x}`" for x in peer_ids)

    if include_full_playbook_catalog:
        blurb = doc.description if doc else ""
        base = (
            f"You have a dedicated workflow playbook (**{title}**). "
            f"Optional first step: call **load_agent_playbook** once to load the full "
            f"SKILL instructions into the conversation, then execute your analysis. "
            f"{blurb}"
        )
        catalog = catalog_lines_for_prompt(all_ids)
        if not catalog.strip():
            return base
        return (
            f"{base}\n\n"
            f"{catalog}\n"
            "You may only **invoke** your own playbook via `load_agent_playbook`; "
            "other rows describe sibling agents in this pipeline.\n"
        )

    peers_clause = (
        peer_labels
        if peer_labels
        else "*(no other built-in playbooks discovered)*"
    )
    return (
        f"**Your playbook:** `{norm}` — {title}. "
        f"**Other playbook IDs in this graph** (IDs only; full markdown **not** loaded here): {peers_clause}. "
        "Call **load_agent_playbook** once at the start of your turn if you need the detailed SKILL workflow; "
        "otherwise rely on your role instructions below. "
        "You may only invoke **your** playbook via `load_agent_playbook`.\n"
    )


def inject_playbook_block(skill_id: str, base_prompt: str) -> str:
    """Prepend playbook body for agents that do not use a tool loop."""
    doc = get_skill(skill_id)
    if doc is None or not doc.body.strip():
        return base_prompt
    header = f"## Dedicated playbook: {doc.name}\n\n{doc.body}\n\n---\n\n"
    return header + base_prompt
