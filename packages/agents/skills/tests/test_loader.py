"""Tests for SK2 SkillLoader — registry, SKILL.md loading, XML block assembly."""
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from packages.agents.skills.loader import SkillLoader

if TYPE_CHECKING:
    from pathlib import Path


def test_build_skills_block_structure():
    loader = SkillLoader()
    block = loader.build_skills_block(["bloom_taxonomy"])
    assert block.startswith("<available_skills>")
    assert block.endswith("</available_skills>")
    assert '<skill name="bloom_taxonomy">' in block


def test_empty_skills_returns_empty_string():
    loader = SkillLoader()
    assert loader.build_skills_block([]) == ""


def test_unknown_skill_raises_key_error():
    loader = SkillLoader()
    with pytest.raises(KeyError, match="not registered"):
        loader.build_skills_block(["nonexistent_skill"])


def test_missing_file_raises_file_not_found(tmp_path: Path):
    fake_map = {"ghost": tmp_path / "ghost.md"}  # file doesn't exist
    loader = SkillLoader(skills_map=fake_map)
    with pytest.raises(FileNotFoundError):
        loader.load_skill("ghost")


def test_multiple_skills_all_present():
    loader = SkillLoader()
    block = loader.build_skills_block(["bloom_taxonomy", "hsa_exam_prep"])
    assert '<skill name="bloom_taxonomy">' in block
    assert '<skill name="hsa_exam_prep">' in block


def test_list_available_returns_all_registered():
    loader = SkillLoader()
    available = loader.list_available()
    assert "ccss_math" in available
    assert "bloom_taxonomy" in available
    assert len(available) >= 5


def test_skill_content_is_non_empty():
    loader = SkillLoader()
    content = loader.load_skill("bloom_taxonomy")
    assert len(content) > 50
    assert "Bloom" in content or "bloom" in content


def test_ccss_math_loads():
    loader = SkillLoader()
    block = loader.build_skills_block(["ccss_math"])
    assert "Common Core" in block or "CCSS" in block or "ccss" in block.lower()


def test_hsa_exam_format_in_block():
    loader = SkillLoader()
    block = loader.build_skills_block(["hsa_exam_prep"])
    assert "HSA" in block
    assert "A, B, C, D" in block


def test_zamery_pack_loads():
    loader = SkillLoader()
    block = loader.build_skills_block(["zamery_pack"])
    assert "Zamery" in block or "zamery" in block.lower()
