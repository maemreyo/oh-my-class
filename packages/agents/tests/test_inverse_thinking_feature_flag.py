from __future__ import annotations

import pytest

from common.contracts.tests.inverse_thinking_fixtures import english_grammar_pack
from packages.agents.inverse_thinking_pipeline import (
    InverseThinkingPipelineRequest,
    inverse_thinking_pipeline,
)


def test_inverse_thinking_request_fails_closed_when_feature_flag_disabled() -> None:
    request = InverseThinkingPipelineRequest(
        teacher_request="Use inverse thinking for present perfect.",
        artifact_types=["lesson"],
        feature_flags={"inverse_thinking_v1": False},
        canonical_pack=english_grammar_pack(),
    )

    with pytest.raises(ValueError, match="inverse_thinking_v1"):
        inverse_thinking_pipeline(request)
