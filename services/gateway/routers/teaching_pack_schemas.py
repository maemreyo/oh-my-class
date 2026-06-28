from __future__ import annotations

from pydantic import BaseModel, Field

from services.gateway.models import RunStatus  # noqa: TC001  Pydantic resolves field annotations
from services.gateway.teaching_pack_types import (
    JsonObject,  # noqa: TC001  Pydantic resolves field annotations
)


class TeachingPackCreateRunRequest(BaseModel):
    raw_request: str = Field(min_length=1)
    class_info: JsonObject = Field(default_factory=dict)


class TeachingPackRunAcceptedResponse(BaseModel):
    run_id: str
    job_id: str | None
    status: RunStatus
    queued: bool = False


class TeachingPackResumeRequest(BaseModel):
    gate_id: str = Field(min_length=1)
    gate_name: str = Field(min_length=1)
    action: str = Field(min_length=1)
    response: JsonObject = Field(default_factory=dict)


class TeachingPackResumeAcceptedResponse(BaseModel):
    run_id: str
    response_id: str
    job_id: str


class TeachingPackCancelResponse(BaseModel):
    run_id: str
    status: RunStatus
    cancelled_jobs: int


class TeachingPackDeleteResponse(BaseModel):
    run_id: str
    deleted: bool


class TeachingPackRestoreResponse(BaseModel):
    run_id: str
    restored: bool
