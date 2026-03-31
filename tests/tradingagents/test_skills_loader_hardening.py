"""Skill loader size limits and graceful degradation."""
from __future__ import annotations

from pathlib import Path

from tradingagents.skills.loader import MAX_PLAYBOOK_SIZE_BYTES, load_skill_file


def test_load_skill_file_oversized_returns_placeholder(tmp_path: Path):
    p = tmp_path / "SKILL.md"
    p.write_bytes(b"x" * (MAX_PLAYBOOK_SIZE_BYTES + 1))
    doc = load_skill_file(p, "x")
    assert "unavailable" in doc.name.lower()
    assert "exceeds" in doc.body.lower() or "bytes" in doc.body.lower()


def test_load_skill_file_bad_encoding_returns_placeholder(tmp_path: Path):
    p = tmp_path / "SKILL.md"
    # Invalid UTF-8 sequence (lone high bit bytes)
    p.write_bytes(b"---\nname: Z\n---\n\n\xc3\x28")
    doc = load_skill_file(p, "z")
    assert "encoding" in doc.body.lower() or "unavailable" in doc.name.lower()


def test_load_skill_file_valid(tmp_path: Path):
    p = tmp_path / "SKILL.md"
    p.write_text(
        "---\nname: Good\ndescription: d\n---\n\nBody.\n",
        encoding="utf-8",
    )
    doc = load_skill_file(p, "good")
    assert doc.name == "Good"
    assert doc.body == "Body."
