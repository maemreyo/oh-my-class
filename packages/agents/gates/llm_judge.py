"""Layer 4: G-Eval LLM judge (f.pro, single judge MVP)."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from packages.agents.config.gate_config import GateConfig
from packages.quality.layer2_content.component_scorer import score_component_usage

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


_MIN_WORDS_BY_TYPE = {
    "lesson": 180,
    "worksheet": 90,
    "quiz": 60,
    "drill": 80,
    "recap": 80,
    "infographic": 60,
}


def _extract_text_content(artifact: dict[str, Any]) -> str:
    """Extract concatenated text from an artifact's sections list."""
    sections = artifact.get("sections") or []
    parts: list[str] = []
    for section in sections:
        text = section.get("content", "")
        if isinstance(text, str) and text.strip():
            parts.append(text.strip())
    return "\n".join(parts)


def _word_count(text: str) -> int:
    return len([word for word in text.split() if word.strip()])


def _section_title_score(artifact: dict[str, Any]) -> float:
    sections = artifact.get("sections") or []
    if not sections:
        return 0.0
    titled = [
        section for section in sections
        if isinstance(section, dict) and str(section.get("title", "")).strip()
    ]
    return len(titled) / len(sections)


def _score_artifact(
    artifact: dict[str, Any],
    lesson_plan: dict[str, Any] | None,
    component_score: float,
) -> float:
    """Score artifact strength until the real multi-judge is wired.

    The heuristic intentionally fails sparse content so the healing loop runs
    instead of exporting a tiny teaching pack with a fake high score.
    """
    content = _extract_text_content(artifact)
    if not content or not content.strip():
        return 0.0
    artifact_type = str(artifact.get("artifact_type", "lesson"))
    minimum_words = _MIN_WORDS_BY_TYPE.get(artifact_type, 80)
    word_score = min(_word_count(content) / minimum_words, 1.0) * 5.0
    section_score = _section_title_score(artifact) * 2.0
    objective_bonus = 1.0 if lesson_plan and lesson_plan.get("learning_objectives") else 0.0
    structure_bonus = 2.0 if len(artifact.get("sections") or []) >= 3 else 1.0
    component_bonus = max(0.0, (component_score - 5.0) / 5.0) * 1.0
    total = word_score + section_score + objective_bonus + structure_bonus + component_bonus
    return round(min(total, 10.0), 2)


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

    component_scores = [
        score_component_usage(a, lesson_plan)
        for a in artifacts
    ]
    scores = [
        _score_artifact(artifact, lesson_plan, component.score)
        for artifact, component in zip(artifacts, component_scores, strict=True)
    ]
    overall = sum(scores) / len(scores)
    quality_scores = {
        "overall": round(overall, 2),
        "per_artifact": scores,
        "components": [
            {
                "score": score.score,
                "component_count": score.component_count,
                "unique_intents": score.unique_intents,
                "methodology_bonus": score.methodology_bonus,
                "stuffing_penalty": score.stuffing_penalty,
                "overuse_penalty": score.overuse_penalty,
                "notes": score.notes,
            }
            for score in component_scores
        ],
        "method": "heuristic_content_strength",
    }

    if overall < config.judge_min_score:
        return {
            "judge_score": overall,
            "quality_scores": quality_scores,
            "fail_layer": "judge",
            "fail_type": "score",
            "fail_count": state.get("fail_count", 0),
            "fail_context": {
                "errors": [f"Judge score {overall:.1f} below threshold {config.judge_min_score}"],
                "per_artifact_scores": scores,
            },
        }

    return {"judge_score": overall, "quality_scores": quality_scores}
