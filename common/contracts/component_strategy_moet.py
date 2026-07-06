from __future__ import annotations

from dataclasses import dataclass
from typing import Final


_PRIMARY_GRADES: Final[frozenset[str]] = frozenset({"Grade 1", "Grade 2", "Grade 3", "Grade 4", "Grade 5"})
_MOET_CLAIM_COPY: Final[tuple[str, ...]] = ("MOET-compliant", "đúng chương trình VN/MOET")


@dataclass(frozen=True, slots=True)
class MoetLaunchCohort:
    supported_scopes: tuple[str, ...]
    required_taxonomy: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MoetComplianceClaim:
    public_claim: bool
    grade_level: str
    subject: str


@dataclass(frozen=True, slots=True)
class MoetValidationInput:
    grade_level: str
    subject: str
    public_claim: bool
    objective_anchor: str
    assessment_policy: str
    taxonomy_level: str


def default_moet_launch_cohort() -> MoetLaunchCohort:
    return MoetLaunchCohort(
        supported_scopes=("grade_5:Tiếng Việt",),
        required_taxonomy=("nhan_biet", "thong_hieu", "van_dung", "van_dung_cao"),
    )


def public_moet_claim_copy() -> tuple[str, ...]:
    return _MOET_CLAIM_COPY


def moet_claim_guard_issues(claim: MoetComplianceClaim, cohort: MoetLaunchCohort) -> tuple[str, ...]:
    if not claim.public_claim:
        return ()
    if _scope_key(claim.grade_level, claim.subject) not in cohort.supported_scopes:
        return ("moet_scope_not_extracted",)
    return ()


def moet_public_compliance_issues(
    validation_input: MoetValidationInput,
    cohort: MoetLaunchCohort | None = None,
) -> tuple[str, ...]:
    if not validation_input.public_claim:
        return ()
    selected_cohort = cohort if cohort is not None else default_moet_launch_cohort()
    issues = list(moet_claim_guard_issues(_claim_from_validation_input(validation_input), selected_cohort))
    if not validation_input.objective_anchor.startswith("Yêu cầu cần đạt"):
        issues.append("moet_objective_anchor_missing")
    if _is_primary(validation_input.grade_level) and validation_input.assessment_policy.startswith("secondary_"):
        issues.append("primary_assessment_policy_mismatch")
    if validation_input.taxonomy_level not in selected_cohort.required_taxonomy:
        issues.append("moet_taxonomy_not_extracted")
    return tuple(issues)


def _claim_from_validation_input(validation_input: MoetValidationInput) -> MoetComplianceClaim:
    return MoetComplianceClaim(
        public_claim=validation_input.public_claim,
        grade_level=validation_input.grade_level,
        subject=validation_input.subject,
    )


def _scope_key(grade_level: str, subject: str) -> str:
    grade_number = grade_level.removeprefix("Grade ")
    return f"grade_{grade_number}:{subject}"


def _is_primary(grade_level: str) -> bool:
    return grade_level in _PRIMARY_GRADES
