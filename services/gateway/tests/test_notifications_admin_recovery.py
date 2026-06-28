"""Tests for notification system and admin recovery actions.

Tests follow the same pattern as test_teaching_pack_worker.py:
async tests against a real PostgreSQL via asyncpg, with cleanup.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from services.gateway.admin_recovery import (
    AdminRecoveryRequest,
    SafeRecoveryAction,
    execute_recovery,
)
from services.gateway.models import Base, Run, RunStatus
from services.gateway.notification_db import (
    Notification,
    NotificationDeliveryRecord,
)
from services.gateway.notification_models import NotificationEvent
from services.gateway.notification_store import (
    create_notification,
    deliver_notification,
    dismiss_notification,
    get_notifications,
    mark_read,
)
from services.gateway.notifications import (
    InAppNotificationChannel,
    notify_blueprint_ready,
    notify_content_preview_ready,
    notify_contract_confirmation,
    notify_gate_required,
    notify_gate_timeout_warning,
    notify_run_completed,
    notify_run_escalated,
    notify_run_failed,
    notify_search_confirmation,
)
from services.gateway.teaching_pack_models import (
    GateInterrupt,
    GateInterruptStatus,
    RunJob,
    RunJobKind,
    RunJobStatus,
    RunStatusHistory,
)
from services.gateway.teaching_pack_store import TeachingPackRunCreate, TeachingPackRunStore
from services.gateway.teaching_pack_types import RunId, TeacherId

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncSession

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        existing_tables = await connection.run_sync(
            lambda sync_connection: set(Base.metadata.tables),
        )
        if "public.notifications" not in existing_tables:
            pytest.skip("notifications table is not present")
    async with session_factory() as database_session:
        yield database_session
        await database_session.rollback()
    await engine.dispose()


# ── Helpers ─────────────────────────────────────────────────────────


async def _create_run(
    session: AsyncSession,
    teacher_id: str = "teacher-test",
) -> RunId:
    run_id = RunId(f"test-notif-{uuid4()}")
    await TeachingPackRunStore(session).create_run(TeachingPackRunCreate(
        run_id=run_id,
        teacher_id=TeacherId(teacher_id),
        raw_request="Test notification run",
        class_info={"grade": 5},
    ))
    await session.flush()
    return run_id


async def _delete_run(session: AsyncSession, run_id: RunId) -> None:
    # Delete in reverse dependency order
    await session.execute(
        delete(NotificationDeliveryRecord)
        .where(NotificationDeliveryRecord.notification_id.in_(
            select(Notification.id).where(Notification.run_id == run_id),
        ))
    )
    await session.execute(
        delete(Notification).where(Notification.run_id == run_id),
    )
    await session.execute(
        delete(RunJob).where(RunJob.run_id == run_id),
    )
    await session.execute(
        delete(RunStatusHistory).where(RunStatusHistory.run_id == run_id),
    )
    await session.execute(
        delete(GateInterrupt).where(GateInterrupt.run_id == run_id),
    )
    await session.execute(
        delete(Run).where(Run.run_id == run_id),
    )
    await session.commit()


def _make_event(
    run_id: RunId,
    teacher_id: str = "teacher-test",
    event_type: str = "run_completed",
) -> NotificationEvent:
    return NotificationEvent(
        event_id=str(uuid4()),
        run_id=run_id,
        teacher_id=teacher_id,
        event_type=event_type,  # type: ignore[arg-type]
        title=f"Test {event_type}",
        message=f"Test message for {event_type}",
        metadata={"test": True},
    )


# ── Notification creation tests ────────────────────────────────────


class TestNotificationCreation:
    async def test_create_notification_returns_id(self, session: AsyncSession) -> None:
        run_id = await _create_run(session)
        event = _make_event(run_id)

        notif_id = await create_notification(event, session)

        assert notif_id == event.event_id
        await _delete_run(session, run_id)

    async def test_create_notification_deduplicates(self, session: AsyncSession) -> None:
        run_id = await _create_run(session)
        event = _make_event(run_id)

        id1 = await create_notification(event, session)
        id2 = await create_notification(event, session)

        assert id1 == id2

        # Only one row in the database
        stmt = select(Notification).where(Notification.run_id == run_id)
        result = await session.execute(stmt)
        count = len(result.scalars().all())
        assert count == 1
        await _delete_run(session, run_id)

    async def test_different_event_types_not_deduplicated(
        self,
        session: AsyncSession,
    ) -> None:
        run_id = await _create_run(session)
        event1 = _make_event(run_id, event_type="run_completed")
        event2 = _make_event(run_id, event_type="run_failed")

        id1 = await create_notification(event1, session)
        id2 = await create_notification(event2, session)

        assert id1 != id2
        await _delete_run(session, run_id)


# ── Delivery tests ─────────────────────────────────────────────────


class TestNotificationDelivery:
    async def test_deliver_notification_returns_id(
        self,
        session: AsyncSession,
    ) -> None:
        run_id = await _create_run(session)
        event = _make_event(run_id)
        notif_id = await create_notification(event, session)

        delivery_id = await deliver_notification(notif_id, "in_app", session)

        assert delivery_id is not None
        assert "in_app" in delivery_id
        await _delete_run(session, run_id)

    async def test_deliver_notification_skips_duplicate(
        self,
        session: AsyncSession,
    ) -> None:
        run_id = await _create_run(session)
        event = _make_event(run_id)
        notif_id = await create_notification(event, session)

        d1 = await deliver_notification(notif_id, "in_app", session)
        d2 = await deliver_notification(notif_id, "in_app", session)

        assert d1 == d2

        # Only one delivery record
        stmt = select(NotificationDeliveryRecord).where(
            NotificationDeliveryRecord.notification_id == notif_id,
        )
        result = await session.execute(stmt)
        count = len(result.scalars().all())
        assert count == 1
        await _delete_run(session, run_id)

    async def test_different_channels_not_deduplicated(
        self,
        session: AsyncSession,
    ) -> None:
        run_id = await _create_run(session)
        event = _make_event(run_id)
        notif_id = await create_notification(event, session)

        d1 = await deliver_notification(notif_id, "in_app", session)
        d2 = await deliver_notification(notif_id, "email", session)

        assert d1 != d2
        await _delete_run(session, run_id)


# ── Query tests ────────────────────────────────────────────────────


class TestNotificationQuery:
    async def test_get_notifications_for_teacher(
        self,
        session: AsyncSession,
    ) -> None:
        run_id = await _create_run(session, teacher_id="teacher-alice")
        event = _make_event(run_id, teacher_id="teacher-alice")
        await create_notification(event, session)

        notifications = await get_notifications("teacher-alice", session)

        assert len(notifications) == 1
        assert notifications[0]["notification_id"] == event.event_id
        await _delete_run(session, run_id)

    async def test_get_unread_notifications_only(
        self,
        session: AsyncSession,
    ) -> None:
        run_id = await _create_run(session, teacher_id="teacher-bob")
        event = _make_event(run_id, teacher_id="teacher-bob")
        await create_notification(event, session)

        # Before read — should appear
        unread = await get_notifications("teacher-bob", session, unread_only=True)
        assert len(unread) == 1

        await mark_read(event.event_id, session)

        # After read — should not appear
        unread = await get_notifications("teacher-bob", session, unread_only=True)
        assert len(unread) == 0
        await _delete_run(session, run_id)

    async def test_cross_teacher_isolation(
        self,
        session: AsyncSession,
    ) -> None:
        run1 = await _create_run(session, teacher_id="teacher-alice")
        run2 = await _create_run(session, teacher_id="teacher-bob")
        event1 = _make_event(run1, teacher_id="teacher-alice")
        event2 = _make_event(run2, teacher_id="teacher-bob")
        await create_notification(event1, session)
        await create_notification(event2, session)

        alice_notifs = await get_notifications("teacher-alice", session)
        bob_notifs = await get_notifications("teacher-bob", session)

        assert len(alice_notifs) == 1
        assert len(bob_notifs) == 1
        assert alice_notifs[0]["teacher_id"] == "teacher-alice"
        assert bob_notifs[0]["teacher_id"] == "teacher-bob"
        await _delete_run(session, run1)
        await _delete_run(session, run2)


# ── Mark read / dismiss tests ──────────────────────────────────────


class TestNotificationActions:
    async def test_mark_read_sets_read_at(self, session: AsyncSession) -> None:
        run_id = await _create_run(session)
        event = _make_event(run_id)
        await create_notification(event, session)

        await mark_read(event.event_id, session)

        notifs = await get_notifications("teacher-test", session)
        assert notifs[0]["read_at"] is not None
        await _delete_run(session, run_id)

    async def test_mark_read_nonexistent_is_noop(
        self,
        session: AsyncSession,
    ) -> None:
        # Should not raise
        await mark_read("nonexistent-id", session)

    async def test_dismiss_sets_status(self, session: AsyncSession) -> None:
        run_id = await _create_run(session)
        event = _make_event(run_id)
        notif_id = await create_notification(event, session)
        await deliver_notification(notif_id, "in_app", session)

        await dismiss_notification(notif_id, "in_app", session)

        stmt = select(NotificationDeliveryRecord).where(
            NotificationDeliveryRecord.notification_id == notif_id,
        )
        result = await session.execute(stmt)
        delivery = result.scalar_one()
        assert delivery.status == "dismissed"
        await _delete_run(session, run_id)

    async def test_dismiss_nonexistent_is_noop(
        self,
        session: AsyncSession,
    ) -> None:
        # Should not raise
        await dismiss_notification("nonexistent", "in_app", session)


# ── In-app channel tests ───────────────────────────────────────────


class TestInAppNotificationChannel:
    async def test_channel_delivers(self, session: AsyncSession) -> None:
        run_id = await _create_run(session)
        event = _make_event(run_id)
        channel = InAppNotificationChannel()

        delivery_id = await channel.send(event, session)

        assert delivery_id is not None

        # Verify notification exists
        notifs = await get_notifications("teacher-test", session)
        assert len(notifs) == 1
        assert notifs[0]["event_type"] == "run_completed"
        await _delete_run(session, run_id)

    async def test_channel_deduplicates(self, session: AsyncSession) -> None:
        run_id = await _create_run(session)
        event = _make_event(run_id)
        channel = InAppNotificationChannel()

        d1 = await channel.send(event, session)
        d2 = await channel.send(event, session)

        # Same delivery_id (deduplicated)
        assert d1 == d2
        await _delete_run(session, run_id)


class TestNotificationHelpers:
    async def test_notify_gate_required(self, session: AsyncSession) -> None:
        run_id = await _create_run(session)

        await notify_gate_required(
            run_id, "teacher-test", "blueprint_approval", session,
        )

        notifs = await get_notifications("teacher-test", session)
        assert len(notifs) == 1
        assert notifs[0]["event_type"] == "clarification_required"
        assert "blueprint" in notifs[0]["title"].lower()
        await _delete_run(session, run_id)

    async def test_notify_run_completed(self, session: AsyncSession) -> None:
        run_id = await _create_run(session)

        await notify_run_completed(run_id, "teacher-test", session)

        notifs = await get_notifications("teacher-test", session)
        assert len(notifs) == 1
        assert notifs[0]["event_type"] == "run_completed"
        await _delete_run(session, run_id)

    async def test_notify_run_failed(self, session: AsyncSession) -> None:
        run_id = await _create_run(session)

        await notify_run_failed(
            run_id, "teacher-test", "LLM timeout", session,
        )

        notifs = await get_notifications("teacher-test", session)
        assert len(notifs) == 1
        assert notifs[0]["event_type"] == "run_failed"
        assert "LLM timeout" in notifs[0]["message"]
        await _delete_run(session, run_id)

    async def test_all_pipeline_event_helpers_emit_notifications(
        self,
        session: AsyncSession,
    ) -> None:
        run_id = await _create_run(session)

        await notify_contract_confirmation(run_id, "teacher-test", session)
        await notify_search_confirmation(run_id, "teacher-test", session)
        await notify_blueprint_ready(run_id, "teacher-test", session)
        await notify_content_preview_ready(run_id, "teacher-test", ("snap-1",), session)
        await notify_run_escalated(run_id, "teacher-test", "needs admin", session)
        await notify_gate_timeout_warning(run_id, "teacher-test", "blueprint_approval", 2, session)

        notifs = await get_notifications("teacher-test", session)
        assert {item["event_type"] for item in notifs} >= {
            "contract_confirmation",
            "search_confirmation",
            "blueprint_ready",
            "content_preview_ready",
            "run_escalated",
            "gate_timeout_warning",
        }
        await _delete_run(session, run_id)


# ── Admin recovery tests ───────────────────────────────────────────


class TestAdminRecovery:
    async def test_cancel_run(self, session: AsyncSession) -> None:
        run_id = await _create_run(session)
        request = AdminRecoveryRequest(
            run_id=run_id,
            action=SafeRecoveryAction.CANCEL_RUN,
            reason="Teacher requested cancellation",
            admin_id="admin-1",
        )

        result = await execute_recovery(request, session)

        assert result.success is True
        assert result.action_performed == "cancel_run"

        # Verify run status
        stmt = select(Run).where(Run.run_id == run_id)
        run = (await session.execute(stmt)).scalar_one()
        assert run.status == RunStatus.CANCELLED
        await _delete_run(session, run_id)

    async def test_cancel_already_completed_run(
        self,
        session: AsyncSession,
    ) -> None:
        run_id = await _create_run(session)
        # Set to completed
        stmt = select(Run).where(Run.run_id == run_id).with_for_update()
        run = (await session.execute(stmt)).scalar_one()
        run.status = RunStatus.COMPLETED
        await session.flush()

        request = AdminRecoveryRequest(
            run_id=run_id,
            action=SafeRecoveryAction.CANCEL_RUN,
            reason="Test",
            admin_id="admin-1",
        )
        result = await execute_recovery(request, session)

        assert result.success is False
        assert "already" in result.message.lower()
        await _delete_run(session, run_id)

    async def test_retry_stuck_job(self, session: AsyncSession) -> None:
        run_id = await _create_run(session)

        # Create a running job
        from services.gateway.teaching_pack_job_store import TeachingPackJobStore, RunJobCreate
        job_store = TeachingPackJobStore(session)
        job = await job_store.enqueue(RunJobCreate(
            job_id=f"job-stuck-{uuid4()}",
            run_id=run_id,
            kind=RunJobKind.START,
            idempotency_key=f"idem-stuck-{uuid4()}",
            payload={"initial_state": {}},
        ))
        # Set to running
        stmt = select(RunJob).where(RunJob.job_id == job.job_id).with_for_update()
        db_job = (await session.execute(stmt)).scalar_one()
        db_job.status = RunJobStatus.RUNNING
        await session.flush()

        request = AdminRecoveryRequest(
            run_id=run_id,
            action=SafeRecoveryAction.RETRY_STUCK_JOB,
            reason="Job stuck for 30min",
            admin_id="admin-1",
        )
        result = await execute_recovery(request, session)

        assert result.success is True
        assert job.job_id in result.message

        # Verify job is back to pending
        stmt2 = select(RunJob).where(RunJob.job_id == job.job_id)
        updated = (await session.execute(stmt2)).scalar_one()
        assert updated.status == RunJobStatus.PENDING
        await _delete_run(session, run_id)

    async def test_retry_failed_artifact(self, session: AsyncSession) -> None:
        run_id = await _create_run(session)

        from services.gateway.teaching_pack_job_store import TeachingPackJobStore, RunJobCreate
        job_store = TeachingPackJobStore(session)
        job = await job_store.enqueue(RunJobCreate(
            job_id=f"job-fail-{uuid4()}",
            run_id=run_id,
            kind=RunJobKind.RESUME,
            idempotency_key=f"idem-fail-{uuid4()}",
            payload={"response_id": "r-1", "resume_payload": {}},
        ))
        # Set to failed
        stmt = select(RunJob).where(RunJob.job_id == job.job_id).with_for_update()
        db_job = (await session.execute(stmt)).scalar_one()
        db_job.status = RunJobStatus.FAILED
        await session.flush()

        request = AdminRecoveryRequest(
            run_id=run_id,
            action=SafeRecoveryAction.RETRY_FAILED_ARTIFACT,
            reason="Retry after transient error",
            admin_id="admin-1",
        )
        result = await execute_recovery(request, session)

        assert result.success is True
        stmt2 = select(RunJob).where(RunJob.job_id == job.job_id)
        updated = (await session.execute(stmt2)).scalar_one()
        assert updated.status == RunJobStatus.PENDING
        await _delete_run(session, run_id)

    async def test_reopen_gate(self, session: AsyncSession) -> None:
        run_id = await _create_run(session)

        # Create a responded gate
        gate = GateInterrupt(
            gate_id=f"gate-{uuid4()}",
            run_id=run_id,
            gate_name="blueprint_approval",
            status=GateInterruptStatus.RESPONDED,
            payload={"gate": "blueprint_approval"},
        )
        session.add(gate)
        await session.flush()

        request = AdminRecoveryRequest(
            run_id=run_id,
            action=SafeRecoveryAction.REOPEN_GATE,
            reason="Teacher wants to edit",
            admin_id="admin-1",
        )
        result = await execute_recovery(request, session)

        assert result.success is True

        # Verify gate status
        stmt = select(GateInterrupt).where(GateInterrupt.gate_id == gate.gate_id)
        updated = (await session.execute(stmt)).scalar_one()
        assert updated.status == GateInterruptStatus.ACTIVE
        await _delete_run(session, run_id)

    async def test_mark_escalated(self, session: AsyncSession) -> None:
        run_id = await _create_run(session)

        gate = GateInterrupt(
            gate_id=f"gate-esc-{uuid4()}",
            run_id=run_id,
            gate_name="content_approval",
            status=GateInterruptStatus.ACTIVE,
            payload={"gate": "content_approval"},
        )
        session.add(gate)
        await session.flush()

        request = AdminRecoveryRequest(
            run_id=run_id,
            action=SafeRecoveryAction.MARK_ESCALATED,
            reason="Gate timed out after 24h",
            admin_id="admin-1",
        )
        result = await execute_recovery(request, session)

        assert result.success is True

        stmt = select(GateInterrupt).where(GateInterrupt.gate_id == gate.gate_id)
        updated = (await session.execute(stmt)).scalar_one()
        assert updated.status == GateInterruptStatus.EXPIRED
        await _delete_run(session, run_id)

    async def test_recovery_emits_audit_event(
        self,
        session: AsyncSession,
    ) -> None:
        from services.gateway.teaching_pack_store import TeachingPackRunStore
        run_id = await _create_run(session)
        request = AdminRecoveryRequest(
            run_id=run_id,
            action=SafeRecoveryAction.CANCEL_RUN,
            reason="Audit test",
            admin_id="admin-1",
        )

        await execute_recovery(request, session)

        # Verify audit event was written
        store = TeachingPackRunStore(session)
        events = await store.replay_events(run_id)
        audit_events = [
            e for e in events
            if e.event_name.startswith("admin.recovery.")
        ]
        assert len(audit_events) == 1
        assert audit_events[0].event_name == "admin.recovery.cancel_run"
        payload = audit_events[0].payload
        assert payload is not None
        assert payload["admin_id"] == "admin-1"
        assert payload["reason"] == "Audit test"
        assert payload["success"] is True
        await _delete_run(session, run_id)

    async def test_retry_stuck_job_no_stuck_job(
        self,
        session: AsyncSession,
    ) -> None:
        run_id = await _create_run(session)
        request = AdminRecoveryRequest(
            run_id=run_id,
            action=SafeRecoveryAction.RETRY_STUCK_JOB,
            reason="No stuck job",
            admin_id="admin-1",
        )

        result = await execute_recovery(request, session)

        assert result.success is False
        assert "no stuck" in result.message.lower()
        await _delete_run(session, run_id)
