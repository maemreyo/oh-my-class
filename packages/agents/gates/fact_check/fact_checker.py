"""Fact-check orchestrator: extract → classify → verify high-risk only."""
from __future__ import annotations

from packages.agents.gates.fact_check.extractor import extract_claims
from packages.agents.gates.fact_check.risk_classifier import filter_high_risk
from packages.agents.gates.fact_check.llm_verifier import verify_claims_with_llm


def run_fact_check(text: str) -> dict:
    """Run full fact-check pipeline on text.

    Returns:
        {
            "passed": bool,
            "total_claims": int,
            "high_risk_claims": int,
            "failed_claims": list[dict],
            "errors": list[str],
        }
    """
    all_claims = extract_claims(text)
    high_risk = filter_high_risk(all_claims)

    if not high_risk:
        return {
            "passed": True,
            "total_claims": len(all_claims),
            "high_risk_claims": 0,
            "failed_claims": [],
            "errors": [],
        }

    verified = verify_claims_with_llm(high_risk, context=text)
    failed = [c for c in verified if not c.get("verified", True)]

    return {
        "passed": len(failed) == 0,
        "total_claims": len(all_claims),
        "high_risk_claims": len(high_risk),
        "failed_claims": failed,
        "errors": [c["text"] for c in failed],
    }
