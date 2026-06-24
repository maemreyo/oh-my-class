"""LLM-based fact verification for high-risk claims only (f.pro)."""
from __future__ import annotations
import json
from dataclasses import dataclass


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
    llm_client,
) -> list[VerificationResult]:
    """Verify HIGH-risk claims using f.pro. Returns verification results."""
    if not claims:
        return []

    claims_json = json.dumps([{"claim": c.text, "context": c.context} for c in claims])

    response = llm_client.chat(
        model="f.pro",
        messages=[{
            "role": "user",
            "content": VERIFY_PROMPT.format(
                grade_level=grade_level,
                claims_json=claims_json,
            ),
        }],
        temperature=0.0,
    )

    raw = json.loads(response.content)
    return [VerificationResult(claim=r["claim"], status=r["status"], note=r.get("note", "")) for r in raw]
