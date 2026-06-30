from __future__ import annotations

from common.contracts.tests.inverse_thinking_fixtures import english_grammar_pack
from packages.agents.inverse_thinking_pipeline import (
    InverseThinkingPipelineRequest,
    inverse_thinking_pipeline,
)


def test_inverse_thinking_metadata_tags_include_methodology_frame_flag_and_repair_attempt() -> None:
    request = InverseThinkingPipelineRequest(
        teacher_request="Use inverse thinking for present perfect.",
        artifact_types=["lesson"],
        feature_flags={"inverse_thinking_v1": True},
        canonical_pack=english_grammar_pack(),
        repair_attempt=2,
    )

    result = inverse_thinking_pipeline(request)

    assert "methodology:inverse_thinking" in result.metadata_tags
    assert "creative_frame:detective_case" in result.metadata_tags
    assert "feature_flag:inverse_thinking_v1" in result.metadata_tags
    assert "repair_attempt:2" in result.metadata_tags
