from __future__ import annotations

import pytest

from common.contracts.tests.inverse_thinking_fixtures import english_grammar_pack
from packages.agents.inverse_thinking_pipeline import (
    InverseThinkingPipelineRequest,
    inverse_thinking_pipeline,
)


def test_inverse_thinking_v1_supports_lesson_worksheet_quiz_and_drill_only() -> None:
    request = InverseThinkingPipelineRequest(
        teacher_request="Use inverse thinking for present perfect.",
        artifact_types=["lesson", "worksheet", "quiz", "drill"],
        feature_flags={"inverse_thinking_v1": True},
        canonical_pack=english_grammar_pack(),
    )

    result = inverse_thinking_pipeline(request)

    assert list(result.projections) == ["lesson", "worksheet", "quiz", "drill"]


def test_inverse_thinking_v1_rejects_unsupported_infographic_scope() -> None:
    request = InverseThinkingPipelineRequest(
        teacher_request="Use inverse thinking for present perfect.",
        artifact_types=["lesson", "infographic"],
        feature_flags={"inverse_thinking_v1": True},
        canonical_pack=english_grammar_pack(),
    )

    with pytest.raises(ValueError, match="infographic"):
        inverse_thinking_pipeline(request)
