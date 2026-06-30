from __future__ import annotations

from common.contracts.tests.inverse_thinking_fixtures import english_grammar_pack
from packages.agents.inverse_thinking_pipeline import (
    InverseThinkingPipelineRequest,
    inverse_thinking_pipeline,
)


def test_blueprint_carries_inverse_thinking_methodology_payload() -> None:
    request = InverseThinkingPipelineRequest(
        teacher_request="Use inverse thinking for present perfect.",
        artifact_types=["lesson"],
        feature_flags={"inverse_thinking_v1": True},
        canonical_pack=english_grammar_pack(),
    )

    result = inverse_thinking_pipeline(request)

    methodology = result.lesson_blueprint["methodology"]

    assert methodology["tags"] == ["inverse_thinking"]
    assert methodology["payloads"]["inverse_thinking"]["methodology"] == "inverse_thinking"
