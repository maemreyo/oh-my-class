from __future__ import annotations

import re
from typing import TYPE_CHECKING, assert_never

from pydantic import ValidationError

from common.contracts.artifact import ArtifactContent
from common.contracts.quality import (
    ArtifactQualityReport,
    ExportReadinessReport,
    HealingDecision,
    HealingStrategy,
    QualityFailureClass,
    QualityIssue,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from services.gateway.pipeline_v2_snapshot_store import ArtifactSnapshotRead
    from services.gateway.pipeline_v2_types import JsonObject, RunId

_PLACEHOLDER_PATTERN = re.compile(
    r"\b(?:todo|placeholder|lorem ipsum|tbd)\b|\[tbd\]",
    re.IGNORECASE,
)
_ANSWER_KEY_PATTERN = re.compile(
    r"\b(?:answer key|answer:|correct:|solution:)",
    re.IGNORECASE,
)
_PII_PATTERN = re.compile(
    r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b|"
    r"\b(?:student|pupil)\s+(?:name|email|phone)\b",
    re.IGNORECASE,
)


def validate_artifact_quality(artifact_id: str, artifact: JsonObject) -> ArtifactQualityReport:
    issues: list[QualityIssue] = []
    try:
        parsed = ArtifactContent.model_validate(artifact)
    except ValidationError as exc:
        return ArtifactQualityReport(
            artifact_id=artifact_id,
            artifact_type=str(artifact.get("artifact_type", "unknown")),
            passed=False,
            issues=[_issue(QualityFailureClass.SCHEMA_INVALID, "artifact", str(exc))],
        )
    issues.extend(_scan_placeholder(parsed))
    issues.extend(_scan_student_answer_keys(parsed))
    issues.extend(_scan_artifact_pii(parsed))
    issues.extend(_scan_accessibility(parsed))
    return _artifact_report(artifact_id, parsed, issues)


def validate_artifact_content(artifact_id: str, artifact: ArtifactContent) -> ArtifactQualityReport:
    issues: list[QualityIssue] = []
    issues.extend(_scan_placeholder(artifact))
    issues.extend(_scan_student_answer_keys(artifact))
    issues.extend(_scan_artifact_pii(artifact))
    issues.extend(_scan_accessibility(artifact))
    return _artifact_report(artifact_id, artifact, issues)


def validate_snapshot_publish_quality(snapshot: ArtifactSnapshotRead) -> ArtifactQualityReport:
    issues: list[QualityIssue] = []
    if not snapshot.standalone_valid:
        issues.append(_issue(
            QualityFailureClass.EXTERNAL_ASSET,
            "rendered_html",
            "rendered HTML is not standalone",
        ))
    if "<!doctype html" not in snapshot.rendered_html.lower():
        issues.append(_issue(
            QualityFailureClass.MISSING_DOCTYPE,
            "rendered_html",
            "rendered HTML is missing doctype",
        ))
    if _ANSWER_KEY_PATTERN.search(snapshot.student_rendered_html):
        issues.append(_issue(
            QualityFailureClass.ANSWER_KEY_LEAKAGE,
            "student_rendered_html",
            "student preview contains answer-key text",
        ))
    if _PII_PATTERN.search(snapshot.student_rendered_html):
        issues.append(_issue(
            QualityFailureClass.PII_LEAKAGE,
            "student_rendered_html",
            "student preview contains student PII",
        ))
    return ArtifactQualityReport(
        artifact_id=snapshot.artifact_id,
        artifact_type=snapshot.artifact_type,
        passed=len(issues) == 0,
        issues=issues,
    )


def pre_search_safety(query: str) -> ArtifactQualityReport:
    issues = []
    if _PII_PATTERN.search(query):
        issues.append(_issue(
            QualityFailureClass.PII_LEAKAGE,
            "query",
            "search query contains student PII",
        ))
    return ArtifactQualityReport(
        artifact_id="pre-search",
        artifact_type="search_query",
        passed=len(issues) == 0,
        issues=issues,
    )


def classify_healing(failure_class: QualityFailureClass) -> HealingDecision:
    match failure_class:
        case QualityFailureClass.SCHEMA_INVALID:
            return _decision(failure_class, HealingStrategy.SCHEMA_REPAIR, 2)
        case QualityFailureClass.ANSWER_KEY_LEAKAGE:
            return _decision(failure_class, HealingStrategy.ANSWER_KEY_REPAIR, 2)
        case QualityFailureClass.PII_LEAKAGE:
            return _decision(failure_class, HealingStrategy.PII_REMOVAL, 1)
        case QualityFailureClass.EXTERNAL_ASSET | QualityFailureClass.MISSING_DOCTYPE:
            return _decision(failure_class, HealingStrategy.PRESENTATION_REPAIR, 2)
        case QualityFailureClass.MISSING_ACCESSIBILITY:
            return _decision(failure_class, HealingStrategy.ACCESSIBILITY_REPAIR, 1)
        case QualityFailureClass.PLACEHOLDER_CONTENT | QualityFailureClass.UNSUPPORTED_COMPONENT:
            return _decision(failure_class, HealingStrategy.REGENERATE_ARTIFACT, 2)
        case QualityFailureClass.EXPORT_NOT_READY:
            return _decision(failure_class, HealingStrategy.ESCALATE, 0)
        case unreachable:
            assert_never(unreachable)


def _artifact_report(
    artifact_id: str,
    artifact: ArtifactContent,
    issues: list[QualityIssue],
) -> ArtifactQualityReport:
    return ArtifactQualityReport(
        artifact_id=artifact_id,
        artifact_type=artifact.artifact_type,
        passed=len(issues) == 0,
        issues=issues,
    )


def export_readiness(
    run_id: RunId,
    snapshots: Sequence[ArtifactSnapshotRead],
    required_artifact_types: Sequence[str] = ("lesson",),
) -> ExportReadinessReport:
    approved = [snapshot for snapshot in snapshots if snapshot.approved_at is not None]
    issues: list[QualityIssue] = []
    approved_types = {snapshot.artifact_type for snapshot in approved}
    for artifact_type in required_artifact_types:
        if artifact_type not in approved_types:
            issues.append(_issue(
                QualityFailureClass.EXPORT_NOT_READY,
                artifact_type,
                "required artifact has no approved snapshot",
            ))
    for snapshot in approved:
        issues.extend(validate_snapshot_publish_quality(snapshot).issues)
    return ExportReadinessReport(
        run_id=run_id,
        passed=len(issues) == 0,
        approved_snapshot_ids=[snapshot.snapshot_id for snapshot in approved],
        issues=issues,
    )


def _scan_placeholder(artifact: ArtifactContent) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    for location, value in _artifact_strings(artifact):
        if _PLACEHOLDER_PATTERN.search(value):
            issues.append(_issue(
                QualityFailureClass.PLACEHOLDER_CONTENT,
                location,
                "placeholder content found",
            ))
            break
    return issues


def _scan_student_answer_keys(artifact: ArtifactContent) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    for index, section in enumerate(artifact.sections):
        if section.get("teacher_only") is True:
            continue
        if _ANSWER_KEY_PATTERN.search(str(section)):
            issues.append(_issue(
                QualityFailureClass.ANSWER_KEY_LEAKAGE,
                f"sections[{index}]",
                "student-facing section contains answer-key text",
            ))
            break
    return issues


def _scan_artifact_pii(artifact: ArtifactContent) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    for location, value in _artifact_strings(artifact):
        if _PII_PATTERN.search(value):
            issues.append(_issue(QualityFailureClass.PII_LEAKAGE, location, "student PII found"))
            break
    return issues


def _scan_accessibility(artifact: ArtifactContent) -> list[QualityIssue]:
    if artifact.accessibility.get("language"):
        return []
    return [_issue(
        QualityFailureClass.MISSING_ACCESSIBILITY,
        "accessibility.language",
        "artifact accessibility language is required",
    )]


def _artifact_strings(artifact: ArtifactContent) -> list[tuple[str, str]]:
    values = [("title", artifact.title)]
    for index, section in enumerate(artifact.sections):
        values.append((f"sections[{index}]", str(section)))
    return values


def _decision(
    failure_class: QualityFailureClass,
    strategy: HealingStrategy,
    max_attempts: int,
) -> HealingDecision:
    return HealingDecision(
        failure_class=failure_class,
        strategy=strategy,
        max_attempts=max_attempts,
    )


def _issue(
    failure_class: QualityFailureClass,
    location: str,
    message: str,
) -> QualityIssue:
    return QualityIssue(failure_class=failure_class, location=location, message=message)
