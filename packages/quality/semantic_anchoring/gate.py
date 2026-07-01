from __future__ import annotations

from typing import Literal, assert_never

from pydantic import BaseModel, ConfigDict, Field

from common.contracts.quality import QualityFailureClass
from common.contracts.vocabulary_batch import PracticeSet, SemanticAnchorCluster
from common.contracts.vocabulary_cluster_workflow import JsonValue, VocabularyClusterEvidenceEntry

SemanticAnchoringVerdict = Literal["passed", "needs_review", "failed"]
SemanticAnchoringLayer = Literal["schema", "lexical", "pedagogy", "projection", "html"]
SemanticAnchoringAction = Literal[
    "none",
    "teacher_review",
    "withhold_student_export",
    "regenerate_cluster",
]

_TEACHER_ONLY_KEYS = frozenset({
    "teacher_script_vi",
    "source_notes",
    "teacher_source_notes",
    "answer",
    "rationale",
})
_EXTERNAL_ASSET_PATTERNS = ("http://", "https://", "//cdn.", "@import url(")
_PLACEHOLDER_PATTERNS = ("[tbd]", "lorem ipsum", "todo", "placeholder")


class SemanticAnchoringQualityInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    cluster: SemanticAnchorCluster
    practice: PracticeSet
    student_projection: JsonValue = None
    rendered_html: str | None = None


class SemanticAnchoringQualityIssue(BaseModel):
    model_config = ConfigDict(frozen=True)

    failure_class: QualityFailureClass
    layer: SemanticAnchoringLayer
    severity: Literal["info", "warning", "critical"]
    location: str = Field(min_length=1, max_length=300)
    evidence: str = Field(min_length=1, max_length=1000)
    recommended_action: SemanticAnchoringAction
    hard_block: bool


class SemanticAnchoringQualityResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    cluster_id: str = Field(min_length=1, max_length=120)
    verdict: SemanticAnchoringVerdict
    issues: tuple[SemanticAnchoringQualityIssue, ...] = Field(default=())
    withhold_student_export: bool
    evidence_entry: VocabularyClusterEvidenceEntry


class SemanticAnchoringQualityGate:
    def evaluate(self, quality_input: SemanticAnchoringQualityInput) -> SemanticAnchoringQualityResult:
        issues = _cluster_issues(quality_input)
        verdict = _verdict(issues)
        return SemanticAnchoringQualityResult(
            cluster_id=quality_input.cluster.cluster_id,
            verdict=verdict,
            issues=issues,
            withhold_student_export=verdict == "failed",
            evidence_entry=_evidence_entry(quality_input.cluster, verdict, issues),
        )


def _cluster_issues(quality_input: SemanticAnchoringQualityInput) -> tuple[SemanticAnchoringQualityIssue, ...]:
    issues: list[SemanticAnchoringQualityIssue] = []
    issues.extend(_placeholder_issues(quality_input.cluster))
    issues.extend(_lexical_uncertainty_issues(quality_input.cluster))
    issues.extend(_projection_issues(quality_input.student_projection))
    issues.extend(_html_issues(quality_input.rendered_html))
    return tuple(issues)


def _placeholder_issues(cluster: SemanticAnchorCluster) -> tuple[SemanticAnchoringQualityIssue, ...]:
    text = cluster.model_dump_json().casefold()
    if any(pattern in text for pattern in _PLACEHOLDER_PATTERNS):
        return (_issue(
            QualityFailureClass.PLACEHOLDER_CONTENT,
            "schema",
            "critical",
            "cluster",
            "placeholder content appears in semantic anchor cluster",
            "regenerate_cluster",
            True,
        ),)
    return ()


def _lexical_uncertainty_issues(cluster: SemanticAnchorCluster) -> tuple[SemanticAnchoringQualityIssue, ...]:
    if cluster.review_status == "needs_review" or cluster.warnings:
        return (_issue(
            QualityFailureClass.FACTUAL_UNCERTAINTY,
            "lexical",
            "warning",
            "cluster.review_status",
            "lexical nuance or source uncertainty needs teacher review",
            "teacher_review",
            False,
        ),)
    return ()


def _projection_issues(student_projection: JsonValue) -> tuple[SemanticAnchoringQualityIssue, ...]:
    leaked_key = _first_teacher_only_key(student_projection)
    if leaked_key is None:
        return ()
    return (_issue(
        QualityFailureClass.ANSWER_KEY_LEAKAGE,
        "projection",
        "critical",
        leaked_key,
        f"teacher-only field leaked into student projection: {leaked_key}",
        "withhold_student_export",
        True,
    ),)


def _html_issues(rendered_html: str | None) -> tuple[SemanticAnchoringQualityIssue, ...]:
    if rendered_html is None:
        return ()
    lowered = rendered_html.casefold()
    if any(pattern in lowered for pattern in _EXTERNAL_ASSET_PATTERNS):
        return (_issue(
            QualityFailureClass.EXTERNAL_ASSET,
            "html",
            "critical",
            "rendered_html",
            "external asset reference found in rendered semantic anchor HTML",
            "withhold_student_export",
            True,
        ),)
    return ()


def _issue(
    failure_class: QualityFailureClass,
    layer: SemanticAnchoringLayer,
    severity: Literal["info", "warning", "critical"],
    location: str,
    evidence: str,
    recommended_action: SemanticAnchoringAction,
    hard_block: bool,
) -> SemanticAnchoringQualityIssue:
    return SemanticAnchoringQualityIssue(
        failure_class=failure_class,
        layer=layer,
        severity=severity,
        location=location,
        evidence=evidence,
        recommended_action=recommended_action,
        hard_block=hard_block,
    )


def _verdict(issues: tuple[SemanticAnchoringQualityIssue, ...]) -> SemanticAnchoringVerdict:
    if any(issue.hard_block for issue in issues):
        return "failed"
    if issues:
        return "needs_review"
    return "passed"


def _evidence_entry(
    cluster: SemanticAnchorCluster,
    verdict: SemanticAnchoringVerdict,
    issues: tuple[SemanticAnchoringQualityIssue, ...],
) -> VocabularyClusterEvidenceEntry:
    return VocabularyClusterEvidenceEntry(
        evidence_id=f"quality-{cluster.cluster_id}",
        workflow_id=f"vocab-quality-{cluster.cluster_id}",
        cluster_id=cluster.cluster_id,
        run_id="quality-gate",
        sequence=1,
        event_type="quality_result",
        payload={
            "verdict": verdict,
            "issue_count": len(issues),
            "issues": [issue.model_dump(mode="json") for issue in issues],
        },
    )


def _first_teacher_only_key(value: JsonValue) -> str | None:
    match value:
        case dict():
            for key, nested in value.items():
                if key in _TEACHER_ONLY_KEYS:
                    return key
                found = _first_teacher_only_key(nested)
                if found is not None:
                    return found
            return None
        case list():
            for item in value:
                found = _first_teacher_only_key(item)
                if found is not None:
                    return found
            return None
        case str() | int() | float() | bool() | None:
            return None
        case unreachable:
            assert_never(unreachable)
