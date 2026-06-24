"""Heuristic claim extractor for fact-checking pipeline."""
from __future__ import annotations
import re

CLAIM_PATTERNS = [
    r"\b\d+(?:\.\d+)?%",           # percentages
    r"\bin \d{4}\b",               # year references
    r"\b(?:first|invented|discovered|created)\b",  # historical claims
]

def extract_claims(text: str) -> list[dict]:
    """Extract factual claims from artifact text.
    Returns list of {text, start, end, pattern_type} dicts.
    """
    claims = []
    for pattern in CLAIM_PATTERNS:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            claims.append({
                "text": m.group(),
                "start": m.start(),
                "end": m.end(),
                "pattern_type": pattern,
            })
    return claims
