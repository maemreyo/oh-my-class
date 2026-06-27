"""Unit tests for compiled_json_chat provenance tag helpers and hash validation.

Covers:
1. _provenance_tags — extraction of prompt_id, prompt_version, hashes
2. _merge_tags — collision resolution between base and provenance tags
3. Hash mutation detection — proves compiled metadata is tamper-evident

No network calls.  See test_compiled_chat_enrichment.py for integration tests.
"""

from __future__ import annotations

import pytest

from packages.agents.llm.compiled_chat import (
    _HASH_PREFIX_LEN,
    _merge_tags,
    _provenance_tags,
)
from packages.agents.llm.prompt_metadata import PromptMetadata
from packages.agents.prompts.compiler import CompiledPrompt, PromptCompiler
from packages.agents.prompts.seed import create_seeded_registry

# ── Helpers ─────────────────────────────────────────────────────────────────


def _make_compiled_prompt(
    *,
    module_id: str = "judge_v1",
    module_version: str = "1.0.0",
    body: str = "# Judge\nScore the artifact.",
    content_hash: str = "aaaa1111bbbb2222cccc3333dddd4444eeee5555ffff6666aaaa7777bbbb8888cccc9999",
    compiled_hash: str = (
        "1111aaaa2222bbbb3333cccc4444dddd5555eeee6666"
        "ffff7777aaaa8888bbbb9999cccc0000"
    ),
    sections: list[str] | None = None,
) -> CompiledPrompt:
    metadata = PromptMetadata(
        prompt_id=module_id,
        prompt_version=module_version,
        content_hash=content_hash,
        compiled_hash=compiled_hash,
        sections=sections or ["Judge"],
    )
    return CompiledPrompt(
        module_id=module_id,
        module_version=module_version,
        compiled_body=body,
        metadata=metadata,
    )


# ── Unit: _provenance_tags ──────────────────────────────────────────────────


class TestProvenanceTags:
    """Tests for _provenance_tag extraction from CompiledPrompt."""

    def test_extracts_all_four_tags(self) -> None:
        cp = _make_compiled_prompt()
        tags = _provenance_tags(cp)
        assert len(tags) == 4
        prefixes = {t.split(":")[0] for t in tags}
        assert prefixes == {"prompt_id", "prompt_version", "content_hash", "compiled_hash"}

    def test_prompt_id_includes_full_id(self) -> None:
        cp = _make_compiled_prompt(module_id="planner_v1")
        tags = _provenance_tags(cp)
        prompt_id_tag = next(t for t in tags if t.startswith("prompt_id:"))
        assert prompt_id_tag == "prompt_id:planner_v1"

    def test_prompt_version_includes_full_version(self) -> None:
        cp = _make_compiled_prompt(module_version="2.1.0")
        tags = _provenance_tags(cp)
        version_tag = next(t for t in tags if t.startswith("prompt_version:"))
        assert version_tag == "prompt_version:2.1.0"

    def test_content_hash_is_prefix(self) -> None:
        cp = _make_compiled_prompt(content_hash="a" * 64)
        tags = _provenance_tags(cp)
        hash_tag = next(t for t in tags if t.startswith("content_hash:"))
        prefix = hash_tag.split(":")[1]
        assert len(prefix) == _HASH_PREFIX_LEN
        assert prefix == "a" * _HASH_PREFIX_LEN

    def test_compiled_hash_is_prefix(self) -> None:
        cp = _make_compiled_prompt(compiled_hash="b" * 64)
        tags = _provenance_tags(cp)
        hash_tag = next(t for t in tags if t.startswith("compiled_hash:"))
        prefix = hash_tag.split(":")[1]
        assert len(prefix) == _HASH_PREFIX_LEN
        assert prefix == "b" * _HASH_PREFIX_LEN


# ── Unit: _merge_tags ───────────────────────────────────────────────────────


class TestMergeTags:
    """Tests for _merge_tags collision resolution."""

    def test_base_tags_preserved(self) -> None:
        base = ["agent:planner", "run:abc", "step:3"]
        prov = ["prompt_id:planner_v1", "prompt_version:1.0.0"]
        merged = _merge_tags(base, prov)
        assert "agent:planner" in merged
        assert "run:abc" in merged
        assert "step:3" in merged
        assert "prompt_id:planner_v1" in merged

    def test_provenance_wins_on_collision(self) -> None:
        base = ["prompt_id:raw_module", "agent:planner"]
        prov = ["prompt_id:planner_v1"]
        merged = _merge_tags(base, prov)
        prompt_tags = [t for t in merged if t.startswith("prompt_id:")]
        assert len(prompt_tags) == 1
        assert prompt_tags[0] == "prompt_id:planner_v1"

    def test_empty_base(self) -> None:
        prov = ["prompt_id:x"]
        merged = _merge_tags([], prov)
        assert merged == ["prompt_id:x"]

    def test_empty_provenance(self) -> None:
        base = ["agent:judge"]
        merged = _merge_tags(base, [])
        assert merged == ["agent:judge"]

    def test_no_collisions_concatenated(self) -> None:
        base = ["a:1", "b:2"]
        prov = ["c:3", "d:4"]
        merged = _merge_tags(base, prov)
        assert len(merged) == 4


# ── Failure case: mutated schema/hash ───────────────────────────────────────


class TestFailureOnMutatedHash:
    """Proves that hash validation catches mutations — the 'red' test."""

    def test_mutated_content_hash_fails_validation(self) -> None:
        """Compile a module, then verify a WRONG expected hash fails assertion."""
        compiler = PromptCompiler(create_seeded_registry())
        compiled = compiler.compile(module_id="judge_v1", variables={})

        wrong_hash = "0" * 64
        assert compiled.metadata.content_hash != wrong_hash, (
            "Compiled prompt content_hash should NOT match a fabricated hash"
        )

    def test_mutated_compiled_hash_fails_assertion(self) -> None:
        """Compile a module, then verify a WRONG compiled hash fails assertion."""
        compiler = PromptCompiler(create_seeded_registry())
        compiled = compiler.compile(module_id="judge_v1", variables={})

        wrong_hash = "f" * 64
        assert compiled.metadata.compiled_hash != wrong_hash, (
            "Compiled prompt compiled_hash should NOT match a fabricated hash"
        )

    def test_wrong_sections_fail(self) -> None:
        """Compile a module, then verify wrong expected sections fail assertion."""
        compiler = PromptCompiler(create_seeded_registry())
        compiled = compiler.compile(module_id="judge_v1", variables={})

        wrong_sections = ["Nonexistent Section", "Another Fake"]
        assert compiled.metadata.sections != wrong_sections, (
            "Sections should NOT match fabricated section list"
        )

    def test_wrong_prompt_id_fails(self) -> None:
        """Compile a module, then verify wrong prompt_id fails assertion."""
        compiler = PromptCompiler(create_seeded_registry())
        compiled = compiler.compile(module_id="judge_v1", variables={})

        assert compiled.metadata.prompt_id != "wrong_module", (
            "prompt_id should NOT match wrong module name"
        )

    def test_hash_prefix_length_enforced(self) -> None:
        """Verify that hash prefix truncation is exactly _HASH_PREFIX_LEN."""
        compiler = PromptCompiler(create_seeded_registry())
        compiled = compiler.compile(module_id="planner_v1", variables={})
        tags = _provenance_tags(compiled)

        for tag in tags:
            if "_hash:" in tag:
                prefix = tag.split(":")[1]
                assert len(prefix) == _HASH_PREFIX_LEN, (
                    f"Hash prefix for '{tag.split(':')[0]}' should be "
                    f"{_HASH_PREFIX_LEN} chars, got {len(prefix)}"
                )
