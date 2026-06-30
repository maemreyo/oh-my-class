from __future__ import annotations

import pytest

from common.contracts.tests.inverse_thinking_fixtures import english_grammar_pack
from packages.agents.inverse_thinking_pipeline import (
    InverseThinkingPipelineRequest,
    inverse_thinking_pipeline,
)


def test_repeated_inverse_thinking_failure_escalates_without_standard_lesson_downgrade() -> None:
    payload = english_grammar_pack()
    payload["cases"][0]["safe_zone"] = "Remember the tense name."
    request = InverseThinkingPipelineRequest(
        teacher_request="Use inverse thinking for present perfect.",
        artifact_types=["lesson"],
        feature_flags={"inverse_thinking_v1": True},
        canonical_pack=payload,
        repair_attempt=3,
    )

    with pytest.raises(ValueError, match="inverse-thinking quality gate failed"):
        inverse_thinking_pipeline(request)
