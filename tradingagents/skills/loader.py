"""Parse SKILL.md files: YAML frontmatter (name, description) + markdown body."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# Hard cap before read_text to protect context windows and memory.
MAX_PLAYBOOK_SIZE_BYTES = 25 * 1024


@dataclass(frozen=True)
class SkillDocument:
    skill_id: str
    name: str
    description: str
    body: str


def _parse_simple_frontmatter(raw: str) -> tuple[dict[str, str], str]:
    """Minimal frontmatter parser (no PyYAML): ``---`` / key: value / ``---``."""
    if not raw.lstrip().startswith("---"):
        return {}, raw
    lines = raw.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, raw
    meta_lines: list[str] = []
    i = 1
    while i < len(lines):
        if lines[i].strip() == "---":
            break
        meta_lines.append(lines[i])
        i += 1
    else:
        return {}, raw
    body = "\n".join(lines[i + 1 :]).lstrip("\n")
    meta: dict[str, str] = {}
    for line in meta_lines:
        if ":" not in line:
            continue
        key, _, rest = line.partition(":")
        k = key.strip()
        v = rest.strip().strip('"').strip("'")
        if k:
            meta[k] = v
    return meta, body


def _placeholder_skill(skill_id: str, detail: str) -> SkillDocument:
    body = (
        f"**Error:** Playbook `{skill_id}` is unavailable ({detail}). "
        "Proceed using your base role instructions only. "
        "**System risk:** Flag in your report that the playbook did not load.\n"
    )
    return SkillDocument(
        skill_id=skill_id,
        name="Playbook unavailable (system)",
        description="Placeholder after load failure or size limit.",
        body=body,
    )


def load_skill_file(path: Path, skill_id: str) -> SkillDocument:
    """Load SKILL.md; never raises — returns a placeholder document on failure."""
    try:
        size = path.stat().st_size
    except OSError as exc:
        logger.warning("skill stat failed skill_id=%s path=%s: %s", skill_id, path, exc)
        return _placeholder_skill(skill_id, "filesystem stat error")

    if size > MAX_PLAYBOOK_SIZE_BYTES:
        logger.warning(
            "skill too large skill_id=%s bytes=%s max=%s",
            skill_id,
            size,
            MAX_PLAYBOOK_SIZE_BYTES,
        )
        return _placeholder_skill(
            skill_id,
            f"file exceeds {MAX_PLAYBOOK_SIZE_BYTES} bytes",
        )

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning("skill read failed skill_id=%s: %s", skill_id, exc)
        return _placeholder_skill(skill_id, "read error")
    except UnicodeDecodeError as exc:
        logger.warning("skill decode failed skill_id=%s: %s", skill_id, exc)
        return _placeholder_skill(skill_id, "encoding error")

    try:
        meta, body = _parse_simple_frontmatter(text)
        name = meta.get("name", skill_id)
        description = meta.get(
            "description", "Workflow playbook for this agent role."
        )
        return SkillDocument(
            skill_id=skill_id,
            name=name,
            description=description,
            body=body.strip(),
        )
    except Exception as exc:  # noqa: BLE001 — defensive parse guard
        logger.warning("skill parse failed skill_id=%s: %s", skill_id, exc)
        return _placeholder_skill(skill_id, "parse error")
