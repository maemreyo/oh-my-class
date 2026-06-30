"""Cross-session coherence checks — advisory lint, never a blocking gate.

All warnings carry severity="advisory".  This module never raises an
exception and never causes a unit to become non-exportable.  Callers
invoke run_coherence_lint() on-demand; it is not wired into any gate.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from common.contracts.lesson_sequence import SessionPlan

if TYPE_CHECKING:
    pass


class CoherenceWarningType(StrEnum):
    TERMINOLOGY_DRIFT = "terminology_drift"
    NON_MONOTONIC_DIFFICULTY = "non_monotonic_difficulty"
    REDUNDANT_COVERAGE = "redundant_coverage"
    UNRESOLVED_BACK_REFERENCE = "unresolved_back_reference"


@dataclass(frozen=True, slots=True)
class CoherenceWarning:
    warning_type: CoherenceWarningType
    involved_session_ids: tuple[str, ...]
    message: str
    severity: str = "advisory"  # always "advisory" — never a blocking gate


# ---------------------------------------------------------------------------
# Bloom rank map (string literals matching BloomLevel Literal type)
# ---------------------------------------------------------------------------

_BLOOM_RANK: dict[str, int] = {
    "remember": 0,
    "understand": 1,
    "apply": 2,
    "analyze": 3,
    "evaluate": 4,
    "create": 5,
}


def _bloom_rank(level: str) -> int:
    return _BLOOM_RANK.get(level, 0)


# ---------------------------------------------------------------------------
# Deterministic checks
# ---------------------------------------------------------------------------


def check_unresolved_back_references(sessions: list[SessionPlan]) -> list[CoherenceWarning]:
    """Scan session titles/objectives/sub_topics for references to non-existent session numbers.

    Recognised patterns (case-insensitive):
      - "as learned in session N"
      - "đã học ở buổi N"
      - "covered in session N"
      - "from session N"

    A reference is considered resolved if N matches any session's order_index or
    any numeric suffix in any session_id within the sequence.
    """
    session_numbers: set[int] = set()
    for s in sessions:
        session_numbers.add(s.order_index)
        m = re.search(r"\d+", s.session_id)
        if m:
            session_numbers.add(int(m.group()))

    _patterns = [
        re.compile(r"as\s+learned\s+in\s+session\s+(\d+)", re.IGNORECASE),
        re.compile(r"đã\s+học\s+ở\s+buổi\s+(\d+)", re.IGNORECASE),
        re.compile(r"covered\s+in\s+session\s+(\d+)", re.IGNORECASE),
        re.compile(r"from\s+session\s+(\d+)", re.IGNORECASE),
    ]

    warnings: list[CoherenceWarning] = []
    for sess in sessions:
        texts = [sess.title, sess.sub_topic] + list(sess.learning_objectives)
        for text in texts:
            for pattern in _patterns:
                for match in pattern.finditer(text):
                    ref_num = int(match.group(1))
                    if ref_num not in session_numbers:
                        warnings.append(CoherenceWarning(
                            warning_type=CoherenceWarningType.UNRESOLVED_BACK_REFERENCE,
                            involved_session_ids=(sess.session_id,),
                            message=(
                                f"Session '{sess.session_id}' references session {ref_num} "
                                f"which does not exist in the sequence."
                            ),
                        ))
    return warnings


def check_non_monotonic_difficulty(sessions: list[SessionPlan]) -> list[CoherenceWarning]:
    """Detect significant Bloom-level drops between consecutive sessions.

    A drop of more than 1 rank (i.e. bloom_rank[j] < bloom_rank[i] - 1) is
    flagged.  A single-rank drop (e.g. understand → remember) is treated as
    normal spiral review and is not flagged.
    """
    warnings: list[CoherenceWarning] = []
    for i in range(len(sessions) - 1):
        curr = sessions[i]
        nxt = sessions[i + 1]
        curr_rank = _bloom_rank(curr.bloom_level_primary)
        next_rank = _bloom_rank(nxt.bloom_level_primary)
        if next_rank < curr_rank - 1:
            warnings.append(CoherenceWarning(
                warning_type=CoherenceWarningType.NON_MONOTONIC_DIFFICULTY,
                involved_session_ids=(curr.session_id, nxt.session_id),
                message=(
                    f"Difficulty drops significantly from '{curr.bloom_level_primary}' "
                    f"(session {curr.session_id}) to '{nxt.bloom_level_primary}' "
                    f"(session {nxt.session_id}). "
                    "Consider reordering to maintain progressive difficulty."
                ),
            ))
    return warnings


def check_redundant_coverage(sessions: list[SessionPlan]) -> list[CoherenceWarning]:
    """Flag sessions sharing the same normalised sub_topic string.

    Normalisation: lowercase + strip whitespace.
    """
    seen: dict[str, str] = {}  # normalised_topic → first session_id
    warnings: list[CoherenceWarning] = []
    for sess in sessions:
        normalised = sess.sub_topic.strip().lower()
        if normalised in seen:
            warnings.append(CoherenceWarning(
                warning_type=CoherenceWarningType.REDUNDANT_COVERAGE,
                involved_session_ids=(seen[normalised], sess.session_id),
                message=(
                    f"Sessions '{seen[normalised]}' and '{sess.session_id}' both cover "
                    f"'{sess.sub_topic}'. "
                    "Consider merging or differentiating them."
                ),
            ))
        else:
            seen[normalised] = sess.session_id
    return warnings


# ---------------------------------------------------------------------------
# LLM-based check (graceful degrade when no client is provided)
# ---------------------------------------------------------------------------


async def check_terminology_drift(
    sessions: list[SessionPlan],
    llm_client=None,
) -> list[CoherenceWarning]:
    """Prompt an LLM to surface sessions that use different terms for the same concept.

    If llm_client is None, returns [] immediately (graceful degrade).
    The client must expose an ``acomplete(prompt: str) -> str`` coroutine.

    Expected response format (one finding per line):
        session_X and session_Y use different terms for <concept>: <termX> vs <termY>
    """
    if llm_client is None:
        return []

    session_summaries: list[str] = []
    for sess in sessions:
        kc_titles = [kc.title for kc in sess.knowledge_components]
        session_summaries.append(
            f"Session {sess.session_id} ('{sess.sub_topic}')"
            + (f": KCs = [{', '.join(kc_titles)}]" if kc_titles else "")
        )

    prompt = (
        "Review these session sub-topics and knowledge component titles. "
        "List any cases where different terms refer to the same concept across sessions. "
        "Format each finding as: "
        "'session_X and session_Y use different terms for <concept>: <termX> vs <termY>'. "
        "If no drift is found, respond with 'NONE'.\n\n"
        + "\n".join(session_summaries)
    )

    try:
        response = await llm_client.acomplete(prompt)
        text = response.strip()
        if text.upper() == "NONE":
            return []

        warnings: list[CoherenceWarning] = []
        # Parse lines like:
        # "session_A and session_B use different terms for X: termA vs termB"
        pattern = re.compile(
            r"session[_\s]+(\w+)\s+and\s+session[_\s]+(\w+)"
            r"\s+use\s+different\s+terms\s+for\s+([^:]+):\s+(.+?)\s+vs\s+(.+)",
            re.IGNORECASE,
        )
        for line in text.splitlines():
            m = pattern.search(line)
            if m:
                sid_a, sid_b, concept, term_a, term_b = m.groups()
                warnings.append(CoherenceWarning(
                    warning_type=CoherenceWarningType.TERMINOLOGY_DRIFT,
                    involved_session_ids=(sid_a.strip(), sid_b.strip()),
                    message=(
                        f"Terminology drift for concept '{concept.strip()}': "
                        f"session {sid_a.strip()} uses '{term_a.strip()}', "
                        f"session {sid_b.strip()} uses '{term_b.strip()}'."
                    ),
                ))
        return warnings
    except Exception:
        # Never block the pipeline; degrade silently.
        return []


# ---------------------------------------------------------------------------
# Aggregate entry point
# ---------------------------------------------------------------------------


async def run_coherence_lint(
    sessions: list[SessionPlan],
    llm_client=None,
) -> list[CoherenceWarning]:
    """Run all cross-session coherence checks and return combined advisory warnings.

    Deterministic checks (back-references, non-monotonic difficulty, redundant
    coverage) always run.  Terminology drift runs only when llm_client is
    provided.

    This function never raises — the unit remains complete/exportable regardless
    of the warnings returned.
    """
    warnings: list[CoherenceWarning] = []
    warnings.extend(check_unresolved_back_references(sessions))
    warnings.extend(check_non_monotonic_difficulty(sessions))
    warnings.extend(check_redundant_coverage(sessions))
    warnings.extend(await check_terminology_drift(sessions, llm_client))
    return warnings
