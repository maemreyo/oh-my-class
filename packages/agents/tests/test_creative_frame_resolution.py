from __future__ import annotations

from common.contracts.tests.inverse_thinking_fixtures import english_grammar_pack
from packages.agents.inverse_thinking_pipeline import (
    InverseThinkingPipelineRequest,
    inverse_thinking_pipeline,
)


def test_auto_creative_frame_resolves_with_rationale() -> None:
    pack = english_grammar_pack()
    pack["creative_frame"] = "auto"
    request = InverseThinkingPipelineRequest(
        teacher_request="Make this a detective style inverse thinking lesson.",
        artifact_types=["lesson"],
        feature_flags={"inverse_thinking_v1": True},
        canonical_pack=pack,
    )

    result = inverse_thinking_pipeline(request)

    assert result.visual_spec["creative_frame"] == "detective_case"
    assert "rationale" in result.visual_spec


def test_explicit_creative_frame_is_preserved_with_rationale() -> None:
    pack = english_grammar_pack()
    pack["creative_frame"] = "survival_guide"
    request = InverseThinkingPipelineRequest(
        teacher_request="Use survival guide framing.",
        artifact_types=["lesson"],
        feature_flags={"inverse_thinking_v1": True},
        canonical_pack=pack,
    )

    result = inverse_thinking_pipeline(request)

    assert result.visual_spec["creative_frame"] == "survival_guide"
    assert result.visual_spec["rationale"] == "teacher_or_pack_selected"
