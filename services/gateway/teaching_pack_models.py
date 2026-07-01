from __future__ import annotations

from datetime import datetime  # noqa: TC003
from enum import StrEnum

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from services.gateway.models import Base, RunStatus, utc_now
from services.gateway.teaching_pack_artifact_models import (  # noqa: F401
    ArtifactCheckStatus,
    ArtifactWorkflow,
    ArtifactWorkflowStatus,
)
from services.gateway.teaching_pack_snapshot_models import ArtifactSnapshot  # noqa: F401
from services.gateway.vocabulary_cluster_models import (  # noqa: F401
    VocabularyClusterEvidenceModel,
    VocabularyClusterEvidenceType,
    VocabularyClusterReviewStatus,
    VocabularyClusterWorkflowModel,
    VocabularyClusterWorkflowStatus,
)

type OrmJsonValue = str | int | float | bool | None | list[OrmJsonValue] | dict[str, OrmJsonValue]
type OrmJsonObject = dict[str, OrmJsonValue]


def _enum_values(enum_class):
    return [member.value for member in enum_class]

__all__ = [
    "ArtifactCheckStatus",
    "ArtifactSnapshot",
    "ArtifactWorkflow",
    "ArtifactWorkflowStatus",
    "ContractRevision",
    "GateInterrupt",
    "GateInterruptStatus",
    "GateResponse",
    "OrmJsonObject",
    "OrmJsonValue",
    "TeachingPackEventVisibility",
    "RunContract",
    "RunEvent",
    "RunJob",
    "RunJobKind",
    "RunJobStatus",
    "RunStatusHistory",
    "VocabularyClusterEvidenceModel",
    "VocabularyClusterEvidenceType",
    "VocabularyClusterReviewStatus",
    "VocabularyClusterWorkflowModel",
    "VocabularyClusterWorkflowStatus",
]


class TeachingPackEventVisibility(StrEnum):
    TEACHER = "teacher"
    ADMIN = "admin"
    INTERNAL = "internal"


class GateInterruptStatus(StrEnum):
    ACTIVE = "active"
    RESPONDED = "responded"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class RunJobStatus(StrEnum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RunJobKind(StrEnum):
    START = "start"
    RESUME = "resume"


class RunStatusHistory(Base):
    __tablename__ = "run_status_history"
    __table_args__ = (
        Index("ix_run_status_history_run_id", "run_id"),
        {"schema": "public"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("public.runs.run_id", ondelete="CASCADE"), nullable=False,
    )
    status: Mapped[RunStatus] = mapped_column(Enum(RunStatus, native_enum=False), nullable=False)
    stage: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class RunContract(Base):
    __tablename__ = "run_contracts"
    __table_args__ = (
        UniqueConstraint("run_id", name="uq_run_contracts_run_id"),
        {"schema": "public"},
    )

    contract_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("public.runs.run_id", ondelete="CASCADE"), nullable=False,
    )
    teacher_id: Mapped[str] = mapped_column(String(64), nullable=False)
    contract_json: Mapped[OrmJsonObject] = mapped_column(JSON, nullable=False)
    current_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now,
    )


class ContractRevision(Base):
    __tablename__ = "contract_revisions"
    __table_args__ = (
        UniqueConstraint("contract_id", "revision", name="uq_contract_revisions_revision"),
        Index("ix_contract_revisions_run_id", "run_id"),
        {"schema": "public"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    contract_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("public.run_contracts.contract_id", ondelete="CASCADE"),
        nullable=False,
    )
    run_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("public.runs.run_id", ondelete="CASCADE"), nullable=False,
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    contract_json: Mapped[OrmJsonObject] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class GateInterrupt(Base):
    __tablename__ = "gate_interrupts"
    __table_args__ = (
        Index(
            "uq_gate_interrupts_active",
            "run_id",
            "gate_name",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
        Index("ix_gate_interrupts_run_id", "run_id"),
        {"schema": "public"},
    )

    gate_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("public.runs.run_id", ondelete="CASCADE"), nullable=False,
    )
    gate_name: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[GateInterruptStatus] = mapped_column(
        Enum(GateInterruptStatus, native_enum=False, values_callable=_enum_values), nullable=False,
    )
    payload: Mapped[OrmJsonObject] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class GateResponse(Base):
    __tablename__ = "gate_responses"
    __table_args__ = (
        UniqueConstraint("gate_id", name="uq_gate_responses_gate_id"),
        Index("ix_gate_responses_run_id", "run_id"),
        {"schema": "public"},
    )

    response_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    gate_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("public.gate_interrupts.gate_id", ondelete="CASCADE"),
        nullable=False,
    )
    run_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("public.runs.run_id", ondelete="CASCADE"), nullable=False,
    )
    teacher_id: Mapped[str] = mapped_column(String(64), nullable=False)
    response_json: Mapped[OrmJsonObject] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class RunEvent(Base):
    __tablename__ = "run_events"
    __table_args__ = (
        UniqueConstraint("run_id", "sequence", name="uq_run_events_run_sequence"),
        Index("ix_run_events_run_id_sequence", "run_id", "sequence"),
        Index("ix_run_events_run_id_visibility", "run_id", "visibility"),
        {"schema": "public"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("public.runs.run_id", ondelete="CASCADE"), nullable=False,
    )
    sequence: Mapped[int] = mapped_column(BigInteger, nullable=False)
    event_name: Mapped[str] = mapped_column(String(128), nullable=False)
    stage: Mapped[str | None] = mapped_column(String(64), nullable=True)
    visibility: Mapped[TeachingPackEventVisibility] = mapped_column(
        Enum(TeachingPackEventVisibility, native_enum=False), nullable=False,
    )
    payload: Mapped[OrmJsonObject | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class RunJob(Base):
    __tablename__ = "run_jobs"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_run_jobs_idempotency_key"),
        Index("ix_run_jobs_status_created_at", "status", "created_at"),
        Index("ix_run_jobs_run_id", "run_id"),
        Index("ix_run_jobs_status_eligible_at", "status", "eligible_at"),
        {"schema": "public"},
    )

    job_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("public.runs.run_id", ondelete="CASCADE"), nullable=False,
    )
    kind: Mapped[RunJobKind] = mapped_column(
        Enum(RunJobKind, native_enum=False, values_callable=_enum_values), nullable=False,
    )
    status: Mapped[RunJobStatus] = mapped_column(
        Enum(RunJobStatus, native_enum=False, values_callable=_enum_values), nullable=False,
    )
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    payload: Mapped[OrmJsonObject] = mapped_column(JSON, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    eligible_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    lease_owner: Mapped[str | None] = mapped_column(String(128), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now,
    )
