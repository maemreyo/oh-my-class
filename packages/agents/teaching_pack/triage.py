"""Triage: decide single-lesson vs multi-session unit."""
from __future__ import annotations
import re
from typing import Any, Literal

from common.contracts.run_contract import DecompositionIntent

TriageSource = Literal["heuristic", "auto"]

DURATION_THRESHOLD_MINUTES = 90
# Regex to detect multi-session patterns in Vietnamese
_MULTI_SESSION_PATTERNS = [
    re.compile(r"\b(\d+)\s*tuần\b", re.IGNORECASE),
    re.compile(r"\b(\d+)\s*buổi\b", re.IGNORECASE),
    re.compile(r"\b(\d+)\s*tiết\b", re.IGNORECASE),
    re.compile(r"\bqua\s+(\d+)\s*(tuần|buổi|tiết)\b", re.IGNORECASE),
    re.compile(r"\btrong\s+(\d+)\s*(tuần|buổi|tiết)\b", re.IGNORECASE),
]


def triage_heuristic(raw_request: str, duration_minutes: int | None) -> tuple[str, int, str] | None:
    """
    Return (suggested_mode, target_sessions, rationale) if heuristics are conclusive,
    else return None (ambiguous → need LLM).

    Heuristics:
    - duration > 90 min → plan_unit
    - regex for "N tuần/buổi/tiết" with N > 1 → plan_unit
    - short request + duration <= 45 min → generate_pack
    """
    if duration_minutes is not None and duration_minutes > DURATION_THRESHOLD_MINUTES:
        sessions = max(2, round(duration_minutes / 45))
        return "plan_unit", sessions, f"Duration {duration_minutes}min exceeds 90min threshold"

    for pattern in _MULTI_SESSION_PATTERNS:
        match = pattern.search(raw_request)
        if match:
            try:
                n = int(match.group(1))
            except (IndexError, ValueError):
                n = 2
            if n > 1:
                unit = match.group(2) if match.lastindex and match.lastindex >= 2 else "sessions"
                return "plan_unit", n, f"Request explicitly mentions {n} {unit}"

    # Short request, no multi-session cues → single lesson
    word_count = len(raw_request.split())
    if duration_minutes is not None and duration_minutes <= 45 and word_count < 30:
        return "generate_pack", 1, "Short single-concept request"

    return None  # ambiguous


async def triage_with_llm(raw_request: str) -> tuple[str, int, str]:
    """
    Call real LLM via the governed LLMClient when heuristics are ambiguous.
    Returns (suggested_mode, target_sessions, rationale).
    """
    import json

    from packages.llm_client.client import ChatMessage, LLMClient

    prompt = f"""Analyze this teaching request and decide: is this a SINGLE LESSON or a MULTI-SESSION UNIT?

Request: {raw_request}

Respond with JSON only:
{{"suggested_mode": "generate_pack"|"plan_unit", "target_sessions": <integer 1-20>, "rationale": "<brief reason>"}}

Rules:
- "generate_pack": single lesson, 1 session, clearly bounded topic
- "plan_unit": multi-session, needs decomposition into multiple lessons
- target_sessions: 1 for single, 2-8 for multi (based on content scope)"""

    client = LLMClient()
    response = await client.chat(
        model="4omc",
        messages=[ChatMessage(role="user", content=prompt)],
        agent="triage",
        task="triage",
        max_tokens=200,
        temperature=0.0,
    )

    content = response.content
    # Strip markdown code fences if present
    content = re.sub(r"```(?:json)?\n?(.*?)```", r"\1", content, flags=re.DOTALL).strip()

    data = json.loads(content)
    mode = data.get("suggested_mode", "generate_pack")
    sessions = int(data.get("target_sessions", 1))
    rationale = data.get("rationale", "LLM analysis")
    return mode, max(1, min(20, sessions)), rationale


async def run_triage(state: dict[str, Any]) -> dict[str, Any]:
    """
    Run triage on the current state. Returns a partial state update.
    If feature flag is off, returns {} (no-op).
    """
    from packages.agents.teaching_pack.features import topic_decomposition_v1_enabled

    if not topic_decomposition_v1_enabled():
        return {}

    contract = state.get("contract") or {}
    raw_request = contract.get("raw_request") or state.get("run_id", "")
    duration_minutes: int | None = contract.get("duration_minutes")
    if isinstance(duration_minutes, str):
        try:
            duration_minutes = int(duration_minutes)
        except ValueError:
            duration_minutes = None

    # Try heuristics first
    heuristic_result = triage_heuristic(raw_request, duration_minutes)

    if heuristic_result is not None:
        suggested_mode, target_sessions, rationale = heuristic_result
        triage_source: TriageSource = "heuristic"
    else:
        suggested_mode, target_sessions, rationale = await triage_with_llm(raw_request)
        triage_source = "auto"

    session_length = min(90, max(35, (duration_minutes or 45) // max(1, target_sessions)))

    # DecompositionIntent.source is Literal["teacher", "system", "admin"]; use "system"
    # for both heuristic and LLM paths. The distinction is preserved in gate_payload.
    intent = DecompositionIntent(
        target_sessions=max(1, min(20, target_sessions)),
        session_length_minutes=session_length,
        source="system",
        rationale=rationale,
    )

    # Store in gate_payload for the contract_confirmation gate to surface
    existing_gate_payload = state.get("gate_payload") or {}
    gate_payload = {
        **existing_gate_payload,
        "decomposition_suggestion": {
            "suggested_mode": suggested_mode,
            "target_sessions": intent.target_sessions,
            "session_length_minutes": intent.session_length_minutes,
            "source": triage_source,
            "rationale": rationale,
        },
    }

    # Update contract with decomposition_intent
    updated_contract = {
        **contract,
        "decomposition_intent": intent.model_dump(),
        "mode": suggested_mode,
    }

    return {"contract": updated_contract, "gate_payload": gate_payload}
