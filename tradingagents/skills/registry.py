"""Discover and cache built-in SKILL.md playbooks under ``builtin/<skill_id>/``."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from tradingagents.skills.loader import SkillDocument, load_skill_file

_BUILTIN_ROOT = Path(__file__).resolve().parent / "builtin"


def _normalize_skill_id(skill_id: str) -> str | None:
    """Reject path segments and traversal so ``skill_id`` cannot escape ``builtin``."""
    if not isinstance(skill_id, str):
        return None
    s = skill_id.strip()
    if not s or s in (".", ".."):
        return None
    if "/" in s or "\\" in s or "\x00" in s:
        return None
    # Single path component only (no "a/b" or "a\\b")
    if Path(s).name != s:
        return None
    try:
        root = _BUILTIN_ROOT.resolve()
        candidate_dir = (root / s).resolve()
    except OSError:
        return None
    if not candidate_dir.is_relative_to(root):
        return None
    # Direct child of builtin only (handles symlinks escaping root)
    if candidate_dir.parent != root:
        return None
    return s


@lru_cache(maxsize=1)
def list_builtin_skill_ids() -> tuple[str, ...]:
    if not _BUILTIN_ROOT.is_dir():
        return ()
    ids: list[str] = []
    for child in sorted(_BUILTIN_ROOT.iterdir()):
        if child.is_dir() and (child / "SKILL.md").is_file():
            norm = _normalize_skill_id(child.name)
            if norm is not None:
                ids.append(norm)
    return tuple(ids)


@lru_cache(maxsize=64)
def _get_skill_cached(norm: str) -> SkillDocument | None:
    path = _BUILTIN_ROOT / norm / "SKILL.md"
    if not path.is_file():
        return None
    return load_skill_file(path, norm)


def get_skill(skill_id: str) -> SkillDocument | None:
    norm = _normalize_skill_id(skill_id)
    if norm is None:
        return None
    return _get_skill_cached(norm)


def catalog_lines_for_prompt(skill_ids: tuple[str, ...]) -> str:
    """Compact list of skills (name + description) for system prompts.

    Used when ``playbook_invocation_hint(..., include_full_playbook_catalog=True)``.
    Also available for CLI/admin surfaces.
    """
    lines: list[str] = []
    for sid in skill_ids:
        norm = _normalize_skill_id(sid)
        if norm is None:
            continue
        doc = _get_skill_cached(norm)
        if doc is None:
            continue
        lines.append(f"- **{doc.name}** (`{norm}`): {doc.description}")
    if not lines:
        return ""
    return "## Available playbooks\n" + "\n".join(lines) + "\n"


def clear_skill_caches() -> None:
    list_builtin_skill_ids.cache_clear()
    _get_skill_cached.cache_clear()
