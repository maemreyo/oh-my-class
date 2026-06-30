"""G-Eval scoring framework — structured evaluation using LLM judges.

Implements the G-Eval methodology for automated content quality assessment.
Each layer is scored independently with weighted aggregation.

Scoring weights (from gate_config.yaml):
- format_compliance: 15%
- content_quality: 55%
- presentation: 30%

Pass threshold: overall_score >= 7.0 AND no critical issues.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from packages.quality.layer4_judge.config import QUALITY_MODELS

if TYPE_CHECKING:
    from common.contracts.judge_output import JudgeOutput


@dataclass
class GEvalConfig:
    """Configuration for G-Eval scoring."""

    pass_threshold: float = 7.0
    weights: dict[str, float] = field(default_factory=lambda: {
        "format_compliance": 0.15,
        "content_quality": 0.55,
        "presentation": 0.30,
    })
    num_judges: int = 3
    judge_model: str = QUALITY_MODELS.llm_judge


class GEvalScorer:
    """G-Eval scorer for Layer 4 quality assessment.

    Runs 3 independent judge calls with different random seeds,
    then aggregates via majority vote.

    Bias mitigations:
    - Rationale written before score (think-before-score)
    - 3 independent judge calls → majority vote
    - Generator model ≠ judge model
    - Explicit guard: "Do not rate longer answers higher"
    """

    def __init__(self, config: GEvalConfig | None = None) -> None:
        self.config = config or GEvalConfig()

    async def score(
        self,
        artifacts: list[dict[str, Any]],
        *,
        lesson_plan: dict[str, Any] | None = None,
    ) -> JudgeOutput:
        """Score artifacts using G-Eval across 3 layers.

        Args:
            artifacts: Generated artifact content dicts.
            lesson_plan: Original lesson plan for alignment scoring.

        Returns:
            JudgeOutput with scores, issues, and pass/fail status.
        """
        import json

        import litellm

        from common.contracts.judge_output import JudgeOutput
        from packages.quality.layer4_judge.majority_vote import majority_vote
        from packages.quality.layer4_judge.prompts import load_system_prompt

        reviewer_system_prompt = load_system_prompt()

        user_prompt = f"""
Evaluate the following teaching artifacts:

Artifacts:
{json.dumps(artifacts, indent=2)}

{f"Lesson Plan for alignment:{chr(10)}{json.dumps(lesson_plan, indent=2)}" if lesson_plan else ""}

Score each artifact across the 3 layers and provide overall assessment.
"""

        messages = [
            {"role": "system", "content": reviewer_system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        judge_outputs: list[JudgeOutput] = []
        for i in range(self.config.num_judges):
            try:
                response = await litellm.acompletion(
                    model=self.config.judge_model,
                    messages=messages,
                    temperature=0.3 + (i * 0.1),
                    extra_body={
                        "metadata": {
                            "tags": [
                                "agent:reviewer",
                                f"judge:{i + 1}",
                                "pipeline:oh-my-class",
                            ]
                        }
                    },
                )

                content = response.choices[0].message.content
                if "```json" in content:
                    json_str = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    json_str = content.split("```")[1].split("```")[0].strip()
                else:
                    json_str = content.strip()

                output_data = json.loads(json_str)
                judge_output = JudgeOutput.model_validate(output_data)
                judge_outputs.append(judge_output)

            except Exception:
                continue

        if not judge_outputs:
            raise ValueError("All judge calls failed")

        if len(judge_outputs) == 1:
            return judge_outputs[0]

        return majority_vote(judge_outputs)
