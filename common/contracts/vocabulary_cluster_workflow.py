from __future__ import annotations

from typing import Literal, assert_never

from pydantic import BaseModel, ConfigDict, Field, field_validator

type JsonValue = str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, JsonValue]

VocabularyClusterStatus = Literal[
    "queued",
    "grounding",
    "synthesizing",
    "practice_generating",
    "validating",
    "needs_review",
    "passed",
    "failed",
    "skipped",
    "exported",
]
VocabularyClusterReviewStatus = Literal["pending", "needs_review", "approved", "rejected"]
VocabularyClusterEvidenceType = Literal[
    "normalized_input",
    "grounding_sources",
    "generated_contract_version",
    "quality_result",
    "teacher_edit",
    "approval",
    "export_ref",
    "retry",
]

_FORBIDDEN_EVIDENCE_KEYS = frozenset({
    "chain_of_thought",
    "internal_prompt",
    "provider_raw_response",
    "raw_provider_response",
})


class VocabularyClusterWorkflow(BaseModel):
    model_config = ConfigDict(frozen=True)

    workflow_id: str = Field(min_length=1, max_length=120)
    cluster_id: str = Field(min_length=1, max_length=120)
    run_id: str = Field(min_length=1, max_length=120)
    normalized_input: tuple[str, ...] = Field(min_length=1)
    raw_input_span: str = Field(min_length=1, max_length=2000)
    status: VocabularyClusterStatus
    attempts: int = Field(ge=0, le=20)
    review_status: VocabularyClusterReviewStatus
    export_refs: dict[str, str] = Field(default_factory=dict)
    snapshot_hash: str | None = Field(default=None, min_length=64, max_length=64)
    last_error: str | None = Field(default=None, max_length=1000)


class VocabularyClusterEvidenceEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    evidence_id: str = Field(min_length=1, max_length=120)
    workflow_id: str = Field(min_length=1, max_length=120)
    cluster_id: str = Field(min_length=1, max_length=120)
    run_id: str = Field(min_length=1, max_length=120)
    sequence: int = Field(ge=1)
    event_type: VocabularyClusterEvidenceType
    payload: JsonObject

    @field_validator("payload")
    @classmethod
    def _reject_internal_payload(cls, value: JsonObject) -> JsonObject:
        if _contains_forbidden_key(value):
            msg = "evidence payload must not store provider raw responses, prompts, or chain-of-thought"
            raise ValueError(msg)
        return value


def apply_cluster_transition(
    current: VocabularyClusterStatus,
    target: VocabularyClusterStatus,
) -> VocabularyClusterStatus:
    allowed = _allowed_targets(current)
    if target not in allowed:
        msg = f"Illegal vocabulary cluster transition: {current} -> {target}"
        raise ValueError(msg)
    return target


def _allowed_targets(status: VocabularyClusterStatus) -> tuple[VocabularyClusterStatus, ...]:
    match status:
        case "queued":
            return ("grounding", "skipped", "failed")
        case "grounding":
            return ("synthesizing", "needs_review", "failed")
        case "synthesizing":
            return ("practice_generating", "needs_review", "failed")
        case "practice_generating":
            return ("validating", "needs_review", "failed")
        case "validating":
            return ("passed", "needs_review", "failed")
        case "needs_review":
            return ("grounding", "synthesizing", "practice_generating", "validating", "passed", "failed")
        case "passed":
            return ("exported", "needs_review")
        case "failed":
            return ("queued",)
        case "skipped":
            return ("queued",)
        case "exported":
            return ()
        case unreachable:
            assert_never(unreachable)


def _contains_forbidden_key(value: JsonValue) -> bool:
    match value:
        case dict():
            return any(key in _FORBIDDEN_EVIDENCE_KEYS or _contains_forbidden_key(nested) for key, nested in value.items())
        case list():
            return any(_contains_forbidden_key(item) for item in value)
        case str() | int() | float() | bool() | None:
            return False
        case unreachable:
            assert_never(unreachable)
