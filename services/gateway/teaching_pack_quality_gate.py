from __future__ import annotations

from common.contracts.artifact_workflow import ArtifactWorkflowState
from common.contracts.quality import ArtifactQualityReport, QualityFailureClass, QualityIssue
from packages.quality.layer2_content.age_check import check_age_appropriateness
from packages.quality.layer2_content.fact_check import FACTChecker, SourceDocument, VerificationTag
from packages.quality.layer2_content.pedagogical import check_pedagogical_metrics
from packages.quality.layer2_content.pii import detect_pii
from packages.quality.layer3_html.html_validator import HTMLValidator

from services.gateway.quality_gates import validate_artifact_quality
from services.gateway.teaching_pack_types import JsonObject, JsonValue


class GatewayTeachingPackQualityGate:
    async def evaluate(self, state: ArtifactWorkflowState, artifact: JsonObject) -> ArtifactQualityReport:
        base_report = validate_artifact_quality(state.artifact_id, artifact)
        issues = [*base_report.issues]
        text = _artifact_text(artifact)

        issues.extend(_pii_issues(artifact))
        issues.extend(_age_issues(text, artifact))
        issues.extend(await _fact_issues(text, artifact))
        issues.extend(_pedagogical_issues(artifact))
        issues.extend(_html_issues(text))

        return ArtifactQualityReport(
            artifact_id=state.artifact_id,
            artifact_type=state.artifact_type,
            passed=len(issues) == 0,
            issues=_dedupe_issues(issues),
        )


def _artifact_text(artifact: JsonObject) -> str:
    return " ".join(_walk_strings(artifact))


def _walk_strings(value: JsonValue) -> tuple[str, ...]:
    match value:
        case str():
            return (value,)
        case dict():
            return tuple(text for item in value.values() for text in _walk_strings(item))
        case list() | tuple():
            return tuple(text for item in value for text in _walk_strings(item))
        case _:
            return ()


def _pii_issues(artifact: JsonObject) -> list[QualityIssue]:
    audit = detect_pii(artifact)
    return [
        _issue(
            QualityFailureClass.PII_LEAKAGE,
            f"artifact.{category}",
            f"student PII detected: {count} {category} value(s)",
        )
        for category, count in audit.redaction_counts.items()
        if count > 0
    ]


def _age_issues(text: str, artifact: JsonObject) -> list[QualityIssue]:
    grade_level = _grade_level(artifact)
    if grade_level is None:
        return []
    result = check_age_appropriateness(text, grade_level)
    return [
        _issue(QualityFailureClass.PEDAGOGICAL_MISMATCH, "age_appropriateness", issue)
        for issue in result["issues"]
    ]


async def _fact_issues(text: str, artifact: JsonObject) -> list[QualityIssue]:
    sources = _research_sources(artifact)
    claims = await FACTChecker(min_sources=2).check_claims(text, sources)
    return [
        _issue(
            QualityFailureClass.FACTUAL_UNCERTAINTY,
            "fact_check",
            f"claim is {claim.tag.value}: {claim.claim}",
        )
        for claim in claims
        if claim.tag is not VerificationTag.VERIFIED
    ]


def _pedagogical_issues(artifact: JsonObject) -> list[QualityIssue]:
    result = check_pedagogical_metrics(artifact)
    return [
        _issue(QualityFailureClass.PEDAGOGICAL_MISMATCH, "pedagogical", issue)
        for issue in result.issues
    ]


def _html_issues(text: str) -> list[QualityIssue]:
    if "<html" not in text.lower() and "<!doctype" not in text.lower():
        return []
    result = HTMLValidator().validate(text)
    return [
        _issue(_html_failure_class(code), "rendered_html", f"HTML hard block: {code}")
        for code in result.hard_block_violations
    ]


def _html_failure_class(code: str) -> QualityFailureClass:
    match code:
        case "missing_doctype":
            return QualityFailureClass.MISSING_DOCTYPE
        case (
            "external_assets"
            | "unmanaged_js_runtime"
            | "native_radio_inputs"
            | "missing_brand_string"
            | "contrast_below_aa"
            | "missing_alt_text"
            | "broken_heading_order"
            | "missing_form_label"
            | "missing_lang"
            | "missing_long_description"
        ):
            return QualityFailureClass.EXTERNAL_ASSET
        case "answer_key_leakage":
            return QualityFailureClass.ANSWER_KEY_LEAKAGE
        case _:
            return QualityFailureClass.EXTERNAL_ASSET


def _grade_level(artifact: JsonObject) -> str | None:
    metadata = artifact.get("metadata")
    accessibility = artifact.get("accessibility")
    candidates: tuple[object, ...] = ()
    if isinstance(metadata, dict):
        candidates = (*candidates, metadata.get("grade_level"), metadata.get("grade"))
    if isinstance(accessibility, dict):
        candidates = (*candidates, accessibility.get("reading_level"))
    for value in candidates:
        if isinstance(value, int):
            return f"Grade {value}"
        if isinstance(value, str) and value.strip():
            return value
    return None


def _research_sources(artifact: JsonObject) -> list[SourceDocument]:
    metadata = artifact.get("metadata")
    if not isinstance(metadata, dict):
        return []
    raw_sources = metadata.get("research_sources") or metadata.get("sources")
    if not isinstance(raw_sources, list):
        return []
    sources: list[SourceDocument] = []
    for source in raw_sources:
        if isinstance(source, dict):
            sources.append({
                key: value
                for key in ("title", "content", "url")
                if isinstance((value := source.get(key)), str)
            })
    return sources


def _dedupe_issues(issues: list[QualityIssue]) -> list[QualityIssue]:
    seen: set[tuple[QualityFailureClass, str, str]] = set()
    deduped: list[QualityIssue] = []
    for issue in issues:
        key = (issue.failure_class, issue.location, issue.message)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(issue)
    return deduped


def _issue(failure_class: QualityFailureClass, location: str, message: str) -> QualityIssue:
    return QualityIssue(failure_class=failure_class, location=location, message=message)
