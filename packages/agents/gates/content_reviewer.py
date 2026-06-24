"""Layer 2-3: FACT hybrid + HTML validation + age-appropriateness."""
from __future__ import annotations

from typing import TYPE_CHECKING

from packages.agents.gates.fact_check import run_fact_check
from packages.agents.gates.presentation import validate_html, check_age_appropriateness, check_answer_key_leakage
from packages.agents.config.gate_config import GateConfig

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


def step_10_content_review(state: "OhMyClassState") -> dict:
    """Layer 2-3: Content review (fact-check, HTML, age-appropriateness, answer key).

    Runs all sub-checks on all artifacts. Fails on first hard error.
    """
    config = GateConfig()
    artifacts = state.get("artifacts") or []
    errors = []
    warnings = []
    grade = state.get("class_info", {}).get("grade")

    for artifact in artifacts:
        content = artifact.get("content", "")
        artifact_type = artifact.get("type", "")

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

    if errors:
        return {
            "content_review_passed": False,
            "fail_layer": "content",
            "fail_type": "content",
            "fail_count": state.get("fail_count", 0),
            "fail_context": {"errors": errors, "warnings": warnings},
        }

    return {"content_review_passed": True}
