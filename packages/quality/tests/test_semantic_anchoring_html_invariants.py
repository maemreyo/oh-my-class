from __future__ import annotations

from packages.quality.tests.test_semantic_anchoring_quality_gate import _cluster, _practice


def test_external_asset_references_hard_fail() -> None:
    from packages.quality.semantic_anchoring.gate import SemanticAnchoringQualityGate, SemanticAnchoringQualityInput

    result = SemanticAnchoringQualityGate().evaluate(SemanticAnchoringQualityInput(
        cluster=_cluster(),
        practice=_practice(),
        rendered_html='<link rel="stylesheet" href="https://cdn.example.com/app.css">',
    ))

    assert result.verdict == "failed"
    assert result.withhold_student_export is True
    assert result.issues[0].failure_class.value == "external_asset"
