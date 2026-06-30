from __future__ import annotations

from uuid import uuid4

import pytest

from services.gateway.models import Run


@pytest.mark.anyio
async def test_real_db_session_round_trips_run_and_rolls_back(real_db_session) -> None:
    run_id = f"harness-{uuid4()}"
    real_db_session.add(
        Run(
            run_id=run_id,
            teacher_id="harness-teacher",
            raw_request="Harness DB isolation",
            class_info={"grade": 5},
            status="pending",
            current_step=1,
        )
    )
    await real_db_session.flush()

    stored = await real_db_session.get(Run, run_id)

    assert stored is not None
    assert stored.teacher_id == "harness-teacher"
