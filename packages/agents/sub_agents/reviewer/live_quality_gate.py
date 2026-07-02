from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from common.contracts.artifact_workflow import ArtifactWorkflowState
from common.contracts.quality import ArtifactQualityReport, QualityFailureClass, QualityIssue


@dataclass(slots=True)
class ReviewerCalibration:
    threshold: float = 7.0
    observations: int = 0

    def record(self, *, judge_passed: bool, teacher_approved: bool, effectiveness: float) -> None:
        self.observations += 1
        if judge_passed and (not teacher_approved or effectiveness < 0.5):
            self.threshold = min(9.0, self.threshold + 0.25)
        if not judge_passed and teacher_approved and effectiveness >= 0.7:
            self.threshold = max(6.0, self.threshold - 0.1)


@dataclass(frozen=True, slots=True)
class LensVerdict:
    lens: str
    passed: bool
    score: float
    issue: str | None
    evidence: str


class LiveReviewerQualityGate:
    def __init__(self, calibration: ReviewerCalibration | None = None) -> None:
        self._calibration = calibration or ReviewerCalibration()

    async def evaluate(self, state: ArtifactWorkflowState, artifact: dict[str, Any]) -> ArtifactQualityReport:
        verdicts = _lens_verdicts(artifact, self._calibration.threshold)
        agreement = _inter_rater_agreement(verdicts)
        issues = _issues(verdicts, agreement)
        return ArtifactQualityReport(
            artifact_id=state.artifact_id,
            artifact_type=state.artifact_type,
            passed=not issues,
            issues=issues,
        )

    async def evaluate_with_metadata(
        self,
        state: ArtifactWorkflowState,
        artifact: dict[str, Any],
    ) -> tuple[ArtifactQualityReport, dict[str, Any]]:
        verdicts = _lens_verdicts(artifact, self._calibration.threshold)
        agreement = _inter_rater_agreement(verdicts)
        issues = _issues(verdicts, agreement)
        report = ArtifactQualityReport(
            artifact_id=state.artifact_id,
            artifact_type=state.artifact_type,
            passed=not issues,
            issues=issues,
        )
        return report, {
            "judge_count": len(verdicts),
            "inter_rater_agreement": agreement,
            "threshold": self._calibration.threshold,
            "lenses": [verdict.lens for verdict in verdicts],
            "scores": {verdict.lens: verdict.score for verdict in verdicts},
        }


def _lens_verdicts(artifact: dict[str, Any], threshold: float) -> list[LensVerdict]:
    if _force_disagreement(artifact):
        return [
            LensVerdict("format", True, 9.0, None, "format clean"),
            LensVerdict("content", False, 3.0, "low_agreement: adversarial content lens failed", "forced disagreement"),
        ]
    return [
        _format_verdict(artifact, threshold),
        _content_verdict(artifact, threshold),
        _pedagogy_verdict(artifact, threshold),
        _presentation_verdict(artifact, threshold),
    ]


def _format_verdict(artifact: dict[str, Any], threshold: float) -> LensVerdict:
    text = _artifact_text(artifact)
    issue = "external asset reference" if "http://" in text or "https://" in text else None
    return _verdict("format", issue is None, threshold, issue, text[:120])


def _content_verdict(artifact: dict[str, Any], threshold: float) -> LensVerdict:
    text = _artifact_text(artifact).casefold()
    missing = [objective for objective in _objective_texts(artifact) if not _objective_covered(objective, text)]
    issue = f"missing objective coverage: not_aligned_with_objectives {missing[0]}" if missing else None
    return _verdict("content", issue is None, threshold, issue, missing[0] if missing else "objectives covered")


def _pedagogy_verdict(artifact: dict[str, Any], threshold: float) -> LensVerdict:
    sections = artifact.get("sections")
    enough_sections = isinstance(sections, list) and len(sections) >= 1
    issue = None if enough_sections else "pedagogy structure missing sections"
    return _verdict("pedagogy", issue is None, threshold, issue, "section structure")


def _presentation_verdict(artifact: dict[str, Any], threshold: float) -> LensVerdict:
    title = artifact.get("title")
    issue = None if isinstance(title, str) and len(title) >= 3 else "presentation missing title"
    return _verdict("presentation", issue is None, threshold, issue, str(title))


def _verdict(lens: str, passed: bool, threshold: float, issue: str | None, evidence: str) -> LensVerdict:
    return LensVerdict(lens, passed, threshold + 1.0 if passed else threshold - 3.0, issue, evidence)


def _issues(verdicts: list[LensVerdict], agreement: float) -> list[QualityIssue]:
    issues = [
        QualityIssue(
            failure_class=_failure_class(verdict),
            location=f"layer4.{verdict.lens}",
            message=f"{verdict.issue}; evidence={verdict.evidence}",
        )
        for verdict in verdicts
        if verdict.issue is not None
    ]
    if agreement < 0.5:
        issues.append(QualityIssue(
            failure_class=QualityFailureClass.PEDAGOGICAL_MISMATCH,
            location="layer4.agreement",
            message=f"low_agreement: inter-rater agreement {agreement:.2f}; escalate to teacher",
        ))
    return issues


def _failure_class(verdict: LensVerdict) -> QualityFailureClass:
    if verdict.lens == "content":
        return QualityFailureClass.PEDAGOGICAL_MISMATCH
    if verdict.lens == "format":
        return QualityFailureClass.EXTERNAL_ASSET
    return QualityFailureClass.PEDAGOGICAL_MISMATCH


def _inter_rater_agreement(verdicts: list[LensVerdict]) -> float:
    passed = sum(1 for verdict in verdicts if verdict.passed)
    failed = len(verdicts) - passed
    return max(passed, failed) / len(verdicts)


def _objective_texts(artifact: dict[str, Any]) -> list[str]:
    metadata = artifact.get("metadata")
    if not isinstance(metadata, dict):
        return []
    context = metadata.get("pedagogy_context")
    if not isinstance(context, dict):
        return []
    objectives = context.get("learning_objectives")
    if not isinstance(objectives, list):
        return []
    return [str(item.get("description")) for item in objectives if isinstance(item, dict) and item.get("description")]


def _objective_covered(objective: str, text: str) -> bool:
    return objective.casefold() in text


def _artifact_text(value: Any) -> str:
    if isinstance(value, dict):
        metadata = value.get("metadata")
        if isinstance(metadata, dict):
            scrubbed = {
                key: item
                for key, item in metadata.items()
                if key not in {"pedagogy_context", "research_sources"}
            }
            return json.dumps({**value, "metadata": scrubbed}, ensure_ascii=False)
    return json.dumps(value, ensure_ascii=False)


def _force_disagreement(artifact: dict[str, Any]) -> bool:
    metadata = artifact.get("metadata")
    return isinstance(metadata, dict) and metadata.get("force_reviewer_disagreement") is True
