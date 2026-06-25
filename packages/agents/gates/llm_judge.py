"""Layer 4: G-Eval LLM judge (f.pro, single judge MVP)."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from packages.agents.config.gate_config import GateConfig

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


def _score_artifact(artifact: dict[str, Any], lesson_plan: dict[str, Any] | None) -> float:
    """Stub: score an artifact. Returns 8.0 in MVP (real impl calls f.pro).

    Dimensions: relevance, accuracy, clarity, age_appropriateness, curriculum_alignment.
    """
    content = artifact.get("content", "")
    if not content or not content.strip():
        return 0.0
    return 8.0


def step_10b_llm_judge(state: OhMyClassState) -> dict[str, Any]:
    """Layer 4: LLM-as-Judge using G-Eval pattern.

    Scores each artifact on 5 dimensions. Returns overall score.
    Routes to healing if score < judge_min_score.
    """
    config = GateConfig()
    artifacts = state.get("artifacts") or []
    lesson_plan = state.get("lesson_plan")

    if not artifacts:
        return {
            "judge_score": 0.0,
            "fail_layer": "judge",
            "fail_type": "score",
            "fail_count": state.get("fail_count", 0),
            "fail_context": {"errors": ["No artifacts to judge"]},
        }

    scores = [_score_artifact(a, lesson_plan) for a in artifacts]
    overall = sum(scores) / len(scores)

    if overall < config.judge_min_score:
        return {
            "judge_score": overall,
            "fail_layer": "judge",
            "fail_type": "score",
            "fail_count": state.get("fail_count", 0),
            "fail_context": {
                "errors": [f"Judge score {overall:.1f} below threshold {config.judge_min_score}"],
                "per_artifact_scores": scores,
            },
        }

    return {"judge_score": overall}
