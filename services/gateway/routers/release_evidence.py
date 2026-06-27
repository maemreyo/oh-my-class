"""Release evidence API — query audit records for completed runs.

Endpoints:
  GET  /pipeline-v2/run/{run_id}/evidence       — evidence for a specific run
  POST /pipeline-v2/run/{run_id}/evidence       — generate + persist evidence (admin)
  GET  /pipeline-v2/release-evidence            — list recent evidence (admin)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from services.gateway.auth.dependencies import require_admin, require_teacher
from services.gateway.auth.models import User  # noqa: TC001
from services.gateway.pipeline_v2_db import get_pipeline_v2_session
from services.gateway.pipeline_v2_types import RunId
from services.gateway.provider_evidence import (
    ProviderEvidenceEntry,
    ProviderProbeConfig,
    collect_provider_evidence,
)
from services.gateway.release_evidence import (
    ReleaseEvidence,
    generate_evidence,
    write_evidence_report,
)
from services.gateway.release_evidence_store import (
    get_evidence,
    list_evidence,
    save_evidence,
)

router = APIRouter()

PIPELINE_V2_SESSION = Depends(get_pipeline_v2_session)
EVIDENCE_REPORT_DIR = Path(".scratch/pipeline-v2/artifacts")

# Default 9Router target for provider evidence collection.
# Override via env for different environments (dev/prod).
_DEFAULT_PROVIDER_BASE_URL = os.getenv("OMC_9ROUTER_BASE_URL", "http://127.0.0.1:20228")
_DEFAULT_PROVIDER_MODEL = os.getenv("OMC_9ROUTER_MODEL", "4omc")


# ── Response schemas ─────────────────────────────────────────────────


class ProviderEvidenceResponse(BaseModel):
    base_url: str
    model: str
    timestamp: str
    status: str
    elapsed_s: float
    models_endpoint_ok: bool
    chat_endpoint_ok: bool
    error: str | None


class ReleaseEvidenceResponse(BaseModel):
    """JSON-serialisable evidence record."""

    run_id: str
    teacher_id_hash: str
    status: str
    event_sequence: list[dict]
    artifact_ids: list[str]
    snapshot_ids: list[str]
    export_files: list[str]
    trace_ids: list[str]
    provider_evidence: list[ProviderEvidenceResponse]
    total_duration_ms: int
    per_stage_duration_ms: dict[str, int]
    tokens_used: int
    cost_usd: float
    created_at: str | None
    completed_at: str | None


class ReleaseEvidenceListResponse(BaseModel):
    """Paginated list of evidence records."""

    items: list[ReleaseEvidenceResponse]
    count: int


# ── Helpers ──────────────────────────────────────────────────────────


def _to_response(e: ReleaseEvidence) -> ReleaseEvidenceResponse:
    provider_entries = [
        ProviderEvidenceResponse(**pe) if isinstance(pe, dict) else pe for pe in e.provider_evidence
    ]
    return ReleaseEvidenceResponse(
        run_id=e.run_id,
        teacher_id_hash=e.teacher_id_hash,
        status=e.status,
        event_sequence=e.event_sequence,
        artifact_ids=e.artifact_ids,
        snapshot_ids=e.snapshot_ids,
        export_files=e.export_files,
        trace_ids=e.trace_ids,
        provider_evidence=provider_entries,
        total_duration_ms=e.total_duration_ms,
        per_stage_duration_ms=e.per_stage_duration_ms,
        tokens_used=e.tokens_used,
        cost_usd=e.cost_usd,
        created_at=e.created_at.isoformat() if e.created_at else None,
        completed_at=e.completed_at.isoformat() if e.completed_at else None,
    )


def _default_provider_configs() -> list[ProviderProbeConfig]:
    """Build the default provider probe configs from env."""
    return [
        ProviderProbeConfig(
            base_url=_DEFAULT_PROVIDER_BASE_URL,
            model=_DEFAULT_PROVIDER_MODEL,
        ),
    ]


def _with_provider_evidence(
    evidence: ReleaseEvidence,
    provider_entries: list[ProviderEvidenceEntry],
) -> ReleaseEvidence:
    """Return a new ReleaseEvidence with provider_evidence populated.

    Since ReleaseEvidence is frozen, we construct a new instance.
    """
    return ReleaseEvidence(
        run_id=evidence.run_id,
        teacher_id_hash=evidence.teacher_id_hash,
        status=evidence.status,
        event_sequence=evidence.event_sequence,
        artifact_ids=evidence.artifact_ids,
        snapshot_ids=evidence.snapshot_ids,
        export_files=evidence.export_files,
        trace_ids=evidence.trace_ids,
        provider_evidence=[pe.to_dict() for pe in provider_entries],
        total_duration_ms=evidence.total_duration_ms,
        per_stage_duration_ms=evidence.per_stage_duration_ms,
        tokens_used=evidence.tokens_used,
        cost_usd=evidence.cost_usd,
        created_at=evidence.created_at,
        completed_at=evidence.completed_at,
    )


# ── Endpoints ────────────────────────────────────────────────────────


@router.get(
    "/run/{run_id}/evidence",
    response_model=ReleaseEvidenceResponse,
)
async def get_run_evidence(
    run_id: str,
    current_user: Annotated[User, Depends(require_teacher)],
    session=PIPELINE_V2_SESSION,
) -> ReleaseEvidenceResponse:
    """Get release evidence for a specific run.

    Teachers can only see evidence for runs they own.
    Admins can see any run's evidence.
    """
    # Check for cached evidence first
    cached = await get_evidence(run_id, session)
    if cached is not None:
        return _to_response(cached)

    # Generate fresh evidence from DB (no live provider probe on GET)
    try:
        evidence = await generate_evidence(RunId(run_id), session)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="run_not_found",
        ) from exc

    return _to_response(evidence)


@router.post(
    "/run/{run_id}/evidence",
    response_model=ReleaseEvidenceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_and_save_evidence(
    run_id: str,
    current_user: Annotated[User, Depends(require_admin)],
    session=PIPELINE_V2_SESSION,
) -> ReleaseEvidenceResponse:
    """Generate and persist release evidence for a run (admin only).

    Collects live 9Router provider evidence during generation.
    If the provider is unreachable, status is recorded as "blocked" —
    never faked as "pass".  No paid fallbacks are attempted.
    """
    try:
        evidence = await generate_evidence(RunId(run_id), session)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="run_not_found",
        ) from exc

    provider_entries = await collect_provider_evidence(_default_provider_configs())
    evidence = _with_provider_evidence(evidence, provider_entries)

    await save_evidence(evidence, session)
    write_evidence_report(evidence, EVIDENCE_REPORT_DIR)
    await session.commit()
    return _to_response(evidence)


@router.get(
    "/release-evidence",
    response_model=ReleaseEvidenceListResponse,
)
async def list_release_evidence(
    current_user: Annotated[User, Depends(require_admin)],
    session=PIPELINE_V2_SESSION,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> ReleaseEvidenceListResponse:
    """List recent release evidence records (admin only)."""
    items = await list_evidence(session, limit=limit)
    return ReleaseEvidenceListResponse(
        items=[_to_response(e) for e in items],
        count=len(items),
    )
