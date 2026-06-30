from __future__ import annotations

from common.contracts.tests.inverse_thinking_fixtures import english_grammar_pack
from packages.agents.inverse_thinking_pipeline import InverseThinkingPipelineRequest, inverse_thinking_pipeline


def test_pipeline_scrubs_teacher_request_and_pack_before_projection() -> None:
    pack = english_grammar_pack()
    pack["cases"][0]["student_task"] = "Help Nguyễn Văn An inspect learner@example.com before rewriting."
    request = InverseThinkingPipelineRequest(
        teacher_request="Use detective style for Nguyễn Văn An, phone 0912 345 678.",
        artifact_types=["lesson"],
        feature_flags={"inverse_thinking_v1": True},
        canonical_pack=pack,
    )

    result = inverse_thinking_pipeline(request)
    rendered_state = str(result.model_dump())

    assert "Nguyễn Văn An" not in rendered_state
    assert "learner@example.com" not in rendered_state
    assert "0912 345 678" not in rendered_state
    assert result.pii_audit_event.redaction_counts["person_name"] == 2
    assert result.pii_audit_event.redaction_counts["email"] == 1
    assert result.pii_audit_event.redaction_counts["phone"] == 1
