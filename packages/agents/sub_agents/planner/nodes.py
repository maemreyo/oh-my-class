"""Planner Agent — LangGraph node function.

Generates structured lesson plans using backward design (UbD) principles
and Gagné's 9-event instruction model. Output validated against LessonPlan schema.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from common.contracts.lesson_plan import LessonPlan
from common.contracts.lesson_sequence import SessionPlan

if TYPE_CHECKING:
    from packages.agents.sub_agents.planner.state import PlannerNodeState


@dataclass(frozen=True, slots=True)
class PlannerDriftError(Exception):
    reason: str

    def __str__(self) -> str:
        return f"planner_seed_drift: {self.reason}"


async def planner_node(state: PlannerNodeState) -> dict[str, Any]:
    """Design a lesson blueprint from raw_request + class_info.

    Returns: {"lesson_plan": {...}}
    """
    seed = state.get("seed")
    if seed is not None:
        session_seed = SessionPlan.model_validate(seed)
        plan = expand_lesson_plan_from_seed(session_seed, state)
        ensure_seed_alignment(plan, session_seed)
        return {"lesson_plan": plan.model_dump()}

    from packages.agents.sub_agents.planner.prompts import load_system_prompt
    planner_system_prompt = load_system_prompt()

    user_prompt = f"""
Teacher request: {state['raw_request']}

Class information:
- Grade: {state['class_info'].get('grade', 'Unknown')}
- Subject: {state['class_info'].get('subject', 'Unknown')}
- Student count: {state['class_info'].get('student_count', 'Unknown')}
- Language: {state['class_info'].get('language', 'en')}
"""

    from packages.agents.config.models import MODELS
    from packages.agents.llm import (
        chat_messages,
        compiled_json_chat,
        extract_json_text,
        log_llm_failure,
        log_llm_start,
        log_llm_success,
    )
    from packages.agents.prompts.compiler import PromptCompiler
    from packages.agents.prompts.seed import create_seeded_registry

    model = MODELS.planner
    run_id = str(state.get("run_id", ""))
    step = int(state.get("current_step", 3))
    system_prompt = (
        planner_system_prompt
        + "\n\nCRITICAL: Respond ONLY with a single JSON object. "
        "No prose, no explanation, no markdown code fences."
    )
    messages = chat_messages(system_prompt, user_prompt)
    compiled = PromptCompiler(create_seeded_registry()).compile(
        module_id="planner_v1", variables={},
    )

    for attempt in range(3):
        attempt_number = attempt + 1
        started = log_llm_start("planner", run_id, step, model, attempt_number)
        try:
            content = await compiled_json_chat(
                model=model,
                compiled=compiled,
                messages=messages,
                temperature=0.3 if attempt > 0 else 0.7,
                tags=[
                    "agent:planner",
                    f"step:{state.get('current_step', 3)}",
                    f"run:{state.get('run_id', '')}",
                    f"attempt:{attempt_number}",
                    "pipeline:oh-my-class",
                ],
            )
            log_llm_success("planner", run_id, step, model, attempt_number, started)
            json_str = extract_json_text(content)
            plan_data = json.loads(json_str)
            plan = LessonPlan.model_validate(plan_data)
            return {"lesson_plan": plan.model_dump()}
        except (ValueError, json.JSONDecodeError) as parse_err:
            log_llm_failure(
                "planner", run_id, step, model, attempt_number, started, parse_err,
            )
            if attempt < 2:
                messages = chat_messages(
                    system_prompt,
                    "Invalid response. Return ONLY the JSON object.",
                )
                continue
            raise ValueError(f"Planner agent failed: {parse_err}") from parse_err
        except Exception as e:
            log_llm_failure("planner", run_id, step, model, attempt_number, started, e)
            if attempt < 2:
                continue
            raise ValueError(f"Planner agent failed: {e}") from e

    raise ValueError("Planner agent failed: exhausted retries")


def expand_lesson_plan_from_seed(seed: SessionPlan, state: PlannerNodeState) -> LessonPlan:
    class_info = state.get("class_info", {})
    return LessonPlan(
        topic=seed.sub_topic,
        grade_level=str(class_info.get("grade", class_info.get("grade_band", "Grade 5"))),
        subject=str(class_info.get("subject", "general")),
        duration_minutes=seed.duration_minutes,
        learning_objectives=[
            {
                "description": objective,
                "bloom_level": seed.bloom_level_primary,
                "assessment_method": "aligned formative check",
            }
            for objective in seed.learning_objectives
        ],
        prerequisite_knowledge=[component.title for component in seed.knowledge_components],
        learning_plan={
            "gain_attention": f"Anchor {seed.sub_topic} in a quick prior-knowledge prompt.",
            "state_objectives": "; ".join(seed.learning_objectives),
            "present_content": f"Teach fixed KCs: {', '.join(kc.kc_id for kc in seed.knowledge_components)}.",
            "provide_guidance": "Use the approved unit methodology and pacing.",
            "elicit_performance": "Students complete a short aligned task.",
            "provide_feedback": "Teacher gives immediate criterion-based feedback.",
            "assess_performance": "Exit ticket checks the approved objective.",
            "enhance_retention": "Recall the KC in the next unit session.",
        },
        assessment_checkpoints=[
            {
                "type": "exit_ticket",
                "description": f"Check {seed.bloom_level_primary} mastery for {seed.sub_topic}.",
                "trigger": "lesson_end",
            },
        ],
    )


def ensure_seed_alignment(plan: LessonPlan, seed: SessionPlan) -> None:
    if plan.duration_minutes != seed.duration_minutes:
        raise PlannerDriftError("duration_changed")
    expected_objectives = set(seed.learning_objectives)
    actual_objectives = {objective.description for objective in plan.learning_objectives}
    if not actual_objectives.issubset(expected_objectives):
        raise PlannerDriftError("objective_added")
    if {objective.bloom_level for objective in plan.learning_objectives} != {seed.bloom_level_primary}:
        raise PlannerDriftError("bloom_changed")
    expected_kcs = {component.title for component in seed.knowledge_components}
    if not expected_kcs.issubset(set(plan.prerequisite_knowledge)):
        raise PlannerDriftError("kc_dropped")
