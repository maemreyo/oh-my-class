"""TSP-08: real evidence harness for TeachingSession platform behavior.

This is not a unit-test suite calling internal functions in isolation -- every
scenario below drives the *actual registered* `/teaching-sessions/*` FastAPI
routes (`services.gateway.routers.teaching_session_live.router`, the same
object `main.py` mounts) against a real Postgres and a real Redis, exactly
the way `test_teaching_session_live_router.py` proves TSP-03's live path.
TSP-08 adds the scenario-level "prove the whole platform" pass: role
isolation, idempotent submission, SSE reconnect, aggregate-default analytics,
delivery-mode declaration, offline/degraded fallback, and teacher-approval
gating for post-lesson recommendations -- then writes a redacted evidence
bundle to `.scratch/teaching-session-platform/artifacts/tsp-08-evidence.json`.

Run directly:  uv run pytest services/gateway/tests/test_teaching_session_evidence_harness.py -q
Run as the standalone harness script (same exit-code contract):
    uv run python scripts/teaching_session_evidence_harness.py

`TSP08_SIMULATE_BROKEN_ROLE_CHECK=1` intentionally breaks controller-role
gating before the router is first imported in this process -- used only by
this module's own `test_harness_catches_a_broken_role_check` meta-test (run
out-of-process via the harness script) to prove the harness is a real gate,
not a rubber stamp.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import anyio
import pytest
import redis.asyncio as redis
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from starlette.testclient import TestClient

# ---------------------------------------------------------------------------
# Optional self-sabotage, applied *before* the router is first imported in
# this process (see module docstring). Must stay above every
# `services.gateway.routers.teaching_session_live` / `session_auth` import.
# ---------------------------------------------------------------------------
if os.environ.get("TSP08_SIMULATE_BROKEN_ROLE_CHECK"):
    from services.gateway.teaching_session import session_auth as _session_auth

    async def _always_allow(
        claims: Any = None,  # noqa: ANN401 -- deliberately loose, this is a fault injection shim
    ) -> Any:
        return claims

    # Route decoration in teaching_session_live.py does
    # `from ...session_auth import require_controller` -- patching the
    # *source* module's attribute before that import statement first runs
    # makes the router bind this always-allow stand-in instead of the real
    # controller-only gate.
    _session_auth.require_controller = _session_auth.get_session_claims

from services.gateway.auth.models import Role, User
from services.gateway.exceptions import AuthorizationError
from services.gateway.models import Base
from services.gateway.routers.teaching_session_live import router
from services.gateway.teaching_pack_db import get_teaching_pack_session
from services.gateway.teaching_session import live_sync, service
from services.gateway.teaching_session.event_log import current_state, replay_events
from services.gateway.teaching_session.models import (
    DeliveryMode,
    RetentionTier,
    SessionStatus,
    TeachingSession,
)
from services.gateway.teaching_session.recommendations import (
    RecommendationStatus,
    create_pending_recommendation,
    generate_recommendation_candidates,
)
from services.gateway.teaching_session.responses import (
    DrillDownRejected,
    class_concept_rollup,
    get_session_aggregates,
    get_session_raw_responses,
    student_drill_down,
)
from services.gateway.teaching_session.retention import describe_retention_policy
from services.gateway.teaching_session.status import SessionTransitionAccepted, validate_session_transition
from services.gateway.teaching_session.tokens import (
    SessionRole,
    SessionTokenPayload,
    mint_session_token,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    from sqlalchemy.ext.asyncio import AsyncSession

# Same env-override reasoning as test_teaching_session_live_router.py: force
# the real dev Redis published on localhost instead of the docker-network-only
# hostname `.env` resolves REDIS_URL to.
os.environ["REDIS_URL"] = "redis://:omc_redis_secret@localhost:6379"

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"
OWNER = User(user_id="teacher-evidence-harness", username="teacher-evidence-harness", role=Role.TEACHER)

EVIDENCE_DIR = Path(".scratch/teaching-session-platform/artifacts")
# The intentionally-broken meta-test run (see module docstring) still runs
# every scenario test and still reaches `test_zzz_write_evidence_bundle` for
# whatever scenarios passed before the injected fault -- redirect its output
# to a throwaway path so a deliberately-broken run never clobbers the real
# evidence bundle a clean run just produced.
EVIDENCE_PATH = (
    Path(tempfile.gettempdir()) / "tsp08-broken-run-evidence.json"
    if os.environ.get("TSP08_SIMULATE_BROKEN_ROLE_CHECK")
    else EVIDENCE_DIR / "tsp-08-evidence.json"
)

# Collected across the module's tests, written once at session end by
# `test_zzz_write_evidence_bundle` (name-sorted last so every scenario above
# has already populated it; pytest collects/runs in file order, not
# alphabetically re-sorted, but the `zzz` prefix keeps this true even if a
# future scenario is appended above without checking sort order).
_EVIDENCE: dict[str, Any] = {
    "schema": "oh-my-class.teaching_session.evidence.v1",
    "generated_at": None,
    "scenarios": [],
}


def _fingerprint(token: str) -> str:
    """Redacted stand-in for a role token in evidence output -- never the raw JWT."""
    return hashlib.sha256(token.encode()).hexdigest()[:16]


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client() -> Iterator[TestClient]:
    anyio.run(_skip_if_schema_missing)
    app = FastAPI()
    app.include_router(router, prefix="/teaching-sessions")

    async def override_session() -> AsyncIterator[AsyncSession]:
        engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            yield session
        await engine.dispose()

    app.dependency_overrides[get_teaching_pack_session] = override_session
    with TestClient(app) as test_client:
        yield test_client


async def _skip_if_schema_missing() -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    async with engine.begin() as connection:
        existing_tables = await connection.run_sync(lambda c: set(Base.metadata.tables))
        if "public.teaching_session_events" not in existing_tables:
            pytest.skip("teaching_session_events table is not present — run alembic upgrade head")
    await engine.dispose()


async def _db_session() -> AsyncSession:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    return session_factory()


async def _create_session(
    *,
    retention_tier: RetentionTier = RetentionTier.AGGREGATE,
    class_id: str | None = None,
    delivery_mode: DeliveryMode = DeliveryMode.LIVE,
    deck_id: str = "deck-tsp08",
    snapshot_id: str = "snap-tsp08",
) -> TeachingSession:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as db:
        created = await service.create_session(
            db,
            session_id=f"tsp08-{uuid4()}",
            teacher_id=OWNER.user_id,
            deck_id=deck_id,
            snapshot_id=snapshot_id,
            retention_tier=retention_tier,
            class_id=class_id,
            delivery_mode=delivery_mode,
        )
        await db.commit()
    await engine.dispose()
    return created


async def _end_session(session_id: str) -> SessionStatus:
    """No HTTP route drives lifecycle transitions yet (TSP-01 built the model
    and transition table; no slice has wired `/start` or `/end` routes) --
    exercise the real transition-validation + persistence path directly, same
    as a future route would call it. A session is created `scheduled`
    (TSP-01 AC1's default), so ending it for real means walking the actual
    `scheduled -> live -> ended` chain, not skipping straight to terminal."""
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as db:
        session = await db.get(TeachingSession, session_id)
        assert session is not None

        start_result = validate_session_transition(session.status, SessionStatus.LIVE)
        assert isinstance(start_result, SessionTransitionAccepted)
        session.status = SessionStatus.LIVE
        session.started_at = datetime.now(UTC)
        await db.flush()

        end_result = validate_session_transition(session.status, SessionStatus.ENDED)
        assert isinstance(end_result, SessionTransitionAccepted)
        session.status = SessionStatus.ENDED
        session.ended_at = datetime.now(UTC)
        await db.commit()
        final_status = session.status
    await engine.dispose()
    return final_status


class BrokenRedisClient:
    """Every call raises a connection error -- simulates Redis being down
    (mirrors test_teaching_session_live_sync.py's BrokenRedisClient)."""

    async def publish(self, *_args: object, **_kwargs: object) -> None:
        raise redis.ConnectionError("simulated outage")

    async def get(self, *_args: object, **_kwargs: object) -> None:
        raise redis.ConnectionError("simulated outage")

    async def set(self, *_args: object, **_kwargs: object) -> None:
        raise redis.ConnectionError("simulated outage")

    def pubsub(self) -> BrokenPubSubClient:
        return BrokenPubSubClient()


class BrokenPubSubClient:
    async def subscribe(self, *_args: object, **_kwargs: object) -> None:
        raise redis.ConnectionError("simulated outage")


# ---------------------------------------------------------------------------
# Scenario 1: live classroom -- role isolation, idempotency, branch gating,
# aggregate-default analytics, teacher-approval-gated recommendations,
# SSE reconnect, and final lifecycle state.
# ---------------------------------------------------------------------------


class TestLiveClassroomScenario:
    def test_full_live_classroom_flow(self, client: TestClient) -> None:
        session = anyio.run(_create_session)
        tokens = {
            role: mint_session_token(
                session,
                role=role,
                minted_by=OWNER if role in {SessionRole.CONTROLLER, SessionRole.DISPLAY, SessionRole.OBSERVER} else None,
            )
            for role in SessionRole
        }

        # -- Controller drives the class: slide advance + branch selection --
        slide_response = client.post(
            f"/teaching-sessions/{session.session_id}/slide",
            json={"slide_id": "slide-1", "slide_index": 0},
            headers=_bearer(tokens[SessionRole.CONTROLLER]),
        )
        assert slide_response.status_code == 200
        branch_response = client.post(
            f"/teaching-sessions/{session.session_id}/branch",
            json={"slide_id": "slide-1", "branch_id": "remediation-path"},
            headers=_bearer(tokens[SessionRole.CONTROLLER]),
        )
        assert branch_response.status_code == 200
        assert branch_response.json()["current_branch_id"] == "remediation-path"

        # -- Role isolation: no non-controller role can drive slide/branch --
        non_controller_roles = [SessionRole.DISPLAY, SessionRole.STUDENT, SessionRole.OBSERVER]
        for role in non_controller_roles:
            for path, body in (
                ("slide", {"slide_id": "slide-2"}),
                ("branch", {"slide_id": "slide-1", "branch_id": "another-path"}),
            ):
                forbidden = client.post(
                    f"/teaching-sessions/{session.session_id}/{path}",
                    json=body,
                    headers=_bearer(tokens[role]),
                )
                assert forbidden.status_code == 403, (
                    f"{role.value} must not be able to POST /{path} (teacher-controlled surface)"
                )

        # -- Role isolation: only STUDENT may submit a response --
        non_student_roles = [SessionRole.CONTROLLER, SessionRole.DISPLAY, SessionRole.OBSERVER]
        for role in non_student_roles:
            forbidden = client.post(
                f"/teaching-sessions/{session.session_id}/responses",
                json={"interaction_id": "i1", "kind": "poll_vote", "payload": {"selected_option_id": "a"}},
                headers={**_bearer(tokens[role]), "Idempotency-Key": f"idem-{uuid4()}"},
            )
            assert forbidden.status_code == 403, f"{role.value} must not be able to submit a student response"

        # -- Idempotent student submission: same key submitted twice, one record --
        idempotency_key = f"idem-{uuid4()}"
        body = {
            "interaction_id": "interaction-1",
            "kind": "poll_vote",
            "payload": {"selected_option_id": "wrong"},
            "correct": False,
        }
        first = client.post(
            f"/teaching-sessions/{session.session_id}/responses",
            json=body,
            headers={**_bearer(tokens[SessionRole.STUDENT]), "Idempotency-Key": idempotency_key},
        )
        second = client.post(
            f"/teaching-sessions/{session.session_id}/responses",
            json=body,
            headers={**_bearer(tokens[SessionRole.STUDENT]), "Idempotency-Key": idempotency_key},
        )
        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json() == second.json()

        aggregates = anyio.run(_fetch_aggregates, session.session_id)
        assert len(aggregates) == 1
        assert aggregates[0].attempt_count == 1  # not 2 -- idempotency held

        # -- Aggregate-default analytics: default (aggregate) tier never
        # persists a raw per-student row, and its own drill-down is refused --
        raw_responses = anyio.run(_fetch_raw_responses, session.session_id)
        assert raw_responses == [], "aggregate tier must never persist a raw per-student response"
        drill_down = student_drill_down(raw_responses, retention_tier=session.retention_tier)
        assert isinstance(drill_down, DrillDownRejected)
        rollup = class_concept_rollup(aggregates)
        assert len(rollup) == 1
        assert rollup[0].attempt_count == 1
        assert rollup[0].incorrect_count == 1

        # -- Teacher-approval gating: a recommendation candidate is generated
        # from the class-level rollup (never raw responses), but stays PENDING
        # -- and there is no student-reachable route anywhere that returns
        # `SessionRecommendation` rows (grep-verified: only this service
        # module and its own tests reference the table) -- until a teacher
        # explicitly approves it, so it never reaches a student surface.
        candidates = generate_recommendation_candidates(rollup)
        assert candidates, "a below-threshold concept must produce at least one candidate"
        pending = anyio.run(_persist_pending_recommendation, session.session_id, candidates[0])
        assert pending.status == RecommendationStatus.PENDING.value
        assert pending.approved_at is None

        # -- SSE reconnect: disconnect after the first read, reconnect with
        # Last-Event-ID, get only what was missed (no replay of what was
        # already seen, nothing lost) --
        first_connect_events = anyio.run(_read_stream_chunks, session.session_id, tokens[SessionRole.DISPLAY], "0", 3)
        last_seen_sequence = max(e["sequence"] for e in first_connect_events)
        client.post(
            f"/teaching-sessions/{session.session_id}/slide",
            json={"slide_id": "slide-9", "slide_index": 9},
            headers=_bearer(tokens[SessionRole.CONTROLLER]),
        )
        reconnect_events = anyio.run(
            _read_stream_chunks, session.session_id, tokens[SessionRole.DISPLAY], str(last_seen_sequence), 1,
        )
        assert len(reconnect_events) == 1
        assert reconnect_events[0]["event_type"] == "slide_changed"
        assert reconnect_events[0]["slide_id"] == "slide-9"
        assert reconnect_events[0]["sequence"] > last_seen_sequence

        # -- Reconnect via GET /state also reflects the latest event --
        state_response = client.get(
            f"/teaching-sessions/{session.session_id}/state",
            headers=_bearer(tokens[SessionRole.STUDENT]),
        )
        assert state_response.status_code == 200
        assert state_response.json()["current_slide_id"] == "slide-9"

        # -- Lifecycle: end the session; final state is a real transition --
        final_status = anyio.run(_end_session, session.session_id)
        assert final_status == SessionStatus.ENDED

        _EVIDENCE["scenarios"].append({
            "name": "live_classroom",
            "session_id": session.session_id,
            "deck_id": session.deck_id,
            "snapshot_id": session.snapshot_id,
            "delivery_mode": session.delivery_mode.value,
            "retention_policy": {
                "tier": session.retention_tier.value,
                "label": describe_retention_policy(session.retention_tier).label,
            },
            "role_tokens_used": [
                {"role": role.value, "token_fingerprint": _fingerprint(token)}
                for role, token in tokens.items()
            ],
            "final_lifecycle_state": final_status.value,
            "checks": {
                "controller_drove_slide_and_branch": True,
                "non_controller_roles_blocked_from_slide_and_branch": True,
                "non_student_roles_blocked_from_responses": True,
                "idempotent_submission_single_aggregate_record": aggregates[0].attempt_count == 1,
                "raw_response_count_at_aggregate_tier": len(raw_responses),
                "drill_down_rejected_at_aggregate_tier": True,
                "recommendation_generated_but_pending_teacher_approval": True,
                "sse_reconnect_delivered_only_missed_events": True,
                "state_reconnect_reflects_latest_event": True,
            },
        })


async def _fetch_aggregates(session_id: str):
    db = await _db_session()
    async with db:
        return await get_session_aggregates(db, session_id=session_id)


async def _fetch_raw_responses(session_id: str):
    db = await _db_session()
    async with db:
        return await get_session_raw_responses(db, session_id=session_id)


async def _persist_pending_recommendation(session_id: str, candidate: Any) -> Any:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as db:
        pending = await create_pending_recommendation(db, session_id=session_id, candidate=candidate)
        await db.commit()
    await engine.dispose()
    return pending


async def _read_stream_chunks(
    session_id: str, token: str, last_event_id: str, want: int,
) -> list[dict[str, Any]]:
    """Drive the real registered `stream_session_events` route function
    (same hazard-avoidance shape as test_teaching_session_live_router.py's
    `_read_first_stream_chunk`: a real infinite SSE generator has no natural
    end for `TestClient.stream()` to hit, so this calls the route object
    FastAPI dispatches to directly and cancels once `want` events arrive)."""
    from services.gateway.routers.teaching_session_live import stream_session_events
    from services.gateway.teaching_session.tokens import verify_session_token

    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    events: list[dict[str, Any]] = []
    async with session_factory() as db:
        claims = verify_session_token(token)
        response = await stream_session_events(
            session_id, claims=claims, db=db, last_event_id=last_event_id,
        )
        async with anyio.create_task_group() as task_group:
            async def _read() -> None:
                async for chunk in response.body_iterator:
                    text = chunk.decode() if isinstance(chunk, bytes) else chunk
                    if text.startswith(":"):
                        continue  # heartbeat comment line -- not an event
                    data_line = next((line for line in text.splitlines() if line.startswith("data: ")), None)
                    if data_line is not None:
                        events.append(json.loads(data_line[len("data: "):]))
                    if len(events) >= want:
                        break
                task_group.cancel_scope.cancel()

            task_group.start_soon(_read)
    await engine.dispose()
    return events


# ---------------------------------------------------------------------------
# Scenario 2: offline/degraded presentation fallback -- Redis unreachable,
# session still functions via Postgres-only fallback (TSP-03 precedent).
# ---------------------------------------------------------------------------


class TestOfflineDegradedFallbackScenario:
    def test_session_still_functions_when_redis_is_down(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        session = anyio.run(_create_session)
        controller_token = mint_session_token(session, role=SessionRole.CONTROLLER, minted_by=OWNER)
        student_token = mint_session_token(session, role=SessionRole.STUDENT)

        monkeypatch.setattr(live_sync, "get_redis_client", lambda: BrokenRedisClient())

        slide_response = client.post(
            f"/teaching-sessions/{session.session_id}/slide",
            json={"slide_id": "slide-offline", "slide_index": 0},
            headers=_bearer(controller_token),
        )
        assert slide_response.status_code == 200, "the write path must still succeed with Redis down"
        assert slide_response.json()["current_slide_id"] == "slide-offline"

        state_response = client.get(
            f"/teaching-sessions/{session.session_id}/state", headers=_bearer(student_token),
        )
        assert state_response.status_code == 200
        assert state_response.json()["current_slide_id"] == "slide-offline", (
            "GET /state must recover the correct slide via Postgres replay, not Redis-hot state"
        )

        hot_state = anyio.run(live_sync.get_hot_state, session.session_id, BrokenRedisClient())
        assert hot_state is None, "Redis is genuinely unreachable in this scenario, not silently working"

        events = anyio.run(_replay_all, session.session_id)
        assert len(events) == 1
        assert events[0].event_type == "slide_changed"

        _EVIDENCE["scenarios"].append({
            "name": "offline_degraded_presentation_fallback",
            "session_id": session.session_id,
            "deck_id": session.deck_id,
            "snapshot_id": session.snapshot_id,
            "delivery_mode": session.delivery_mode.value,
            "retention_policy": {
                "tier": session.retention_tier.value,
                "label": describe_retention_policy(session.retention_tier).label,
            },
            "role_tokens_used": [
                {"role": SessionRole.CONTROLLER.value, "token_fingerprint": _fingerprint(controller_token)},
                {"role": SessionRole.STUDENT.value, "token_fingerprint": _fingerprint(student_token)},
            ],
            "final_lifecycle_state": session.status.value,
            "checks": {
                "write_path_succeeds_with_redis_down": True,
                "state_recovers_via_postgres_replay": True,
                "redis_hot_state_genuinely_unreachable": True,
            },
        })


async def _replay_all(session_id: str):
    db = await _db_session()
    async with db:
        return await replay_events(db, session_id, after_sequence=0)


# ---------------------------------------------------------------------------
# Scenario 3: review/homework delivery mode -- declaration-level proof.
#
# TSP-07 has, as of this harness, actually landed `DeliveryMode` (all five
# modes) plus a fail-closed `create_session` gate: only `live` is selectable
# today. That is a real, runtime-enforced behavior (not a stub), so this
# scenario proves it directly rather than treating it as unprovable.
# ---------------------------------------------------------------------------


class TestDeliveryModeDeclarationScenario:
    @pytest.mark.parametrize("mode", [DeliveryMode.HOMEWORK, DeliveryMode.REVIEW, DeliveryMode.FLIPPED, DeliveryMode.CATCH_UP])
    def test_non_live_delivery_modes_are_cleanly_rejected(self, mode: DeliveryMode) -> None:
        from services.gateway.exceptions import OMCError

        with pytest.raises(OMCError) as excinfo:
            anyio.run(partial(_create_session, delivery_mode=mode))
        assert excinfo.value.details[0]["reason"] == "delivery_mode_not_yet_supported"

    def test_live_delivery_mode_is_selectable(self, client: TestClient) -> None:
        session = anyio.run(_create_session)
        assert session.delivery_mode == DeliveryMode.LIVE

        _EVIDENCE["scenarios"].append({
            "name": "review_homework_delivery_mode_declaration",
            "session_id": session.session_id,
            "deck_id": session.deck_id,
            "snapshot_id": session.snapshot_id,
            "delivery_mode": session.delivery_mode.value,
            "retention_policy": {
                "tier": session.retention_tier.value,
                "label": describe_retention_policy(session.retention_tier).label,
            },
            "role_tokens_used": [],
            "final_lifecycle_state": session.status.value,
            "checks": {
                "live_mode_selectable": True,
                "homework_review_flipped_catch_up_cleanly_rejected": True,
                "note": (
                    "TSP-07 declares all 5 delivery modes and fail-closed-gates "
                    "the 4 async ones; only `live` has a working runtime, proven "
                    "end to end by the live_classroom scenario above."
                ),
            },
        })


# ---------------------------------------------------------------------------
# Role-scoped token minting: teacher-only roles require the session's own
# teacher; STUDENT never does (base AC/amendment #1).
# ---------------------------------------------------------------------------


class TestRoleTokenMintingIsolation:
    def test_teacher_minted_roles_require_the_owning_teacher(self, client: TestClient) -> None:
        session = anyio.run(_create_session)
        someone_else = User(user_id="not-the-owner", username="not-the-owner", role=Role.TEACHER)

        with pytest.raises(AuthorizationError):
            mint_session_token(session, role=SessionRole.CONTROLLER, minted_by=None)
        with pytest.raises(AuthorizationError):
            mint_session_token(session, role=SessionRole.DISPLAY, minted_by=someone_else)

        # STUDENT never requires a teacher -- the whole point of the
        # anonymous-first join flow.
        token = mint_session_token(session, role=SessionRole.STUDENT)
        assert token


# ---------------------------------------------------------------------------
# Evidence bundle: written once, after every scenario above has run.
# `test_` prefix (not a fixture teardown) so a failure upstream still leaves
# partial evidence on disk for debugging, and pytest's own exit code stays
# the single source of truth for "did everything pass."
# ---------------------------------------------------------------------------


def test_zzz_write_evidence_bundle() -> None:
    assert _EVIDENCE["scenarios"], "no scenario ran before the evidence bundle would be written"
    _EVIDENCE["generated_at"] = datetime.now(UTC).isoformat()
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    EVIDENCE_PATH.write_text(json.dumps(_EVIDENCE, indent=2, sort_keys=True), encoding="utf-8")
    written = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    assert written["scenarios"], "evidence bundle round-trips from disk"
    # No secrets/PII: never a raw JWT, never a student alias/pseudonym.
    serialized = json.dumps(written)
    for scenario in written["scenarios"]:
        for role_token in scenario["role_tokens_used"]:
            assert set(role_token) == {"role", "token_fingerprint"}
            assert len(role_token["token_fingerprint"]) == 16
    assert "eyJ" not in serialized, "evidence bundle must never contain a raw JWT"


# ---------------------------------------------------------------------------
# Meta-test: the harness script is a real gate, not a rubber stamp. Run
# out-of-process (spawns its own pytest subprocess) so it can prove the
# *script's* exit-code contract, not just an in-process assertion.
# ---------------------------------------------------------------------------


def test_harness_script_exits_zero_on_a_clean_run() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/teaching_session_evidence_harness.py"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_harness_script_exits_nonzero_when_a_role_check_is_broken() -> None:
    env = {**os.environ, "TSP08_SIMULATE_BROKEN_ROLE_CHECK": "1"}
    result = subprocess.run(
        [sys.executable, "scripts/teaching_session_evidence_harness.py"],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode != 0, "a broken controller-role gate must fail the harness, not pass silently"
    assert "403" in result.stdout or "assert" in result.stdout.lower()
