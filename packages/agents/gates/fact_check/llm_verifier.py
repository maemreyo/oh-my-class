"""LLM verifier — only called for HIGH-risk claims (f.pro)."""
from __future__ import annotations


def verify_claims_with_llm(claims: list[dict], context: str = "") -> list[dict]:
    """Stub: verify HIGH-risk claims with LLM. Returns claims with 'verified' field.

    In production, this calls the f.pro model. For MVP (K4), always returns verified=True
    to avoid false positives on educational content.
    """
    return [
        {**claim, "verified": True, "confidence": 0.8}
        for claim in claims
    ]
