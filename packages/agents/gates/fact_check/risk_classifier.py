"""Risk classifier for extracted claims."""
from __future__ import annotations

HIGH_RISK_KEYWORDS = {"first", "invented", "discovered", "created", "only", "never", "always"}
MEDIUM_RISK_KEYWORDS = {"usually", "often", "typically", "generally"}

def classify_risk(claim: dict) -> str:
    """Return 'HIGH', 'MEDIUM', or 'LOW' risk for a claim dict."""
    text_lower = claim.get("text", "").lower()
    words = set(text_lower.split())
    if words & HIGH_RISK_KEYWORDS:
        return "HIGH"
    if words & MEDIUM_RISK_KEYWORDS:
        return "MEDIUM"
    return "LOW"

def filter_high_risk(claims: list[dict]) -> list[dict]:
    """Return only HIGH-risk claims."""
    return [c for c in claims if classify_risk(c) == "HIGH"]
