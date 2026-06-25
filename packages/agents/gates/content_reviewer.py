"""Layer 2-3: FACT hybrid + HTML validation + age-appropriateness."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from packages.agents.config.gate_config import GateConfig
from packages.agents.gates.fact_check import run_fact_check
from packages.agents.gates.presentation import (
    check_age_appropriateness,
    check_answer_key_leakage,
    validate_html,
)
from packages.quality.layer2_content.methodology import check_methodology_compliance

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


def step_10_content_review(state: OhMyClassState) -> dict[str, Any]:
    """Layer 2-3: Content review (fact-check, HTML, age-appropriateness, answer key).

    Runs all sub-checks on all artifacts. Fails on first hard error.
    """
    config = GateConfig()
    artifacts = state.get("artifacts") or []
    errors = []
    warnings = []
    grade = state.get("class_info", {}).get("grade")

    # Methodology gate — only active when lesson_plan declares methodology tags
    lesson_plan = state.get("lesson_plan") or {}
    methodology_tags = (lesson_plan.get("methodology") or {}).get("tags") or []

    for artifact in artifacts:
        # Extract text content from sections (ArtifactContent contract)
        sections = artifact.get("sections") or []
        content = "\n".join(
            s.get("content", "") for s in sections
            if isinstance(s, dict) and s.get("content", "").strip()
        )
        artifact_type = artifact.get("artifact_type", "")

        # Fact check
        fact_result = run_fact_check(content)
        if not fact_result["passed"]:
            errors.extend(fact_result["errors"])

        # HTML validation (only for html-type artifacts)
        if "html" in artifact_type.lower() or content.strip().startswith("<"):
            html_result = validate_html(
                content,
                block_external_assets=config.block_external_assets,
                block_missing_doctype=config.block_missing_doctype,
            )
            if not html_result["passed"]:
                errors.extend(html_result["errors"])
            warnings.extend(html_result.get("warnings", []))

        # Age-appropriateness
        if config.age_check_enabled:
            age_result = check_age_appropriateness(content, grade=grade)
            if not age_result["passed"]:
                errors.extend(age_result["errors"])

        # Answer key leakage
        if config.block_answer_key_leakage:
            ak_result = check_answer_key_leakage(artifact)
            if not ak_result["passed"]:
                errors.extend(ak_result["errors"])

        # Methodology compliance gate (lesson artifacts with methodology tags only)
        if artifact_type == "lesson" and methodology_tags:
            sections = artifact.get("sections") or []
            meth_result = check_methodology_compliance(sections, methodology_tags)
            if not meth_result.passed:
                errors.extend(v.message for v in meth_result.violations)

    if errors:
        return {
            "content_review_passed": False,
            "fail_layer": "content",
            "fail_type": "content",
            "fail_count": state.get("fail_count", 0),
            "fail_context": {"errors": errors, "warnings": warnings},
        }

    return {"content_review_passed": True}
