from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from common.contracts.vocabulary_batch import PracticeIntent, PracticeSet, SemanticAnchorCluster

RequiredPracticeIntent = Literal[
    "core_trigger_recall",
    "context_discrimination",
    "boundary_explanation",
    "reverse_retrieval",
]
REQUIRED_INTENTS: tuple[RequiredPracticeIntent, ...] = (
    "core_trigger_recall",
    "context_discrimination",
    "boundary_explanation",
    "reverse_retrieval",
)


class PracticeGenerationRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    cluster: SemanticAnchorCluster
    grade_band: str | None = Field(default=None, max_length=64)
    target_cefr: str | None = Field(default=None, max_length=16)
    exam_target: str | None = Field(default=None, max_length=120)


class StudentPracticeItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    item_id: str = Field(min_length=1, max_length=120)
    intent: PracticeIntent
    prompt: str = Field(min_length=1, max_length=1000)


class SemanticAnchorStudentPracticeProjection(BaseModel):
    model_config = ConfigDict(frozen=True)

    practice_set_id: str = Field(min_length=1, max_length=120)
    cluster_id: str = Field(min_length=1, max_length=120)
    items: tuple[StudentPracticeItem, ...] = Field(min_length=1)


class SemanticAnchorPracticeSet(PracticeSet):
    @model_validator(mode="after")
    def _covers_required_intents(self) -> SemanticAnchorPracticeSet:
        intents = {item.intent for item in self.items}
        if intents != set(REQUIRED_INTENTS):
            msg = "semantic anchor practice must cover all four required intents"
            raise ValueError(msg)
        return self


@dataclass(frozen=True, slots=True)
class PracticeGenerationFailed(Exception):
    cluster_id: str
    attempts: int
    validation_error: str

    def __str__(self) -> str:
        return (
            f"practice generation failed for {self.cluster_id} "
            f"after {self.attempts} attempts: {self.validation_error}"
        )


@dataclass(frozen=True, slots=True)
class PracticePromptContext:
    request: PracticeGenerationRequest
    validation_feedback: str | None = None
    previous_output: str | None = None


async def generate_semantic_anchor_practice(
    request: PracticeGenerationRequest,
    run_id: str,
) -> PracticeSet:
    from packages.agents.config.models import MODELS
    from packages.agents.llm import chat_messages, complete_json_chat, extract_json_text

    system_prompt = _system_prompt()
    user_prompt = _prompt_payload(PracticePromptContext(request=request))
    last_error = "unknown validation error"

    for attempt in range(3):
        content = await complete_json_chat(
            model=MODELS.content_creator,
            messages=chat_messages(system_prompt, user_prompt),
            temperature=0.3,
            tags=[
                "agent:practice_generator",
                "profile:semantic_anchor_practice",
                "step:8",
                f"run:{run_id}",
                f"attempt:{attempt + 1}",
                "pipeline:oh-my-class",
            ],
        )
        try:
            data = json.loads(extract_json_text(content))
            return SemanticAnchorPracticeSet.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as exc:
            last_error = str(exc)
            user_prompt = _prompt_payload(PracticePromptContext(
                request=request,
                validation_feedback=last_error,
                previous_output=content,
            ))

    raise PracticeGenerationFailed(
        cluster_id=request.cluster.cluster_id,
        attempts=3,
        validation_error=last_error,
    )


def student_practice_projection(practice: PracticeSet) -> SemanticAnchorStudentPracticeProjection:
    return SemanticAnchorStudentPracticeProjection(
        practice_set_id=practice.practice_set_id,
        cluster_id=practice.cluster_id,
        items=tuple(
            StudentPracticeItem(
                item_id=item.item_id,
                intent=item.intent,
                prompt=item.prompt,
            )
            for item in practice.items
        ),
    )


def _system_prompt() -> str:
    return (
        "You are the reusable PracticeGenerator running semantic_anchor_practice. "
        "Return one JSON object matching PracticeSet only. Emit typed practice items and teacher-only "
        "answer keys/rationales, not rendered HTML. Cover exactly the four required intents."
    )


def _prompt_payload(context: PracticePromptContext) -> str:
    request = context.request
    payload = {
        "profile": "semantic_anchor_practice",
        "cluster": request.cluster.model_dump(mode="json"),
        "difficulty_targets": {
            "grade_band": request.grade_band,
            "target_cefr": request.target_cefr,
            "exam_target": request.exam_target,
        },
        "required_intents": list(REQUIRED_INTENTS),
        "answer_key_policy": "prompt is student-facing; answer and rationale are teacher-only",
    }
    if context.validation_feedback is not None and context.previous_output is not None:
        payload["validation_feedback"] = (
            "Previous output failed PracticeSet validation: "
            f"{context.validation_feedback}"
        )
        payload["previous_output"] = context.previous_output
    return json.dumps(payload, ensure_ascii=False, indent=2)
