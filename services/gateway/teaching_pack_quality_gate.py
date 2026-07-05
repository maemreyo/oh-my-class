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
        # The grounded research corpus lives in metadata.research_sources but is
        # evidence, not artifact content — exclude it from text/PII scanning so it is
        # not mistaken for student content (fact_check still reads it from `artifact`).
        content = _content_view(artifact)
        text = _artifact_text(content)

        issues.extend(_pii_issues(content))
        issues.extend(_age_issues(text, artifact))
        issues.extend(await _fact_issues(text, artifact))
        issues.extend(_pedagogical_issues(content, _pedagogy_context(artifact)))
        issues.extend(_html_issues(text))

        return ArtifactQualityReport(
            artifact_id=state.artifact_id,
            artifact_type=state.artifact_type,
            passed=len(issues) == 0,
            issues=_dedupe_issues(issues),
        )


# Gate-context metadata: evidence/context the gate reads but which is NOT student
# content, so it must be excluded from text/PII/claim scanning.
_GATE_CONTEXT_KEYS = ("research_sources", "pedagogy_context")


def _content_view(artifact: JsonObject) -> JsonObject:
    """Artifact minus gate-context metadata, for text/PII scanning.

    ``research_sources`` (fetched evidence) and ``pedagogy_context`` (lesson-plan
    subset) are inputs the gate cross-references against — not student-facing content —
    so they must not be scanned as claims or PII, nor let content self-match its own
    objectives.
    """
    metadata = artifact.get("metadata")
    if not isinstance(metadata, dict) or not any(key in metadata for key in _GATE_CONTEXT_KEYS):
        return artifact
    scrubbed = {key: value for key, value in metadata.items() if key not in _GATE_CONTEXT_KEYS}
    return {**artifact, "metadata": scrubbed}


def _pedagogy_context(artifact: JsonObject) -> dict[str, JsonValue] | None:
    metadata = artifact.get("metadata")
    if isinstance(metadata, dict):
        context = metadata.get("pedagogy_context")
        if isinstance(context, dict):
            return context
    return None


def _artifact_text(artifact: JsonObject) -> str:
    # Join distinct artifact strings with a sentence boundary so claim extraction
    # treats each field as its own unit instead of mashing titles/ids into the
    # factual sentence (which polluted claim terms and blocked verification).
    return ". ".join(_walk_strings(artifact))


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
    # Without grounded research sources we have no evidence corpus, so the
    # fact checker has nothing to verify against and marks everything UNCERTAIN.
    # Skip rather than block generation — factual coverage is a delivery-time
    # concern, not a blocker when research was unavailable (e.g. offline dev).
    if not sources:
        return []
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


def _pedagogical_issues(
    content: JsonObject,
    lesson_plan: dict[str, JsonValue] | None,
) -> list[QualityIssue]:
    result = check_pedagogical_metrics(content, lesson_plan=lesson_plan)
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
