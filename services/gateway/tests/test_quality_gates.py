from __future__ import annotations

from datetime import UTC, datetime

from common.contracts.quality import HealingStrategy, QualityFailureClass
from services.gateway.teaching_pack_snapshot_store import ArtifactSnapshotRead
from services.gateway.teaching_pack_types import RunId
from services.gateway.quality_gates import (
    classify_healing,
    export_readiness,
    pre_search_safety,
    validate_artifact_quality,
    validate_snapshot_publish_quality,
)


def test_artifact_quality_blocks_placeholder_answer_key_and_missing_accessibility() -> None:
    report = validate_artifact_quality(
        artifact_id="quiz-1",
        artifact={
            "artifact_type": "quiz",
            "title": "Quiz Artifact",
            "sections": [{"content": "TODO answer: 42"}],
        },
    )

    assert report.passed is False
    assert [issue.failure_class for issue in report.issues] == [
        QualityFailureClass.PLACEHOLDER_CONTENT,
        QualityFailureClass.ANSWER_KEY_LEAKAGE,
        QualityFailureClass.MISSING_ACCESSIBILITY,
    ]


def test_artifact_quality_passes_valid_teacher_only_answer_key() -> None:
    report = validate_artifact_quality(
        artifact_id="quiz-1",
        artifact={
            "artifact_type": "quiz",
            "title": "Quiz Artifact",
            "sections": [
                {"content": "Student question"},
                {"content": "answer: 42", "teacher_only": True},
            ],
            "accessibility": {"language": "en", "alt_texts": {}},
        },
    )

    assert report.passed is True
    assert report.issues == []


def test_snapshot_publish_quality_blocks_external_asset_and_student_key_leak() -> None:
    snapshot = _snapshot(
        standalone_valid=False,
        student_html="<!DOCTYPE html><html><body>Answer Key: 42</body></html>",
    )

    report = validate_snapshot_publish_quality(snapshot)

    assert report.passed is False
    assert [issue.failure_class for issue in report.issues] == [
        QualityFailureClass.EXTERNAL_ASSET,
        QualityFailureClass.ANSWER_KEY_LEAKAGE,
    ]


def test_pre_search_safety_blocks_student_pii() -> None:
    report = pre_search_safety("Find examples for student email mai@example.com")

    assert report.passed is False
    assert report.issues[0].failure_class is QualityFailureClass.PII_LEAKAGE


def test_healing_classifier_maps_failure_to_bounded_strategy() -> None:
    decision = classify_healing(QualityFailureClass.ANSWER_KEY_LEAKAGE)

    assert decision.strategy is HealingStrategy.ANSWER_KEY_REPAIR
    assert decision.max_attempts == 2


def test_healing_classifier_routes_factual_uncertainty_to_research_enrichment() -> None:
    decision = classify_healing(QualityFailureClass.FACTUAL_UNCERTAINTY)

    assert decision.strategy is HealingStrategy.RESEARCH_ENRICHMENT
    assert decision.max_attempts == 1


def test_healing_classifier_routes_pedagogical_mismatch_to_blueprint_replan() -> None:
    decision = classify_healing(QualityFailureClass.PEDAGOGICAL_MISMATCH)

    assert decision.strategy is HealingStrategy.REPLAN_BLUEPRINT
    assert decision.max_attempts == 1


def test_export_readiness_requires_approved_standalone_required_artifacts() -> None:
    report = export_readiness(
        run_id=RunId("run-1"),
        snapshots=[_snapshot(artifact_type="lesson", approved=True)],
        required_artifact_types=("lesson", "quiz"),
    )

    assert report.passed is False
    assert report.approved_snapshot_ids == ["snapshot-1"]
    assert report.issues[0].failure_class is QualityFailureClass.EXPORT_NOT_READY


def _snapshot(
    *,
    artifact_type: str = "lesson",
    standalone_valid: bool = True,
    student_html: str = "<!DOCTYPE html><html><body>oh-my-class</body></html>",
    approved: bool = False,
) -> ArtifactSnapshotRead:
    return ArtifactSnapshotRead(
        snapshot_id="snapshot-1",
        run_id=RunId("run-1"),
        artifact_id="artifact-1",
        artifact_type=artifact_type,
        content_hash="0" * 64,
        html_hash="1" * 64,
        content_json={"title": "Lesson"},
        rendered_html="<!DOCTYPE html><html><body>oh-my-class</body></html>",
        student_rendered_html=student_html,
        renderer_version="renderer@test",
        template_version="template@test",
        theme_version="theme@test",
        standalone_valid=standalone_valid,
        approved_at=datetime.now(UTC) if approved else None,
    )
