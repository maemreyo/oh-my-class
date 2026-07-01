from __future__ import annotations

from packages.quality.tests.test_semantic_anchoring_quality_gate import _cluster, _practice


def test_teacher_only_notes_in_student_projection_hard_fail() -> None:
    from packages.quality.semantic_anchoring.gate import SemanticAnchoringQualityGate, SemanticAnchoringQualityInput

    result = SemanticAnchoringQualityGate().evaluate(SemanticAnchoringQualityInput(
        cluster=_cluster(),
        practice=_practice(),
        student_projection={"cards": [{"word": "fare", "teacher_script_vi": "Teacher only"}]},
    ))

    assert result.verdict == "failed"
    assert result.withhold_student_export is True
    assert result.issues[0].failure_class.value == "answer_key_leakage"
    assert result.issues[0].hard_block is True
