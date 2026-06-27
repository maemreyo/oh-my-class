"""Deterministic hard-block enforcement for Layer 4 judge.

Hard blocks are deterministic gate violations that override any LLM score.
A high LLM score can NEVER override these — they are FAIL-CLOSED by design.

Sourced from packages/quality/layer3_html/html_validator.py HARD_BLOCKS
and common/contracts/quality.py QualityFailureClass values.
"""

from __future__ import annotations

from common.contracts.judge_output import JudgeOutput

# ---------------------------------------------------------------------------
# Hard block codes — deterministic gate violations that override any LLM score.
# These are NEVER overridable by LLM judge output.
# ---------------------------------------------------------------------------

HARD_BLOCK_CODES: frozenset[str] = frozenset({
    "missing_doctype",
    "external_assets",          # HTML validator naming
    "external_asset",           # QualityFailureClass naming
    "answer_key_leakage",
    "pii_leakage",
    "native_radio_inputs",
    "unmanaged_js_runtime",
    "missing_brand_string",
    "schema_invalid",
})


def enforce_hard_blocks(
    judge_output: JudgeOutput,
    deterministic_issues: list[str],
    teacher_approved: bool,
) -> tuple[JudgeOutput, bool, list[str]]:
    """Enforce deterministic hard blocks on the LLM judge output.

    Returns ``(modified_judge_output, was_blocked, block_violations)``.

    If hard blocks are detected:

    - ``passed`` is forced to ``False``
    - All hard block codes are added to ``critical_issues``
    - The ``overall_score`` is preserved for diagnostics (not zeroed)
    """
    violations: list[str] = []

    # Check deterministic issues against hard block codes
    for issue in deterministic_issues:
        normalized = issue.strip().lower().replace(" ", "_")
        if normalized in HARD_BLOCK_CODES:
            violations.append(issue)

    # Check teacher gate state
    if not teacher_approved:
        violations.append("teacher_gate_not_approved")

    if not violations:
        return judge_output, False, []

    # Force fail — override passed and ensure violations are in critical_issues
    existing_critical = list(judge_output.critical_issues)
    new_critical = existing_critical.copy()
    for v in violations:
        if v not in new_critical:
            new_critical.append(v)

    overridden = JudgeOutput(
        overall_score=judge_output.overall_score,
        layer_scores=list(judge_output.layer_scores),
        critical_issues=new_critical,
        passed=False,
        rationale=(
            judge_output.rationale
            + f"\n[Deterministic override: {', '.join(violations)} forced fail]"
        ),
    )

    return overridden, True, violations
