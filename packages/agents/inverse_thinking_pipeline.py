from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal, assert_never

from pydantic import BaseModel, ConfigDict, Field

from common.contracts.inverse_thinking import CreativeFrame, InverseThinkingPack
from packages.methodologies.inverse_thinking import (
    InverseThinkingProjection,
    normalize_pack,
    project_drill,
    project_lesson,
    project_quiz,
    project_worksheet,
)
from packages.quality.layer2_content.inverse_thinking import validate_inverse_thinking_pack
from packages.quality.layer2_content.pii import PiiAuditEvent, scrub_pii

InverseThinkingArtifactType = Literal["lesson", "worksheet", "quiz", "drill"]
FeatureFlags = Mapping[str, bool]
_SUPPORTED_ARTIFACTS: frozenset[str] = frozenset({"lesson", "worksheet", "quiz", "drill"})


class InverseThinkingPipelineRequest(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    teacher_request: str = Field(min_length=1)
    artifact_types: list[str] = Field(min_length=1)
    feature_flags: FeatureFlags
    canonical_pack: InverseThinkingPack | dict[str, Any]
    repair_attempt: int = Field(default=0, ge=0)


class InverseThinkingPipelineResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    canonical_pack: InverseThinkingPack
    lesson_blueprint: dict[str, Any]
    visual_spec: dict[str, str]
    projections: dict[InverseThinkingArtifactType, InverseThinkingProjection]
    metadata_tags: list[str]
    pii_audit_event: PiiAuditEvent


def inverse_thinking_pipeline(request: InverseThinkingPipelineRequest) -> InverseThinkingPipelineResult:
    _ensure_enabled(request.feature_flags)
    artifact_types = _scope_artifacts(request.artifact_types)
    scrubbed_request = scrub_pii(request.teacher_request)
    scrubbed_pack = scrub_pii(request.canonical_pack)
    canonical_pack = normalize_pack(scrubbed_pack.value)
    gate_result = validate_inverse_thinking_pack(canonical_pack)
    if not gate_result.passed:
        first_issue = gate_result.issues[0]
        msg = f"inverse-thinking quality gate failed: {first_issue.field_path}: {first_issue.repair_instruction}"
        raise ValueError(msg)
    frame = _resolve_frame(canonical_pack.creative_frame, scrubbed_request.value)
    visual_spec = {
        "creative_frame": frame,
        "rationale": _frame_rationale(canonical_pack.creative_frame),
    }
    projections: dict[InverseThinkingArtifactType, InverseThinkingProjection] = {
        artifact_type: _project(artifact_type, canonical_pack)
        for artifact_type in artifact_types
    }
    return InverseThinkingPipelineResult(
        canonical_pack=canonical_pack,
        lesson_blueprint={
            "methodology": {
                "tags": ["inverse_thinking"],
                "payloads": {"inverse_thinking": canonical_pack.model_dump()},
            },
            "visual_engine": visual_spec,
        },
        visual_spec=visual_spec,
        projections=projections,
        metadata_tags=[
            "methodology:inverse_thinking",
            f"creative_frame:{frame}",
            "feature_flag:inverse_thinking_v1",
            f"repair_attempt:{request.repair_attempt}",
        ],
        pii_audit_event=_merge_audit_events(scrubbed_request.audit_event, scrubbed_pack.audit_event),
    )


def _merge_audit_events(left: PiiAuditEvent, right: PiiAuditEvent) -> PiiAuditEvent:
    categories = set(left.redaction_counts) | set(right.redaction_counts)
    return PiiAuditEvent(
        redaction_counts={category: left.redaction_counts.get(category, 0) + right.redaction_counts.get(category, 0) for category in categories},
        token_hashes={
            category: left.token_hashes.get(category, ()) + right.token_hashes.get(category, ())
            for category in categories
        },
        low_confidence_hashes=left.low_confidence_hashes + right.low_confidence_hashes,
    )


def _ensure_enabled(feature_flags: FeatureFlags) -> None:
    if not feature_flags.get("inverse_thinking_v1", False):
        msg = "features.inverse_thinking_v1 must be enabled for inverse-thinking generation"
        raise ValueError(msg)


def _scope_artifacts(artifact_types: list[str]) -> list[InverseThinkingArtifactType]:
    unsupported = [artifact_type for artifact_type in artifact_types if artifact_type not in _SUPPORTED_ARTIFACTS]
    if unsupported:
        msg = f"inverse-thinking v1 does not support: {', '.join(unsupported)}"
        raise ValueError(msg)
    scoped: list[InverseThinkingArtifactType] = []
    for artifact_type in artifact_types:
        match artifact_type:
            case "lesson" | "worksheet" | "quiz" | "drill":
                scoped.append(artifact_type)
            case _:
                continue
    return scoped


def _resolve_frame(frame: CreativeFrame, teacher_request: str) -> CreativeFrame:
    if frame != "auto":
        return frame
    request = teacher_request.lower()
    if "court" in request or "trial" in request:
        return "courtroom_trial"
    if "survival" in request:
        return "survival_guide"
    if "lab" in request or "myth" in request:
        return "mythbusters_lab"
    if "report" in request:
        return "disaster_report"
    return "detective_case"


def _frame_rationale(frame: CreativeFrame) -> str:
    if frame == "auto":
        return "auto_resolved_from_teacher_request"
    return "teacher_or_pack_selected"


def _project(
    artifact_type: InverseThinkingArtifactType,
    pack: InverseThinkingPack,
) -> InverseThinkingProjection:
    match artifact_type:
        case "lesson":
            return project_lesson(pack)
        case "worksheet":
            return project_worksheet(pack)
        case "quiz":
            return project_quiz(pack)
        case "drill":
            return project_drill(pack)
        case unreachable:
            assert_never(unreachable)
