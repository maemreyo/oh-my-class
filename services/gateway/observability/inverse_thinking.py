from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Projection = Literal["lesson", "worksheet", "quiz", "drill"]
QualityGateStatus = Literal["passed", "failed", "warning"]
ExportStatus = Literal["passed", "failed"]
TeacherAction = Literal["approve", "edit", "reject"]


class InverseThinkingEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str = Field(min_length=1)
    methodology: Literal["inverse_thinking"]
    creative_frame: str = Field(min_length=1)
    projection: Projection
    feature_flag: Literal["inverse_thinking_v1"]
    quality_gate: QualityGateStatus
    repair_attempt: int = Field(ge=0)
    warning_category: str | None = None
    teacher_action: TeacherAction | None = None
    export_status: ExportStatus | None = None


def build_inverse_thinking_metadata(event: InverseThinkingEvent) -> dict[str, str | int]:
    metadata: dict[str, str | int] = {
        "run_id": event.run_id,
        "methodology": event.methodology,
        "creative_frame": event.creative_frame,
        "projection": event.projection,
        "feature_flag": event.feature_flag,
        "quality_gate": event.quality_gate,
        "repair_attempt": event.repair_attempt,
    }
    if event.warning_category is not None:
        metadata["warning_category"] = event.warning_category
    if event.teacher_action is not None:
        metadata["teacher_action"] = event.teacher_action
    if event.export_status is not None:
        metadata["export_status"] = event.export_status
    return metadata
