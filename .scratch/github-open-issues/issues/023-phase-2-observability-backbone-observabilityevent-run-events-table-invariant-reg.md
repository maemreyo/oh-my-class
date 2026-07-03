# Issue #23: [Phase 2] Observability backbone — ObservabilityEvent, run_events table, INVARIANT_REGISTRY

Status: DONE
Source: https://github.com/maemreyo/oh-my-class/issues/23
State: OPEN
Created: 2026-07-02T16:42:36Z
Updated: 2026-07-02T16:42:36Z
Labels: enhancement, agents-refactor, phase-2
Assignees: 

## Todo

- [x] Read and understand acceptance criteria
- [x] Implement required changes
- [x] Run targeted verification available without local Postgres
- [x] Run real Postgres-backed persistence verification
- [x] Run surface/manual QA for the in-memory event bus
- [x] Update this ticket status

## Progress notes

- Added typed `ObservabilityEvent` in `packages/agents/events.py` with:
  - Pydantic model validation.
  - `Literal` event kinds for stage/gate/healing/hard-block/escalation/cost and existing run/step/LLM event names.
  - bounded `run_id`, optional `teacher_id`/`stage`, timestamp and event-id `default_factory` fields, and optional sequence bounds.
  - `legacy_dict()` compatibility for existing `/run/{id}/status` SSE consumers.
- Kept the existing `emit_run_event()` API working and added `publish_event(ObservabilityEvent)` so current LLM/event callers do not fork into a second stream.
- Added `TeachingPackRunStore.write_observability_event()` to persist typed `ObservabilityEvent` rows into the existing durable `public.run_events` table.
- Extracted the typed durable row/payload construction into `services/gateway/observability_events.py`, keeping `TeachingPackRunStore` as the public store seam without growing its responsibilities further.
- Confirmed the durable table already exists in `services/gateway/alembic/versions/002_pipeline_v2_persistence.py` and `services/gateway/teaching_pack_models.py`; no new migration was needed.
- Added a real Postgres-backed test path: `services/gateway/tests/test_teaching_pack_store.py::TestTeachingPackStore::test_observability_events_persist_to_run_events`.
- Added non-DB regression coverage in `services/gateway/tests/test_observability_events.py` for the exact `run_events` row shape produced from an `ObservabilityEvent`.
- Added `packages/agents/testing/invariant_registry.py` with `INVARIANT_REGISTRY` entries for all documented `INVARIANT-01` through `INVARIANT-10`.
- Added `tests/test_invariant_coverage.py` meta-tests that verify registry test files exist, are not skipped/xfail-marked, and cover all 10 invariant IDs.

## Verification notes

- `uv run pytest packages/agents/tests/test_events.py tests/test_invariant_coverage.py -q` → `20 passed`.
- `uv run pytest packages/agents/tests/test_events.py tests/test_invariant_coverage.py services/gateway/tests/test_teaching_pack_store.py::TestTeachingPackStore::test_observability_events_persist_to_run_events -q` → `20 passed, 1 skipped`.
- `uv run pytest services/gateway/tests/test_observability_events.py packages/agents/tests/test_events.py tests/test_invariant_coverage.py services/gateway/tests/test_teaching_pack_store.py::TestTeachingPackStore::test_observability_events_persist_to_run_events -q` → `22 passed, 1 skipped`.
- Skip reason for the real DB test: local Postgres was unavailable at `localhost:5432` (`Errno 61` on both IPv4/IPv6). Docker was also unavailable (`Cannot connect to the Docker daemon`). The test is present and will exercise real Postgres when the dependency is running.
- Started the existing Docker Compose Postgres service with `docker compose -f infra/compose/docker-compose.yml up -d db`; `docker compose ... ps db` reported `compose-db-1` healthy on `5432`.
- `uv run pytest services/gateway/tests/test_teaching_pack_store.py::TestTeachingPackStore::test_observability_events_persist_to_run_events -q` → `1 passed` against real Postgres.
- `uv run pytest services/gateway/tests/test_observability_events.py packages/agents/tests/test_events.py tests/test_invariant_coverage.py services/gateway/tests/test_teaching_pack_store.py::TestTeachingPackStore::test_observability_events_persist_to_run_events -q` → `23 passed` against real Postgres.
- Manual surface smoke: `uv run python -c '...'` published an `ObservabilityEvent` through `publish_event()` and read it back via `get_run_events()` → `observability_event_bus_ok`.
- Manual row-builder smoke: `uv run python -c '...'` built a durable event payload from `ObservabilityEvent` through `observability_event_payload()` → `observability_event_payload_ok`.
- Manual store smoke: `uv run python - <<'PY' ... PY` created a run through `TeachingPackRunStore`, wrote an `ObservabilityEvent` with `write_observability_event()`, replayed it from `run_events`, and cleaned up the row → `observability_event_store_ok`.
- Post-review remediation wired the in-memory package bus into the production worker path: `TeachingPackWorker.run_one()` / `run_claimed()` now drain `packages.agents.events` and persist typed observability events through `TeachingPackRunStore.write_observability_event()`.
- Fixed legacy-to-typed event reconstruction so flattened SSE-compatible payload fields are preserved when durable `ObservabilityEvent` rows are written.
- Added a Postgres-backed worker bridge regression: `services/gateway/tests/test_teaching_pack_worker.py::TestTeachingPackWorker::test_run_one_persists_observability_events`.
- `uv run pytest packages/agents/tests/test_events.py services/gateway/tests/test_teaching_pack_worker.py services/gateway/tests/test_teaching_pack_runs_router.py -q` → `33 passed`.
- Broader post-review focused suite including observability/worker/router/runtime/breaker/gate registry → `147 passed`.
- LSP diagnostics clean for:
  - `packages/agents/events.py`
  - `packages/agents/tests/test_events.py`
  - `packages/agents/testing/invariant_registry.py`
  - `tests/test_invariant_coverage.py`
  - `services/gateway/observability_events.py`
  - `services/gateway/tests/test_observability_events.py`
  - `services/gateway/tests/test_teaching_pack_store.py`
  - `services/gateway/tests/test_teaching_pack_worker.py`
- `services/gateway/teaching_pack_store.py` has only pre-existing SQLAlchemy event-listener hints for unaccessed listener functions.
- Python no-excuse helper referenced by the programming skill is not present at `scripts/python/check-no-excuse-rules.py`; pure LOC check for the newly created/modified focused Python files returned `231`, with each file under the 250 LOC ceiling.
- Round 3 remediation removed placeholder `event1`/`event2` observability event kinds, wired production `healing_decision` + `escalate` emits from `HealingOrchestrator`, and wired `cost_accrued` emits from successful `complete_json_chat()` calls.
- Round 3 verification: `uv run pytest packages/agents/tests/test_events.py services/gateway/tests/test_teaching_pack_worker.py services/gateway/tests/test_teaching_pack_runs_router.py -q` → `34 passed`.
- Round 3 focused backend slice: `uv run pytest packages/agents/healing/tests/test_orchestrator.py packages/agents/healing/tests/test_circuit_breaker.py packages/agents/tests/test_events.py services/gateway/tests/test_runs_router.py packages/agents/tests/teaching_pack/test_nodes.py::TestTeachingPackApprovalExport -q` → `110 passed, 1 skipped`.

## Boundary / blocker

- Resolved: the real Postgres-backed event test has now run against the local Docker Compose Postgres service and passed.

## Body

## Context

The system has no real observability backbone. There is no typed event, no durable event store, and no registry that ties invariants to tests. This blocks both ops visibility and the Phase 5 teacher live-status. Critically, ops and the teacher UI must be fed from the **same** stream — building two pipelines would guarantee they diverge.

This is a production-ready rebuild, NOT patching: `events.py` becomes a real bus, backed by a typed event and a Postgres table. High-readability, SoC, modular, testable.

## Scope

- [x] Define `ObservabilityEvent` as a Pydantic model (typed fields, `Literal` for event kinds, `Field` bounds where relevant, `default_factory` for timestamps/ids).
- [x] Turn `events.py` into a real event bus (publish/subscribe), not a stub.
- [x] Add a Postgres `run_events` table + a writer that persists every `ObservabilityEvent`.
- [x] Build `INVARIANT_REGISTRY` (one entry per invariant) and a meta-test `test_invariant_coverage.py` that fails if any registered invariant lacks a corresponding test.
- [x] Make this stream the **single** shared source for the ops dashboard AND the Phase 5 teacher live-status — do not build two pipelines.

## Acceptance

- [x] `ObservabilityEvent` model + `run_events` writer land with real DB tests (real Postgres, not mocked).
- [x] Events published on the bus are persisted to `run_events` and readable by a single downstream consumer.
- [x] `test_invariant_coverage.py` passes and fails when an invariant has no test.

## References

- ADR: `docs/adr/027-circuit-breaker-scope.md` (breaker events feed this bus)
- Verdict: `docs/reports/agents/06-testing-and-observability-strategy.md`

## Depends on

- `[Epic][Phase 2] State unification + observability backbone` (parent). Consumed by Phase 4 (breaker events) and Phase 5 (teacher live-status). See milestone `agents-hardening`.
