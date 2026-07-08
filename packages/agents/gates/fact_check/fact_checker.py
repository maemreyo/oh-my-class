from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from packages.agents.gates.fact_check.extractor import extract_claims
from packages.agents.gates.fact_check.llm_verifier import verify_high_risk_claims
from packages.agents.gates.fact_check.risk_classifier import filter_high_risk


@dataclass
class FactCheckResult:
    passed: bool
    total_claims: int
    high_risk_count: int
    llm_called: bool
    issues: list[str] = field(default_factory=list)
    uncertain_claims: list[str] = field(default_factory=list)
    grounded_claims: list[str] = field(default_factory=list)


def fact_check(
    content: str,
    grade_level: str = "Grade 5",
    llm_client=None,
    skip_llm: bool = False,
    grounding_corpus: list[dict[str, Any]] | None = None,
) -> FactCheckResult:
    """Run FACT hybrid pipeline on content.

    Fast path (no LLM): if no high-risk claims found.
    LLM path: only for high-risk claims.
    """
    claims = extract_claims(content)
    high_risk = filter_high_risk(claims)
    grounded = _grounded_claim_texts(high_risk, grounding_corpus or [])
    unresolved = [claim for claim in high_risk if claim.text not in grounded]

    if not high_risk:
        return FactCheckResult(
            passed=True,
            total_claims=len(claims),
            high_risk_count=len(high_risk),
            llm_called=False,
            grounded_claims=grounded,
        )

    if not unresolved:
        return FactCheckResult(
            passed=True,
            total_claims=len(claims),
            high_risk_count=len(high_risk),
            llm_called=False,
            grounded_claims=grounded,
        )

    if skip_llm:
        return FactCheckResult(
            passed=False,
            total_claims=len(claims),
            high_risk_count=len(high_risk),
            llm_called=False,
            uncertain_claims=[claim.text for claim in unresolved],
            grounded_claims=grounded,
        )

    if llm_client is None:
        # No LLM configured at all — there's no way to verify, so give benefit
        # of the doubt rather than block on an uncertain claim alone.
        return FactCheckResult(
            passed=True,
            total_claims=len(claims),
            high_risk_count=len(high_risk),
            llm_called=False,
            uncertain_claims=[claim.text for claim in unresolved],
            grounded_claims=grounded,
        )

    results = verify_high_risk_claims(unresolved, grade_level, llm_client)
    issues = [f"{r.claim}: {r.note}" for r in results if r.status == "INCORRECT"]
    uncertain = [r.claim for r in results if r.status == "UNCERTAIN"]

    return FactCheckResult(
        passed=len(issues) == 0,
        total_claims=len(claims),
        high_risk_count=len(high_risk),
        llm_called=True,
        issues=issues,
        uncertain_claims=uncertain,
        grounded_claims=grounded,
    )


def _grounded_claim_texts(claims: list[Any], grounding_corpus: list[dict[str, Any]]) -> list[str]:
    grounded: list[str] = []
    verified_excerpts = [
        str(source.get("excerpt", ""))
        for source in grounding_corpus
        if source.get("verification_status") == "VERIFIED" and source.get("excerpt")
    ]
    for claim in claims:
        if _claim_supported_by_corpus(claim.text, claim.context, verified_excerpts):
            grounded.append(claim.text)
    return grounded


def _claim_supported_by_corpus(claim_text: str, context: str, excerpts: list[str]) -> bool:
    claim = claim_text.lower()
    sentence = context.lower()
    support_count = 0
    for excerpt in excerpts:
        lowered = excerpt.lower()
        if claim in lowered or sentence in lowered:
            support_count += 1
    return support_count >= 2


def run_fact_check(text: str) -> dict[str, Any]:
    """Backward-compat wrapper for content_reviewer.py.

    Returns legacy dict format: {"passed": bool, "errors": list[str], ...}
    """
    result = fact_check(text)
    return {
        "passed": result.passed,
        "total_claims": result.total_claims,
        "high_risk_claims": result.high_risk_count,
        "failed_claims": [],
        "errors": result.issues,
        "grounded_claims": result.grounded_claims,
        "uncertain_claims": result.uncertain_claims,
    }
