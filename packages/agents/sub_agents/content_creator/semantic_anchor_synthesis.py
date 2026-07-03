from __future__ import annotations

import json
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from common.contracts.vocabulary_batch import (
    LexicalGroundingBundle,
    NormalizedVocabularyCluster,
    SemanticAnchorCluster,
)


type PromptPayload = dict[str, str | dict[str, str | list[str] | dict[str, object]]]


class StudentAnchorCard(BaseModel):
    model_config = ConfigDict(frozen=True)

    word: str = Field(min_length=1, max_length=120)
    impression_vi: str = Field(min_length=1, max_length=300)
    core_trigger_en: str = Field(min_length=1, max_length=120)
    visual_cue_vi: str = Field(min_length=1, max_length=300)
    semantic_chain: tuple[str, ...] = Field(min_length=1, max_length=8)
    example_en: str = Field(min_length=1, max_length=500)
    contrast_note_vi: str = Field(min_length=1, max_length=500)
    student_explanation_vi: str = Field(min_length=1, max_length=700)


class SemanticAnchorStudentProjection(BaseModel):
    model_config = ConfigDict(frozen=True)

    cluster_id: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=200)
    terms: tuple[str, ...] = Field(min_length=2)
    anchors: tuple[StudentAnchorCard, ...] = Field(min_length=1)
    contrast_notes: tuple[str, ...] = Field(min_length=1)
    summary_rows: tuple[str, ...] = Field(min_length=1)


@dataclass(frozen=True, slots=True)
class SemanticAnchorSynthesisFailed(Exception):
    cluster_id: str
    attempts: int
    validation_error: str

    def __str__(self) -> str:
        return (
            f"semantic anchor synthesis failed for {self.cluster_id} "
            f"after {self.attempts} attempts: {self.validation_error}"
        )


@dataclass(frozen=True, slots=True)
class SemanticAnchorPromptContext:
    cluster: NormalizedVocabularyCluster
    grounding: LexicalGroundingBundle
    validation_feedback: str | None = None
    previous_output: str | None = None


async def synthesize_semantic_anchor_cluster(
    cluster: NormalizedVocabularyCluster,
    grounding: LexicalGroundingBundle,
    run_id: str,
) -> SemanticAnchorCluster:
    from packages.agents.config.models import MODELS
    from packages.agents.llm import extract_json_text
    from packages.agents.runtime import AgentRuntime, AgentRuntimeConfig
    from packages.agents.teaching_pack.stages import StageEnum, stage_number

    system_prompt = _system_prompt()
    user_prompt = _user_prompt(cluster, grounding)
    last_error = "unknown validation error"
    current_step = StageEnum.ARTIFACT_WORKFLOW
    runtime = AgentRuntime(AgentRuntimeConfig(
        agent="content_creator",
        run_id=run_id,
        step=stage_number(current_step),
        step_label=current_step.value,
        model=MODELS.content_creator,
        base_temperature=0.3,
        retry_temperature=0.3,
    ))

    for attempt in range(3):
        content = await runtime.complete_json(
            messages=runtime.messages(system_prompt, user_prompt),
            attempt=attempt,
            extra_tags=("profile:semantic_anchor_synthesis",),
        )
        try:
            data = json.loads(extract_json_text(content))
            return SemanticAnchorCluster.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as exc:
            last_error = str(exc)
            user_prompt = _retry_prompt(cluster, grounding, last_error, content)

    raise SemanticAnchorSynthesisFailed(
        cluster_id=cluster.cluster_id,
        attempts=3,
        validation_error=last_error,
    )


def semantic_anchor_student_projection(cluster: SemanticAnchorCluster) -> SemanticAnchorStudentProjection:
    return SemanticAnchorStudentProjection(
        cluster_id=cluster.cluster_id,
        title=cluster.title,
        terms=cluster.terms,
        anchors=tuple(
            StudentAnchorCard(
                word=anchor.word,
                impression_vi=anchor.impression_vi,
                core_trigger_en=anchor.core_trigger_en,
                visual_cue_vi=anchor.visual_cue_vi,
                semantic_chain=anchor.semantic_chain,
                example_en=anchor.example_en,
                contrast_note_vi=anchor.contrast_note_vi,
                student_explanation_vi=anchor.student_explanation_vi,
            )
            for anchor in cluster.anchors
        ),
        contrast_notes=cluster.contrast_notes,
        summary_rows=cluster.summary_rows,
    )


def _system_prompt() -> str:
    return (
        "You are the Content Creator running semantic_anchor_synthesis. "
        "Return one JSON object matching SemanticAnchorCluster only. "
        "Produce RCM data, not HTML and not practice items. "
        "Student-facing fields must be compact; teacher scripts and source notes stay teacher-facing."
    )


def _user_prompt(cluster: NormalizedVocabularyCluster, grounding: LexicalGroundingBundle) -> str:
    return _prompt_payload(SemanticAnchorPromptContext(cluster=cluster, grounding=grounding))


def _retry_prompt(
    cluster: NormalizedVocabularyCluster,
    grounding: LexicalGroundingBundle,
    validation_feedback: str,
    previous_output: str,
) -> str:
    return _prompt_payload(SemanticAnchorPromptContext(
        cluster=cluster,
        grounding=grounding,
        validation_feedback=validation_feedback,
        previous_output=previous_output,
    ))


def _prompt_payload(context: SemanticAnchorPromptContext) -> str:
    payload: PromptPayload = {
        "profile": "semantic_anchor_synthesis",
        "cluster": context.cluster.model_dump(mode="json"),
        "lexical_grounding": context.grounding.model_dump(mode="json"),
        "required_output": {
            "type": "SemanticAnchorCluster",
            "bilingual_anchor_fields": [
                "impression_vi",
                "core_trigger_en",
                "visual_cue_vi",
                "semantic_chain",
                "example_en",
                "contrast_note_vi",
                "student_explanation_vi",
                "teacher_script_vi",
            ],
            "teacher_only_fields": ["teacher_script_vi", "source_notes", "teacher_source_notes"],
            "forbidden_outputs": ["raw_html", "practice_items", "export_files"],
        },
    }
    if context.validation_feedback is not None and context.previous_output is not None:
        payload["validation_feedback"] = (
            "Previous output failed SemanticAnchorCluster validation: "
            f"{context.validation_feedback}"
        )
        payload["previous_output"] = context.previous_output
    return json.dumps(payload, ensure_ascii=False, indent=2)
