"""Prompt construction for the LLM judge.

Builds system and user prompts with rubric formatting for the judge model.
Separated from the judge interface to keep prompt logic independently testable.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from common.contracts.rubric import Rubric

# ---------------------------------------------------------------------------
# Judge system prompt template
# ---------------------------------------------------------------------------

JUDGE_SYSTEM_PROMPT = """\
You are an expert educational content reviewer.

Score the provided teaching artifacts using the rubric below. For each criterion,
assign a score from 0-10 based on the rubric levels.

The artifacts are pre-render JSON content (title/sections/objectives), not final
rendered HTML. Do NOT check for or penalize the absence of HTML markup, DOCTYPE,
branding strings, external assets, or form-input rendering — those are validated
separately by deterministic gates downstream, after this content is rendered.
Judge only what is present in the JSON: pedagogical structure, content accuracy,
and readability of the text itself. Sections marked `"teacher_only": true` (e.g.
answer keys) are stripped by the renderer before students see the artifact —
do not flag their presence as answer-key leakage.

Rubric (version {rubric_version}):
{rubric_text}

IMPORTANT RULES:
- Write your rationale BEFORE giving numeric scores (think-before-score).
- Do NOT rate longer answers higher.
- Be precise and honest — flag real issues.
- Return ONLY valid JSON matching this schema:
{{
  "overall_score": <0-10>,
  "layer_scores": [{{"layer": "<name>", "score": <0-10>, "weight": <0-1>}}],
  "critical_issues": ["..."],
  "passed": <bool>,
  "rationale": "...",
  "teacher_facing_summary": "one short teacher-facing explanation of the verdict"
}}
"""


def build_rubric_text(rubric: Rubric) -> str:
    """Format rubric criteria into a human-readable prompt section."""
    lines: list[str] = []
    for criterion in rubric.criteria:
        lines.append(f"\n### {criterion.name} (weight: {criterion.weight:.0%})")
        for level in criterion.levels:
            lines.append(f"  Score {level.score}: {level.description}")
        if criterion.descriptors:
            for key, desc in criterion.descriptors.items():
                lines.append(f"  [{key}] {desc}")
    return "\n".join(lines)


def build_user_prompt(
    artifacts: list[dict[str, Any]],
    lesson_plan: dict[str, Any] | None = None,
    deterministic_issues: list[str] | None = None,
) -> str:
    """Build the user prompt containing artifacts and context."""
    parts = [
        "Evaluate the following teaching artifacts:\n",
        f"Artifacts:\n{json.dumps(artifacts, indent=2, ensure_ascii=False)}",
    ]
    if lesson_plan:
        lp_json = json.dumps(lesson_plan, indent=2, ensure_ascii=False)
        parts.append(f"\nLesson Plan for alignment:\n{lp_json}")
    if deterministic_issues:
        parts.append(
            f"\n⚠️  Deterministic gates already flagged these issues: "
            f"{', '.join(deterministic_issues)}\n"
            f"Focus your review on the areas NOT covered by these flags."
        )
    parts.append("\nScore each criterion and provide overall assessment.")
    return "\n\n".join(parts)
