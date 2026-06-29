"""Release evidence — deterministic audit record for a completed pipeline run.

Captures the full lifecycle of a run for production-readiness evidence,
compliance auditing, and release gating.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime  # noqa: TC003 - SQLAlchemy evaluates mapped annotations
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from services.gateway.identity_hash import hash_teacher_id
from services.gateway.models import Base, utc_now

if TYPE_CHECKING:
    from pathlib import Path

    from sqlalchemy.ext.asyncio import AsyncSession


# ── SQLAlchemy model ─────────────────────────────────────────────────


class ReleaseEvidenceRecord(Base):
    """Persisted release evidence row."""

    __tablename__ = "release_evidence"
    __table_args__ = {"schema": "public"}

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    teacher_id_hash: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    event_sequence: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    artifact_ids: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    snapshot_ids: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    export_files: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    trace_ids: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    total_duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    per_stage_duration_ms: Mapped[dict[str, int] | None] = mapped_column(JSON, nullable=True)
    provider_evidence: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# ── Dataclass (in-memory representation) ─────────────────────────────


@dataclass(frozen=True, slots=True)
class ReleaseEvidence:
    """Compact audit record for a completed pipeline run."""

    run_id: str
    teacher_id_hash: str
    status: str
    event_sequence: list[dict] = field(default_factory=list)
    artifact_ids: list[str] = field(default_factory=list)
    snapshot_ids: list[str] = field(default_factory=list)
    export_files: list[str] = field(default_factory=list)
    trace_ids: list[str] = field(default_factory=list)
    total_duration_ms: int = 0
    per_stage_duration_ms: dict[str, int] = field(default_factory=dict)
    provider_evidence: list[dict] = field(default_factory=list)
    tokens_used: int = 0
    cost_usd: float = 0.0
    created_at: datetime | None = None
    completed_at: datetime | None = None

    def to_db_record(self) -> ReleaseEvidenceRecord:
        """Convert to SQLAlchemy model for persistence."""
        return ReleaseEvidenceRecord(
            run_id=self.run_id,
            teacher_id_hash=self.teacher_id_hash,
            status=self.status,
            event_sequence=self.event_sequence or None,
            artifact_ids=self.artifact_ids or None,
            snapshot_ids=self.snapshot_ids or None,
            export_files=self.export_files or None,
            trace_ids=self.trace_ids or None,
            provider_evidence=self.provider_evidence or None,
            total_duration_ms=self.total_duration_ms,
            per_stage_duration_ms=self.per_stage_duration_ms or None,
            tokens_used=self.tokens_used,
            cost_usd=self.cost_usd,
            created_at=self.created_at,
            completed_at=self.completed_at,
        )

    @classmethod
    def from_db_record(cls, record: ReleaseEvidenceRecord) -> ReleaseEvidence:
        """Reconstruct from SQLAlchemy model."""
        return cls(
            run_id=record.run_id,
            teacher_id_hash=record.teacher_id_hash,
            status=record.status,
            event_sequence=record.event_sequence or [],
            artifact_ids=record.artifact_ids or [],
            snapshot_ids=record.snapshot_ids or [],
            export_files=record.export_files or [],
            trace_ids=record.trace_ids or [],
            provider_evidence=record.provider_evidence or [],
            total_duration_ms=record.total_duration_ms,
            per_stage_duration_ms=record.per_stage_duration_ms or {},
            tokens_used=record.tokens_used,
            cost_usd=record.cost_usd,
            created_at=record.created_at,
            completed_at=record.completed_at,
        )


# ── Evidence generation ──────────────────────────────────────────────

if TYPE_CHECKING:
    from services.gateway.teaching_pack_types import RunId


async def generate_evidence(run_id: RunId, db: AsyncSession) -> ReleaseEvidence:
    """Build a ReleaseEvidence record from live database state.

    Queries the run, events, snapshots, and artifacts tables to construct
    a compact evidence record.  Teacher IDs are hashed for privacy.
    """
    from sqlalchemy import select

    from services.gateway.models import Artifact, Run
    from services.gateway.teaching_pack_models import ArtifactSnapshot, RunEvent

    # ── Run ──────────────────────────────────────────────────────────
    run_result = await db.execute(select(Run).where(Run.run_id == run_id))
    run = run_result.scalar_one_or_none()
    if run is None:
        raise ValueError(f"Run {run_id} not found")

    teacher_hash = hash_teacher_id(run.teacher_id)

    # ── Events (compact) ─────────────────────────────────────────────
    events_result = await db.execute(
        select(RunEvent).where(RunEvent.run_id == run_id).order_by(RunEvent.sequence)
    )
    events = events_result.scalars().all()
    event_sequence = [
        {
            "sequence": e.sequence,
            "event_name": e.event_name,
            "stage": e.stage,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in events
    ]
    export_files = _export_files_from_events(events)

    # ── Snapshots ────────────────────────────────────────────────────
    snapshots_result = await db.execute(
        select(ArtifactSnapshot.snapshot_id)
        .where(ArtifactSnapshot.run_id == run_id)
        .order_by(ArtifactSnapshot.created_at)
    )
    snapshot_ids = [row[0] for row in snapshots_result.all()]

    # ── Artifacts ────────────────────────────────────────────────────
    artifacts_result = await db.execute(
        select(Artifact.artifact_id).where(Artifact.run_id == run_id).order_by(Artifact.created_at)
    )
    artifact_ids = [row[0] for row in artifacts_result.all()]

    # ── Duration computation ─────────────────────────────────────────
    total_duration_ms = 0
    per_stage: dict[str, int] = {}
    if run.created_at and run.updated_at:
        total_duration_ms = int((run.updated_at - run.created_at).total_seconds() * 1000)

    # Compute per-stage durations from event pairs
    stage_starts: dict[str, datetime] = {}
    for event in events:
        if event.created_at is None:
            continue
        if event.event_name.endswith(".started") and event.stage:
            stage_starts[event.stage] = event.created_at
        elif event.event_name.endswith(".completed") and event.stage:
            start = stage_starts.get(event.stage)
            if start is not None:
                duration = int((event.created_at - start).total_seconds() * 1000)
                per_stage[event.stage] = duration

    return ReleaseEvidence(
        run_id=run.run_id,
        teacher_id_hash=teacher_hash,
        status=run.status.value if hasattr(run.status, "value") else str(run.status),
        event_sequence=event_sequence,
        artifact_ids=artifact_ids,
        snapshot_ids=snapshot_ids,
        export_files=export_files,
        trace_ids=[],  # populated by Langfuse integration if enabled
        total_duration_ms=total_duration_ms,
        per_stage_duration_ms=per_stage,
        tokens_used=run.tokens_used,
        cost_usd=run.cost_usd,
        created_at=run.created_at,
        completed_at=run.updated_at if run.status.value == "completed" else None,
    )


def _export_files_from_events(events) -> list[str]:
    exported: list[str] = []
    for event in events:
        if event.event_name != "teaching_pack.run.completed" or not isinstance(event.payload, dict):
            continue
        values = event.payload.get("exported_files")
        if isinstance(values, list):
            exported.extend(str(value) for value in values if isinstance(value, str))
    return list(dict.fromkeys(exported))


def render_evidence_markdown(evidence: ReleaseEvidence) -> str:
    event_lines = [
        f"- {event.get('sequence')}: {event.get('event_name')} ({event.get('stage') or 'run'})"
        for event in evidence.event_sequence
    ]

    provider_lines: list[str] = []
    if evidence.provider_evidence:
        provider_lines.append("")
        provider_lines.append("## Provider evidence (9Router)")
        for pe in evidence.provider_evidence:
            status = pe.get("status", "unknown")
            base_url = pe.get("base_url", "unknown")
            model = pe.get("model", "unknown")
            ts = pe.get("timestamp", "unknown")
            error = pe.get("error")
            line = f"- [{status.upper()}] {base_url} model={model} at {ts}"
            if error:
                line += f" — {error}"
            provider_lines.append(line)

    return "\n".join(
        (
            f"# Teaching Pack Release Evidence — {evidence.run_id}",
            "",
            f"- Status: {evidence.status}",
            f"- Teacher hash: {evidence.teacher_id_hash}",
            f"- Tokens used: {evidence.tokens_used}",
            f"- Cost USD: {evidence.cost_usd:.4f}",
            f"- Total duration ms: {evidence.total_duration_ms}",
            f"- Artifacts: {', '.join(evidence.artifact_ids) or 'none'}",
            f"- Snapshots: {', '.join(evidence.snapshot_ids) or 'none'}",
            f"- Exports: {', '.join(evidence.export_files) or 'none'}",
            "",
            "## Event sequence",
            *(event_lines or ["- none"]),
            *provider_lines,
            "",
        )
    )


def write_evidence_report(evidence: ReleaseEvidence, directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    report_path = directory / f"teaching-pack-run-evidence-{evidence.run_id}.md"
    report_path.write_text(render_evidence_markdown(evidence), encoding="utf-8")
    return report_path
