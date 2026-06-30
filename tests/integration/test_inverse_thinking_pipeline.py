from __future__ import annotations

from common.contracts.tests.inverse_thinking_fixtures import english_grammar_pack
from packages.agents.inverse_thinking_pipeline import (
    InverseThinkingPipelineRequest,
    inverse_thinking_pipeline,
)


def test_inverse_thinking_pipeline_stores_one_canonical_pack_and_derives_selected_projections() -> None:
    request = InverseThinkingPipelineRequest(
        teacher_request="Use inverse thinking for present perfect.",
        artifact_types=["lesson", "quiz"],
        feature_flags={"inverse_thinking_v1": True},
        canonical_pack=english_grammar_pack(),
    )

    result = inverse_thinking_pipeline(request)

    assert result.canonical_pack.methodology == "inverse_thinking"
    assert list(result.projections) == ["lesson", "quiz"]
    assert result.projections["lesson"].case_ids == result.projections["quiz"].case_ids
