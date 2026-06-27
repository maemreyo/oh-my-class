from __future__ import annotations

from common.contracts.quality import (
    ArtifactQualityReport,
    HealingDecision,
    HealingStrategy,
    QualityFailureClass,
    QualityIssue,
)


def test_quality_report_model_dump_roundtrip() -> None:
    report = ArtifactQualityReport(
        artifact_id="lesson-1",
        artifact_type="lesson",
        passed=False,
        issues=[
            QualityIssue(
                failure_class=QualityFailureClass.ANSWER_KEY_LEAKAGE,
                location="sections[0].content",
                message="answer leaked",
            ),
        ],
    )

    roundtrip = ArtifactQualityReport.model_validate(report.model_dump(mode="python"))

    assert roundtrip == report


def test_healing_decision_is_typed() -> None:
    decision = HealingDecision(
        failure_class=QualityFailureClass.SCHEMA_INVALID,
        strategy=HealingStrategy.SCHEMA_REPAIR,
        max_attempts=2,
    )

    assert decision.model_dump(mode="python") == {
        "failure_class": QualityFailureClass.SCHEMA_INVALID,
        "strategy": HealingStrategy.SCHEMA_REPAIR,
        "max_attempts": 2,
    }
