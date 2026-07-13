from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from services.gateway.run_event_outbox import RunEventOutboxStore
from services.gateway.teaching_pack_models import RunEventOutbox
from services.gateway.teaching_pack_types import RunId


def test_run_event_outbox_has_replay_and_dedupe_constraints() -> None:
    table = RunEventOutbox.__table__
    constraint_names = {constraint.name for constraint in table.constraints if constraint.name}
    index_names = {index.name for index in table.indexes}

    assert "uq_run_event_outbox_dedupe_key" in constraint_names
    assert "uq_run_event_outbox_run_sequence" in constraint_names
    assert "ix_run_event_outbox_claim" in index_names
    assert table.c.status.nullable is False
    assert table.c.attempts.nullable is False
    assert table.c.lease_expires_at.nullable is True
    assert table.c.published_at.nullable is True


@pytest.mark.anyio
async def test_enqueue_uses_run_sequence_as_the_idempotency_key() -> None:
    class FakeSession:
        def __init__(self) -> None:
            self.rows: list[RunEventOutbox] = []
            self.flush = AsyncMock()

        def add(self, row: RunEventOutbox) -> None:
            self.rows.append(row)

    session = FakeSession()
    await RunEventOutboxStore(session).enqueue(RunId("run-1"), 7)  # type: ignore[arg-type]

    assert len(session.rows) == 1
    row = session.rows[0]
    assert row.run_id == "run-1"
    assert row.sequence == 7
    assert row.dedupe_key == "run-1:7"
    assert row.status == "pending"
    assert row.attempts == 0
    session.flush.assert_awaited_once()
