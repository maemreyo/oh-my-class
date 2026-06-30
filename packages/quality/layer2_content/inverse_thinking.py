from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from common.contracts.inverse_thinking import InverseThinkingPack
from packages.methodologies.inverse_thinking import validate_semantics
from packages.quality.layer2_content.pii import detect_pii

IssueSeverity = Literal["critical", "major"]


class InverseThinkingQualityIssue(BaseModel):
    model_config = ConfigDict(frozen=True)

    severity: IssueSeverity
    code: str
    case_id: str
    field_path: str
    repair_instruction: str = Field(min_length=1)


class InverseThinkingGateResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    passed: bool
    issues: list[InverseThinkingQualityIssue] = Field(default_factory=list)


def validate_inverse_thinking_pack(payload: InverseThinkingPack | dict[str, Any]) -> InverseThinkingGateResult:
    try:
        pack = validate_semantics(payload)
    except ValidationError as exc:
        return InverseThinkingGateResult(passed=False, issues=_critical_issues_from_validation(exc, payload))
    issues = _residual_pii_issues(pack) + _warning_issues(pack)
    return InverseThinkingGateResult(passed=not issues, issues=issues)


def _residual_pii_issues(pack: InverseThinkingPack) -> list[InverseThinkingQualityIssue]:
    audit = detect_pii(pack.model_dump())
    if not audit.redaction_counts:
        return []
    return [
        InverseThinkingQualityIssue(
            severity="critical",
            code="residual_pii_detected",
            case_id="unknown_case",
            field_path="methodology.inverse_thinking",
            repair_instruction="Scrub private student identifiers before generation, persistence, rendering, preview, or export.",
        )
    ]


def _critical_issues_from_validation(
    exc: ValidationError,
    payload: InverseThinkingPack | dict[str, Any],
) -> list[InverseThinkingQualityIssue]:
    issues: list[InverseThinkingQualityIssue] = []
    for error in exc.errors():
        loc = tuple(str(part) for part in error["loc"])
        if len(loc) >= 2 and loc[0].startswith("case-"):
            case_id = loc[0]
            field = loc[1]
        else:
            case_id, field = _case_and_field_from_contract_error(loc, payload)
        issues.append(
            InverseThinkingQualityIssue(
                severity="critical",
                code=_critical_code(field, str(error["msg"])),
                case_id=case_id,
                field_path=f"cases.{case_id}.{field}",
                repair_instruction=_repair_instruction(field),
            )
        )
    return issues


def _case_and_field_from_contract_error(
    loc: tuple[str, ...],
    payload: InverseThinkingPack | dict[str, Any],
) -> tuple[str, str]:
    if "cases" in loc:
        field = loc[-1]
        case_id = _case_id_from_loc(loc, payload)
        return case_id, field
    return "unknown_case", loc[-1] if loc else "payload"


def _case_id_from_loc(loc: tuple[str, ...], payload: InverseThinkingPack | dict[str, Any]) -> str:
    try:
        case_index = int(loc[loc.index("cases") + 1])
    except (ValueError, IndexError):
        return "unknown_case"
    cases = payload.cases if isinstance(payload, InverseThinkingPack) else payload.get("cases", [])
    if not isinstance(cases, list) or case_index >= len(cases):
        return "unknown_case"
    case = cases[case_index]
    if isinstance(case, dict):
        value = case.get("id")
        return value if isinstance(value, str) else "unknown_case"
    return case.id


def _critical_code(field: str, message: str) -> str:
    if "student-facing" in message:
        return "answer_key_leakage"
    if field == "disaster" and "Field required" in message:
        return "missing_disaster"
    if field == "disaster":
        return "rule_first_ordering"
    if field == "key_clues":
        return "missing_key_clues"
    if field == "safe_zone":
        return "missing_safe_zone_boundary"
    if field == "filing_note":
        return "missing_filing_note"
    return "inverse_thinking_contract_failure"


def _repair_instruction(field: str) -> str:
    match field:
        case "disaster":
            return "Rewrite the case to open with a concrete student error or failure before naming the rule."
        case "key_clues":
            return "Add at least one specific observable clue that helps students diagnose the disaster."
        case "safe_zone":
            return "Add a clear boundary rule or safe-zone repair students can apply."
        case "filing_note":
            return "Add a synthesis note that connects the disaster, clue, and safe rule."
        case "student_task":
            return "Move answer keys and rationales into teacher_only and keep the task student-facing."
        case _:
            return "Repair the inverse-thinking field named in the failure path."


def _warning_issues(pack: InverseThinkingPack) -> list[InverseThinkingQualityIssue]:
    issues: list[InverseThinkingQualityIssue] = []
    for case in pack.cases:
        disaster = case.disaster.lower()
        if disaster in {"this is wrong.", "wrong.", "bad answer."} or len(disaster.split()) < 5:
            issues.append(_warning(case.id, "disaster", "generic_disaster", "Make the disaster concrete, specific, and tied to the target concept."))
        if case.title.lower() in {"exercise", "case", "practice"}:
            issues.append(_warning(case.id, "title", "missing_signature_element", "Add a memorable case-file title or signature element."))
        if "hiện trường → manh mối → vùng an toàn → biên bản" in case.student_task.lower():
            issues.append(_warning(case.id, "student_task", "over_copied_template", "Adapt the reference flow instead of copying template labels verbatim."))
        if pack.creative_frame == "courtroom_trial" and not _contains_any(case.title + " " + case.student_task, ("evidence", "claim", "verdict", "trial", "court")):
            issues.append(_warning(case.id, "title", "weak_metaphor_consistency", "Align case wording with courtroom evidence, claims, or verdict language."))
    return issues


def _warning(case_id: str, field: str, code: str, instruction: str) -> InverseThinkingQualityIssue:
    return InverseThinkingQualityIssue(
        severity="major",
        code=code,
        case_id=case_id,
        field_path=f"cases.{case_id}.{field}",
        repair_instruction=instruction,
    )


def _contains_any(value: str, needles: tuple[str, ...]) -> bool:
    lowered = value.lower()
    return any(needle in lowered for needle in needles)
