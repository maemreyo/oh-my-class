"""UnitOrchestrator — pure decide() logic and I/O reactor for td-010.

The orchestrator drives session fan-out for a UNIT_PARENT run.  It is
deliberately split into two layers:

* ``decide()`` — pure function; builds the prerequisite DAG with networkx
  and returns a list of ``SessionAction`` objects describing what must happen.
* ``UnitOrchestrator.react()`` — I/O layer; loads state from the DB, calls
  ``decide()``, and executes SPAWN actions (creates child row + enqueues START
  job + fires event-bus notification).
* ``reconcile_units()`` — sweep helper called by the background sweeper; runs
  ``react()`` for every live UNIT_PARENT run.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import uuid4

import networkx as nx

from common.contracts.lesson_sequence import LessonSequence
from services.gateway.models import RunStatus, UnitRole
from services.gateway.teaching_pack_types import JsonObject, RunId
from services.gateway.unit_run_store import UnitSessionRunCreate, UnitSessionRunRead

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from services.gateway.teaching_pack_job_store import TeachingPackJobStore
    from services.gateway.unit_run_store import UnitRunStore


# ---------------------------------------------------------------------------
# Value types
# ---------------------------------------------------------------------------


class OrchestratorAction(StrEnum):
    SPAWN = "spawn"
    BLOCK = "block"
    MARK_PARTIALLY_COMPLETE = "mark_partially_complete"
    MARK_COMPLETE = "mark_complete"


@dataclass(frozen=True, slots=True)
class SessionAction:
    session_id: str
    action: OrchestratorAction
    reason: str


# ---------------------------------------------------------------------------
# Terminal / non-terminal status helpers
# ---------------------------------------------------------------------------

_COMPLETED_STATUS: frozenset[RunStatus] = frozenset({RunStatus.COMPLETED})
_FAILED_STATUS: frozenset[RunStatus] = frozenset({RunStatus.FAILED, RunStatus.CANCELLED})
_ACTIVE_STATUSES: frozenset[RunStatus] = frozenset({
    RunStatus.PENDING,
    RunStatus.PLANNING,
    RunStatus.RESEARCHING,
    RunStatus.GENERATING,
    RunStatus.REVIEWING,
    RunStatus.AWAITING_APPROVAL,
    RunStatus.EXPORTING,
})


def _is_completed(status: RunStatus) -> bool:
    return status in _COMPLETED_STATUS


def _is_failed(status: RunStatus) -> bool:
    return status in _FAILED_STATUS


# ---------------------------------------------------------------------------
# Pure decide() — no I/O
# ---------------------------------------------------------------------------


def decide(
    sequence: LessonSequence,
    children_states: dict[str, RunStatus],
    unit_fanout_concurrency: int = 1,
) -> list[SessionAction]:
    """Return the list of actions the orchestrator must take right now.

    Parameters
    ----------
    sequence:
        The fully-validated ``LessonSequence`` stored on the parent run.
    children_states:
        Mapping of ``session_id`` → current ``RunStatus`` for every child row
        that already exists in the DB.  Sessions not present in this dict have
        not been spawned yet.
    unit_fanout_concurrency:
        Maximum number of new sessions that may be spawned in a single
        ``react()`` call.  Defaults to 1 (serial fan-out).

    Returns
    -------
    list[SessionAction]
        SPAWN / BLOCK for individual sessions, and optionally a single
        MARK_COMPLETE or MARK_PARTIALLY_COMPLETE at the end.
    """
    # Build a mapping keyed by session_id for quick look-up.
    session_map: dict[str, object] = {s.session_id: s for s in sequence.sessions}

    # Build the prerequisite DAG using networkx.
    dag: nx.DiGraph = nx.DiGraph()
    for session in sequence.sessions:
        dag.add_node(session.session_id)
        for prereq_id in session.prerequisite_sessions:
            dag.add_edge(prereq_id, session.session_id)

    actions: list[SessionAction] = []
    spawn_slots: int = unit_fanout_concurrency

    for session in sequence.sessions:
        sid = session.session_id

        # Already spawned — skip.
        if sid in children_states:
            continue

        # Check prerequisites.
        prereqs: list[str] = list(dag.predecessors(sid))

        # If any prerequisite has failed → BLOCK this session.
        failed_prereq = next(
            (
                p
                for p in prereqs
                if p in children_states and _is_failed(children_states[p])
            ),
            None,
        )
        if failed_prereq is not None:
            actions.append(SessionAction(
                session_id=sid,
                action=OrchestratorAction.BLOCK,
                reason=f"prerequisite {failed_prereq} failed",
            ))
            continue

        # All prerequisites must be COMPLETED before we can SPAWN.
        all_prereqs_done = all(
            p in children_states and _is_completed(children_states[p])
            for p in prereqs
        )
        if not all_prereqs_done:
            # Not ready yet — do nothing for this session.
            continue

        # Ready to spawn — but respect the concurrency cap.
        if spawn_slots > 0:
            actions.append(SessionAction(
                session_id=sid,
                action=OrchestratorAction.SPAWN,
                reason="prerequisites satisfied",
            ))
            spawn_slots -= 1

    # Determine overall unit lifecycle after processing individual sessions.
    all_session_ids = {s.session_id for s in sequence.sessions}

    completed_ids = {sid for sid, st in children_states.items() if _is_completed(st)}
    failed_ids = {sid for sid, st in children_states.items() if _is_failed(st)}

    # Include sessions that are about to be spawned as "accounted for".
    spawned_now = {a.session_id for a in actions if a.action is OrchestratorAction.SPAWN}
    blocked_ids = {a.session_id for a in actions if a.action is OrchestratorAction.BLOCK}

    # All sessions are completed → MARK_COMPLETE.
    if all_session_ids == completed_ids:
        actions.append(SessionAction(
            session_id="",
            action=OrchestratorAction.MARK_COMPLETE,
            reason="all sessions completed",
        ))
        return actions

    # Some sessions failed AND no sessions are active/spawnable → MARK_PARTIALLY_COMPLETE.
    # Condition: no pending spawns AND no active children AND at least one completed.
    active_ids = {sid for sid, st in children_states.items() if st in _ACTIVE_STATUSES}
    if (
        failed_ids
        and not spawned_now
        and not active_ids
        and completed_ids
    ):
        actions.append(SessionAction(
            session_id="",
            action=OrchestratorAction.MARK_PARTIALLY_COMPLETE,
            reason="some sessions failed, no active or spawnable sessions remain",
        ))

    return actions


# ---------------------------------------------------------------------------
# I/O reactor
# ---------------------------------------------------------------------------


class UnitOrchestrator:
    """Drives fan-out for a single UNIT_PARENT run.

    Parameters
    ----------
    session:
        The active ``AsyncSession`` for this request / sweep tick.
    unit_run_store:
        A ``UnitRunStore`` instance bound to ``session``.
    job_store:
        A ``TeachingPackJobStore`` instance bound to ``session``.
    session_factory:
        Optional callable that produces a fresh ``AsyncSession``.  Reserved
        for future use (e.g. long sweeps that need independent transactions).
    """

    def __init__(
        self,
        session: AsyncSession,
        unit_run_store: UnitRunStore,
        job_store: TeachingPackJobStore,
        session_factory=None,
    ) -> None:
        self._session = session
        self._unit_run_store = unit_run_store
        self._job_store = job_store
        self._session_factory = session_factory

    async def react(self, parent_run_id: RunId) -> list[SessionAction]:
        """Run one reconciliation tick for *parent_run_id*.

        Steps:
        1. Load the ``LessonSequence`` JSON from the parent run.
        2. Load all existing child rows.
        3. Call ``decide()``.
        4. Execute SPAWN actions (create child run + enqueue START job + notify).
        5. Return the full action list.
        """
        from services.gateway.teaching_pack_event_bus import notify_run_event
        from services.gateway.teaching_pack_job_store import RunJobCreate
        from services.gateway.teaching_pack_models import RunJobKind
        from services.gateway.models import Run
        from sqlalchemy import select

        # 1. Load lesson sequence.
        seq_json: JsonObject | None = await self._unit_run_store.get_lesson_sequence(parent_run_id)
        if seq_json is None:
            return []

        sequence = LessonSequence.model_validate(seq_json)

        # 2. Load existing children.
        children: list[UnitSessionRunRead] = await self._unit_run_store.list_children(parent_run_id)
        children_states: dict[str, RunStatus] = {
            child.session_id: child.status
            for child in children
            if child.session_id
        }

        # 3. Build a session_map for index look-up.
        session_map = {s.session_id: s for s in sequence.sessions}

        # 4. Decide.
        actions = decide(sequence, children_states, unit_fanout_concurrency=1)

        # 5. Retrieve parent metadata once for SPAWN actions.
        parent_run_result = await self._session.execute(
            select(Run).where(Run.run_id == parent_run_id)
        )
        parent_run = parent_run_result.scalar_one_or_none()
        if parent_run is None:
            return actions

        # 6. Execute SPAWN actions.
        for action in actions:
            if action.action is not OrchestratorAction.SPAWN:
                continue

            session_plan = session_map.get(action.session_id)
            if session_plan is None:
                continue

            child_run_id = RunId(str(uuid4()))
            payload = UnitSessionRunCreate(
                run_id=child_run_id,
                parent_run_id=parent_run_id,
                teacher_id=parent_run.teacher_id,
                session_id=action.session_id,
                session_index=session_plan.order_index,
                raw_request=parent_run.raw_request,
                class_info=parent_run.class_info or {},
                retention_days=parent_run.retention_days,
            )

            # create_child_run uses flush() + unique constraint — idempotent.
            await self._unit_run_store.create_child_run(payload)

            # Enqueue a START job for the child run.
            job_id = str(uuid4())
            idempotency_key = f"unit-session-start:{parent_run_id}:{action.session_id}"
            await self._job_store.enqueue(RunJobCreate(
                job_id=job_id,
                run_id=child_run_id,
                kind=RunJobKind.START,
                idempotency_key=idempotency_key,
                payload={"run_id": child_run_id},
            ))

            # Notify the event bus so SSE subscribers wake up.
            notify_run_event(parent_run_id)
            notify_run_event(child_run_id)

        return actions


# ---------------------------------------------------------------------------
# Sweep entry-point
# ---------------------------------------------------------------------------


async def reconcile_units(session: AsyncSession) -> None:
    """Advance every live UNIT_PARENT run by one orchestration tick.

    Called from the background sweeper.  Creates one ``UnitOrchestrator``
    per live parent run and calls ``react()``.  All mutations are flushed to
    the same ``session``; the caller is responsible for commit / rollback.
    """
    from sqlalchemy import select

    from services.gateway.models import Run
    from services.gateway.teaching_pack_job_store import TeachingPackJobStore
    from services.gateway.unit_run_store import UnitRunStore

    _TERMINAL = {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED}

    statement = select(Run).where(
        Run.unit_role == UnitRole.UNIT_PARENT,
        Run.status.not_in([s.value for s in _TERMINAL]),
    )
    result = await session.execute(statement)
    parent_runs = result.scalars().all()

    for parent_run in parent_runs:
        unit_run_store = UnitRunStore(session)
        job_store = TeachingPackJobStore(session)
        orchestrator = UnitOrchestrator(
            session=session,
            unit_run_store=unit_run_store,
            job_store=job_store,
        )
        await orchestrator.react(RunId(parent_run.run_id))
