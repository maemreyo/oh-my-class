from __future__ import annotations

from common.contracts.component_strategy_moet import (
    MoetComplianceClaim,
    MoetLaunchCohort,
    MoetValidationInput,
    default_moet_launch_cohort,
    moet_claim_guard_issues,
    moet_public_compliance_issues,
)


def test_moet_claim_guard_blocks_public_claim_before_extraction_scope() -> None:
    claim = MoetComplianceClaim(public_claim=True, grade_level="Grade 3", subject="Tiếng Việt")

    issues = moet_claim_guard_issues(claim, default_moet_launch_cohort())

    assert issues == ("moet_scope_not_extracted",)


def test_moet_claim_guard_allows_internal_non_public_improvement() -> None:
    claim = MoetComplianceClaim(public_claim=False, grade_level="Grade 3", subject="Tiếng Việt")

    issues = moet_claim_guard_issues(claim, default_moet_launch_cohort())

    assert issues == ()


def test_moet_public_compliance_checks_objective_assessment_and_taxonomy() -> None:
    cohort = MoetLaunchCohort(
        supported_scopes=("grade_5:Tiếng Việt",),
        required_taxonomy=("nhan_biet", "thong_hieu", "van_dung"),
    )
    validation_input = MoetValidationInput(
        grade_level="Grade 5",
        subject="Tiếng Việt",
        public_claim=True,
        objective_anchor="Yêu cầu cần đạt: đọc hiểu văn bản",
        assessment_policy="primary_periodic_with_comments",
        taxonomy_level="thong_hieu",
    )

    assert moet_public_compliance_issues(validation_input, cohort) == ()


def test_moet_public_compliance_fails_closed_for_secondary_scoring_in_primary() -> None:
    validation_input = MoetValidationInput(
        grade_level="Grade 5",
        subject="Tiếng Việt",
        public_claim=True,
        objective_anchor="Yêu cầu cần đạt: đọc hiểu văn bản",
        assessment_policy="secondary_numeric_matrix",
        taxonomy_level="thong_hieu",
    )

    issues = moet_public_compliance_issues(validation_input, default_moet_launch_cohort())

    assert "primary_assessment_policy_mismatch" in issues
