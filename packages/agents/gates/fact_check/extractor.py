"""Extract factual claims from educational content using regex patterns."""
from __future__ import annotations
import re
from dataclasses import dataclass


@dataclass
class Claim:
    text: str
    claim_type: str   # "number" | "date" | "named_entity" | "formula" | "statistic"
    context: str      # surrounding sentence


_PATTERNS = [
    ("date",         r"\b\d{4}\b|\b(?:January|February|March|April|May|June|July|"
                     r"August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b"),
    ("statistic",    r"\b\d+(?:\.\d+)?%|\b\d+\s+(?:out of|in)\s+\d+\b"),
    ("formula",      r"[A-Z][a-z]?\d*(?:\+[A-Z][a-z]?\d*)+|[a-z]\s*=\s*[a-z0-9+\-*/^()]+"),
    ("named_entity", r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b"),
    ("number",       r"\b\d{2,}\b"),
]


def extract_claims(text: str) -> list[Claim]:
    """Extract all factual claims from text. Pure function — no LLM."""
    claims = []
    sentences = re.split(r"(?<=[.!?])\s+", text)

    for sentence in sentences:
        for claim_type, pattern in _PATTERNS:
            for match in re.finditer(pattern, sentence):
                claims.append(Claim(
                    text=match.group(),
                    claim_type=claim_type,
                    context=sentence.strip(),
                ))

    return claims
