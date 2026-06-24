---
title: "FACT Detection: I2 Hybrid — Heuristics-first, f.pro for High-risk Claims"
status: ready
labels: [quality, agents, gates]
created: 2026-06-24
priority: p1
report: "02"
---

## What to build

Hybrid FACT hallucination detection: deterministic heuristics for fast first pass, f.pro LLM only for high-risk claims. Used inside `step_10_content_review` (Layer 2).

**Design decision (grilling Q3-I2):** 80% of artifacts pass heuristics without LLM call. Only high-risk claims (dates, numbers, named entities, formulas) trigger f.pro verification. Pure functions = easily testable without LLM mocks.

## File Structure

```
packages/agents/gates/fact_check/
├── __init__.py
├── extractor.py          # pure fn: regex-based claim extraction
├── risk_classifier.py    # pure fn: HIGH/MEDIUM/LOW per claim
├── llm_verifier.py       # f.pro LLM verify (only called for HIGH-risk)
└── fact_checker.py       # orchestrate: extract → classify → maybe verify
```

## Implementation Spec

### `fact_check/extractor.py` — pure functions, no LLM

```python
"""Extract factual claims from educational content using regex patterns."""
from __future__ import annotations
import re
from dataclasses import dataclass


@dataclass
class Claim:
    text: str
    claim_type: str   # "number" | "date" | "named_entity" | "formula" | "statistic"
    context: str      # surrounding sentence


# Patterns ordered by specificity
_PATTERNS = [
    ("date",         r"\b\d{4}\b|\b(?:January|February|March|April|May|June|July|"
                     r"August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b"),
    ("statistic",    r"\b\d+(?:\.\d+)?%|\b\d+\s+(?:out of|in)\s+\d+\b"),
    ("formula",      r"[A-Z][a-z]?\d*(?:\+[A-Z][a-z]?\d*)+|"   # chemical: H2O
                     r"[a-z]\s*=\s*[a-z0-9+\-*/^()]+"),          # algebraic: a = b+c
    ("named_entity", r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b"),    # Proper Nouns
    ("number",       r"\b\d{2,}\b"),                              # 2+ digit numbers
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
```

### `fact_check/risk_classifier.py` — pure functions, no LLM

```python
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
        # Named entity near high-risk keyword → HIGH
        context_lower = claim.context.lower()
        if any(kw in context_lower for kw in HIGH_RISK_KEYWORDS):
            return "HIGH"
        return "MEDIUM"

    return "LOW"


def has_high_risk_claims(claims: list[Claim]) -> bool:
    """Quick check: any HIGH-risk claims present?"""
    return any(classify_risk(c) == "HIGH" for c in claims)
```

### `fact_check/llm_verifier.py` — f.pro LLM, only for HIGH-risk

```python
"""LLM-based fact verification for high-risk claims only (f.pro)."""
from __future__ import annotations
import json
from dataclasses import dataclass

from packages.agents.config import MODELS


VERIFY_PROMPT = """You are a fact-checker for educational content.

Verify the following HIGH-RISK factual claims extracted from a lesson for {grade_level} students.
For each claim, determine: VERIFIED / UNCERTAIN / INCORRECT.

Claims to verify:
{claims_json}

Return JSON array:
[{{"claim": "...", "status": "VERIFIED|UNCERTAIN|INCORRECT", "note": "..."}}]
"""


@dataclass
class VerificationResult:
    claim: str
    status: str    # "VERIFIED" | "UNCERTAIN" | "INCORRECT"
    note: str


def verify_high_risk_claims(
    claims: list,
    grade_level: str,
    llm_client,        # injected — testable with mock
) -> list[VerificationResult]:
    """Verify HIGH-risk claims using f.pro. Returns verification results."""
    if not claims:
        return []

    claims_json = json.dumps([{"claim": c.text, "context": c.context} for c in claims])

    response = llm_client.chat(
        model=MODELS.fact_verification,  # f.pro
        messages=[{
            "role": "user",
            "content": VERIFY_PROMPT.format(
                grade_level=grade_level,
                claims_json=claims_json,
            ),
        }],
        temperature=0.0,
    )

    results = json.loads(response.content)
    return [VerificationResult(**r) for r in results]
```

### `fact_check/fact_checker.py` — orchestrate

```python
"""FACT hybrid pipeline: heuristics → optionally LLM for high-risk."""
from __future__ import annotations
from dataclasses import dataclass

from packages.agents.gates.fact_check.extractor import extract_claims
from packages.agents.gates.fact_check.risk_classifier import classify_risk, has_high_risk_claims
from packages.agents.gates.fact_check.llm_verifier import verify_high_risk_claims


@dataclass
class FactCheckResult:
    passed: bool
    total_claims: int
    high_risk_count: int
    llm_called: bool             # True if LLM verification was triggered
    issues: list[str]            # empty = pass
    uncertain_claims: list[str]  # claims LLM could not verify


def fact_check(
    content: str,
    grade_level: str,
    llm_client=None,             # None = skip LLM (for tests)
    skip_llm: bool = False,
) -> FactCheckResult:
    """Run FACT hybrid pipeline on content.

    Fast path (no LLM): if no high-risk claims found.
    LLM path: only for high-risk claims.
    """
    claims = extract_claims(content)
    high_risk = [c for c in claims if classify_risk(c) == "HIGH"]

    if not high_risk or skip_llm or llm_client is None:
        return FactCheckResult(
            passed=True,
            total_claims=len(claims),
            high_risk_count=len(high_risk),
            llm_called=False,
            issues=[],
            uncertain_claims=[],
        )

    # LLM verification for high-risk only
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
```

## Tests

```python
# No LLM needed for extractor and classifier tests

def test_extract_date_claim():
    claims = extract_claims("The French Revolution began in 1789.")
    assert any(c.claim_type == "date" and "1789" in c.text for c in claims)

def test_extract_formula():
    claims = extract_claims("Water molecule is H2O.")
    assert any(c.claim_type == "formula" for c in claims)

def test_classify_date_as_high_risk():
    from packages.agents.gates.fact_check.extractor import Claim
    claim = Claim(text="1789", claim_type="date", context="Revolution in 1789")
    assert classify_risk(claim) == "HIGH"

def test_no_high_risk_skips_llm():
    result = fact_check("Plants use sunlight to make food.", "Grade 3")
    assert result.llm_called is False
    assert result.passed is True

def test_high_risk_triggers_llm():
    mock_llm = MagicMock()
    mock_llm.chat.return_value.content = '[{"claim":"1789","status":"VERIFIED","note":"Correct"}]'
    result = fact_check("The French Revolution began in 1789.", "Grade 8", llm_client=mock_llm)
    assert result.llm_called is True
    mock_llm.chat.assert_called_once()
```

## Acceptance Criteria

- [ ] `extractor.py` extracts dates, statistics, formulas, named entities, numbers — pure function
- [ ] `risk_classifier.py` classifies HIGH/MEDIUM/LOW — pure function
- [ ] `fact_checker.py` skips LLM when no high-risk claims (fast path)
- [ ] `llm_verifier.py` only called for HIGH-risk claims, uses `MODELS.fact_verification` (f.pro)
- [ ] `fact_check()` returns `FactCheckResult` with `llm_called` flag (for cost tracking)
- [ ] Extractor + classifier tests require ZERO LLM mocking
- [ ] LLM path tested with mock client only

## Dependencies

- Blocked by: `gate-config` (MODELS), `quality-gate-nodes` (used inside content_reviewer.py)
- Priority: p1
