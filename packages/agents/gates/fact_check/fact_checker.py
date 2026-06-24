"""FACT hybrid pipeline: heuristics → optionally LLM for high-risk."""
from __future__ import annotations
from dataclasses import dataclass, field

from packages.agents.gates.fact_check.extractor import extract_claims
from packages.agents.gates.fact_check.risk_classifier import classify_risk, filter_high_risk
from packages.agents.gates.fact_check.llm_verifier import verify_high_risk_claims


@dataclass
class FactCheckResult:
    passed: bool
    total_claims: int
    high_risk_count: int
    llm_called: bool
    issues: list[str] = field(default_factory=list)
    uncertain_claims: list[str] = field(default_factory=list)


def fact_check(
    content: str,
    grade_level: str = "Grade 5",
    llm_client=None,
    skip_llm: bool = False,
) -> FactCheckResult:
    """Run FACT hybrid pipeline on content.

    Fast path (no LLM): if no high-risk claims found.
    LLM path: only for high-risk claims.
    """
    claims = extract_claims(content)
    high_risk = filter_high_risk(claims)

    if not high_risk or skip_llm or llm_client is None:
        return FactCheckResult(
            passed=True,
            total_claims=len(claims),
            high_risk_count=len(high_risk),
            llm_called=False,
        )

    results = verify_high_risk_claims(high_risk, grade_level, llm_client)
    issues = [f"{r.claim}: {r.note}" for r in results if r.status == "INCORRECT"]
    uncertain = [r.claim for r in results if r.status == "UNCERTAIN"]

    return FactCheckResult(
        passed=len(issues) == 0,
        total_claims=len(claims),
        high_risk_count=len(high_risk),
        llm_called=True,
        issues=issues,
        uncertain_claims=uncertain,
    )


def run_fact_check(text: str) -> dict:
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
    }
