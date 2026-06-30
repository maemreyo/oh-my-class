from __future__ import annotations

from common.contracts.tests.inverse_thinking_fixtures import english_grammar_pack
from packages.agents.inverse_thinking_pipeline import (
    InverseThinkingPipelineRequest,
    inverse_thinking_pipeline,
)
from packages.renderer.inverse_thinking_html import render_release_fixture_html


def test_inverse_thinking_release_flow_generates_approves_and_exports_standalone_html() -> None:
    result = inverse_thinking_pipeline(
        InverseThinkingPipelineRequest(
            teacher_request="Use inverse thinking for present perfect.",
            artifact_types=["lesson", "worksheet", "quiz", "drill"],
            feature_flags={"inverse_thinking_v1": True},
            canonical_pack=english_grammar_pack(),
        ),
    )

    html = render_release_fixture_html(result.canonical_pack, artifact_type="worksheet")

    assert result.projections["lesson"].case_ids == ["case-present-perfect"]
    assert "<!DOCTYPE html>" in html
    assert "oh-my-class" in html
    assert "case-file" in html
    assert "Summary table" in html
    assert "Evidence worksheet practice" in html
    assert "She met him last week" not in html
    assert "http://" not in html
    assert "https://" not in html
