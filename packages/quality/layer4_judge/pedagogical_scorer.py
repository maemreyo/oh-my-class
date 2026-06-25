"""5-dimension pedagogical quality rubric via f.pro LLM (QG2)."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

PASS_THRESHOLD = 3.5   # avg of 5 dimensions must be >= 3.5 to pass

SCORE_PROMPT = """\
You are an expert educational content evaluator.

Score the following educational content on 5 dimensions (1-5 scale each):

1. Clarity (1-5): Is the content clear and understandable for the target audience?
2. Integrity (1-5): Are all required sections present and complete?
3. Depth (1-5): Does it go beyond surface-level coverage?
4. Practicality (1-5): Can a teacher implement this as-is without modification?
5. Pertinence (1-5): Is it relevant to the stated learning objectives?

Return ONLY valid JSON:
{{"clarity": N, "integrity": N, "depth": N, "practicality": N, "pertinence": N, \
"rationale": "one sentence per dimension"}}

Content to evaluate:
{content}\
"""

# Truncate to 6000 chars to stay within context budget
_MAX_CONTENT_CHARS = 6000


@dataclass
class PedagogicalScore:
    clarity:      float
    integrity:    float
    depth:        float
    practicality: float
    pertinence:   float
    total:        float   # average of 5 dimensions
    passed:       bool    # total >= PASS_THRESHOLD
    rationale:    str


async def score_pedagogical(
    content: str,
    llm: object | None = None,
    run_id: str | None = None,
    step: int | None = None,
) -> PedagogicalScore:
    """Score content on 5 pedagogical dimensions using an f.pro LLM judge.

    Args:
        content: The educational content to evaluate (plain text or markdown)
        llm:     Optional LLMClient instance. If None, creates a new one.
        run_id:  Pipeline run ID for cost attribution (INVARIANT-07)
        step:    Pipeline step index for cost attribution (INVARIANT-07)

    Returns:
        PedagogicalScore with 5 dimension scores (1-5) and a total average.
    """
    from packages.agents.config import MODELS
    from packages.llm_client.client import ChatMessage, LLMClient

    llm = llm or LLMClient()
    truncated = content[:_MAX_CONTENT_CHARS]
    prompt = SCORE_PROMPT.format(content=truncated)

    response = await llm.chat(  # type: ignore[union-attr]
        model=MODELS.llm_judge,
        messages=[ChatMessage(role="user", content=prompt)],
        agent="pedagogical_scorer",
        task="quality_gate",
        run_id=run_id,
        step=step,
        response_format={"type": "json_object"},
    )

    try:
        data: dict[str, Any] = json.loads(response.content)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse pedagogical score JSON", exc_info=exc)
        raise

    dims = [
        float(data["clarity"]),
        float(data["integrity"]),
        float(data["depth"]),
        float(data["practicality"]),
        float(data["pertinence"]),
    ]
    total = sum(dims) / len(dims)

    return PedagogicalScore(
        clarity=dims[0],
        integrity=dims[1],
        depth=dims[2],
        practicality=dims[3],
        pertinence=dims[4],
        total=round(total, 2),
        passed=total >= PASS_THRESHOLD,
        rationale=str(data.get("rationale", "")),
    )
