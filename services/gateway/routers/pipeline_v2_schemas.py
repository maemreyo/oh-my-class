from __future__ import annotations

from pydantic import BaseModel, Field

from services.gateway.models import RunStatus  # noqa: TC001  Pydantic resolves field annotations
from services.gateway.pipeline_v2_types import (
    JsonObject,  # noqa: TC001  Pydantic resolves field annotations
)


class PipelineV2CreateRunRequest(BaseModel):
    raw_request: str = Field(min_length=1)
    class_info: JsonObject = Field(default_factory=dict)


class PipelineV2RunAcceptedResponse(BaseModel):
    run_id: str
    job_id: str | None
    status: RunStatus
    queued: bool = False


class PipelineV2ResumeRequest(BaseModel):
    gate_id: str = Field(min_length=1)
    gate_name: str = Field(min_length=1)
    action: str = Field(min_length=1)
    response: JsonObject = Field(default_factory=dict)


class PipelineV2ResumeAcceptedResponse(BaseModel):
    run_id: str
    response_id: str
    job_id: str


class PipelineV2CancelResponse(BaseModel):
    run_id: str
    status: RunStatus
    cancelled_jobs: int


class PipelineV2DeleteResponse(BaseModel):
    run_id: str
    deleted: bool


class PipelineV2RestoreResponse(BaseModel):
    run_id: str
    restored: bool
