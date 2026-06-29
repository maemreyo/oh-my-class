from __future__ import annotations

import pytest

from packages.agents.prompts.compiler import PromptCompactionError, PromptCompiler
from packages.agents.prompts.registry import PromptModule, PromptRegistry


def _compiler_for(body: str) -> PromptCompiler:
    registry = PromptRegistry()
    registry.register(PromptModule.create(id="compact_v1", version="1.0.0", body=body))
    return PromptCompiler(registry)


def test_compaction_drops_examples_before_core_sections() -> None:
    body = "\n".join([
        "# Content Creator",
        "## Examples",
        "Example item. " * 30,
        "## Output Schema",
        "Return a JSON object with title and sections.",
        "## Safety Rules",
        "Answer keys in teacher_only only.",
        "## Teacher Must-Haves",
        "Grade {{grade}} {{subject}} {{language}} {{artifact_type}}.",
    ])

    result = _compiler_for(body).compile(
        module_id="compact_v1",
        variables={
            "grade": "5",
            "subject": "Math",
            "language": "vi-VN",
            "artifact_type": "quiz",
        },
        max_chars=260,
    )

    assert "Example item" not in result.compiled_body
    assert "Return a JSON object" in result.compiled_body
    assert "Answer keys in teacher_only only" in result.compiled_body
    assert "Grade 5 Math vi-VN quiz" in result.compiled_body
    assert result.metadata.compacted is True
    assert result.metadata.dropped_sections == ["Examples"]


def test_compaction_fails_when_core_sections_still_exceed_budget() -> None:
    body = "\n".join([
        "# Content Creator",
        "## Output Schema",
        "Return a JSON object with title and sections. " * 20,
        "## Safety Rules",
        "Answer keys in teacher_only only.",
    ])

    with pytest.raises(PromptCompactionError, match="core prompt exceeds"):
        _compiler_for(body).compile(module_id="compact_v1", variables={}, max_chars=120)
