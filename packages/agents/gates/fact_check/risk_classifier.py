"""Classify factual claims by hallucination risk level."""
from __future__ import annotations
from packages.agents.gates.fact_check.extractor import Claim

HIGH_RISK_TYPES = {"date", "statistic", "formula"}
MEDIUM_RISK_TYPES = {"named_entity"}
LOW_RISK_TYPES = {"number"}

HIGH_RISK_KEYWORDS = {
    "invented", "discovered", "founded", "born", "died",
    "percent", "%", "million", "billion", "equation",
}


def classify_risk(claim: Claim) -> str:
    """Return 'HIGH' | 'MEDIUM' | 'LOW'. Pure function."""
    if claim.claim_type in HIGH_RISK_TYPES:
        return "HIGH"

    if claim.claim_type in MEDIUM_RISK_TYPES:
        context_lower = claim.context.lower()
        if any(kw in context_lower for kw in HIGH_RISK_KEYWORDS):
            return "HIGH"
        return "MEDIUM"

    return "LOW"


def filter_high_risk(claims: list[Claim]) -> list[Claim]:
    """Return only HIGH-risk claims."""
    return [c for c in claims if classify_risk(c) == "HIGH"]


def has_high_risk_claims(claims: list[Claim]) -> bool:
    """Quick check: any HIGH-risk claims present?"""
    return any(classify_risk(c) == "HIGH" for c in claims)
