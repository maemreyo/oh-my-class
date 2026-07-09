"""Reviewer Agent — LangGraph node function.

LLM-as-Judge with G-Eval scoring. Uses 4omc (different from generator)
to avoid self-review bias.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from packages.agents.sub_agents.reviewer.state import ReviewerState


async def reviewer_node(state: ReviewerState) -> dict[str, Any]:
    """Review artifacts using G-Eval criteria.

    Returns: {"quality_scores": {...}, "quality_passed": bool}
    """
    from packages.quality.layer4_judge.judge_interface import AdaptiveJudge
    from packages.agents.config.models import MODELS
    from packages.agents.runtime import AgentRuntime, AgentRuntimeConfig
    from packages.agents.teaching_pack.stages import StageEnum, stage_number

    artifacts = state.get("artifacts") or []
    lesson_plan = state.get("lesson_plan")
    run_id = str(state.get("run_id", ""))
    current_step = state.get("current_step", StageEnum.RENDER_QUALITY)
    step = stage_number(current_step)
    runtime = AgentRuntime(AgentRuntimeConfig(
        agent="reviewer",
        run_id=run_id,
        step=step,
        step_label=current_step.value,
        model=MODELS.reviewer,
        base_temperature=0.3,
        retry_temperature=0.3,
    ))

    async def runtime_transport(
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float,
        extra_body: dict[str, Any],
    ) -> str:
        _ = model
        tags = extra_body.get("metadata", {}).get("tags", [])
        extra_tags = tuple(tag for tag in tags if isinstance(tag, str) and not tag.startswith(("agent:", "pipeline:")))
        judge_tag = next((tag for tag in extra_tags if tag.startswith("judge:")), "judge:1")
        attempt = max(int(judge_tag.split(":", 1)[1]) - 1, 0)
        return await runtime.complete_json(
            messages=messages,
            attempt=attempt,
            extra_tags=extra_tags,
            temperature=temperature,
        )

    artifact_type = str(artifacts[0].get("artifact_type", "lesson")) if artifacts else "lesson"
    from packages.agents.config.gate_config import GateConfig
    judge = AdaptiveJudge(model=MODELS.reviewer, llm_transport=runtime_transport, num_judges=GateConfig().judge_n)
    result = await judge.judge(
        artifacts=artifacts,
        artifact_type=artifact_type,
        lesson_plan=lesson_plan,
    )
    judge_output = result.judge_output

    return {
        "quality_scores": {
            **judge_output.model_dump(),
            "rubric_version": result.rubric_version,
            "rubric_description": result.rubric_description,
            "deterministic_blocked": result.deterministic_blocked,
            "hard_block_violations": result.hard_block_violations,
        },
        "quality_passed": judge_output.passed,
    }
