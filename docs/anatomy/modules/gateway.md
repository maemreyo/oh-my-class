# Module: gateway

**Path:** `services/gateway`
**Role:** FastAPI composition root that embeds the LangGraph agent runtime, manages teaching pack lifecycle (CRUD, job queue, HITL gates), handles auth/webhooks/observability, and exposes the REST + SSE API for the teacher dashboard.

## Public interface

- `app` — FastAPI application instance with lifespan, middleware chain, and 14+ routers (`main.py:200`)
- POST `/teaching-packs/runs` — `create_teaching_pack_run` — Create a new teaching pack run (202 Accepted)
- POST `/teaching-packs/runs/{run_id}/resume` — `resume_teaching_pack_run` — Resume a gated run (teacher decision)
- GET `/teaching-packs/runs/{run_id}/status` — `stream_teaching_pack_status` — SSE stream of run events
- POST `/teaching-packs/runs/{run_id}/cancel` — `cancel_teaching_pack_run` — Cancel a run
- POST `/teaching-packs/runs/{run_id}/restore` — `restore_teaching_pack_run` — Restore a soft-deleted run
- DELETE `/teaching-packs/runs/{run_id}` — `delete_teaching_pack_run` — Soft-delete a run
- POST `/teaching-packs/runs/{run_id}/artifacts/{artifact_id}/request-revision` — `request_artifact_revision` — Scoped artifact revision
- GET `/teaching-packs/runs/{run_id}/snapshots/{snapshot_id}/preview` — `preview_rendered_snapshot` — Rendered HTML preview
- POST `/teaching-packs/runs/{run_id}/approved-snapshots` — `approve_rendered_snapshots` — Approve snapshots
- PATCH `/teaching-packs/runs/{run_id}/snapshots/{snapshot_id}/blocks/{block_id}` — `edit_slide_deck_snapshot_block` — Edit slide deck block
- POST `/teaching-packs/runs/{run_id}/snapshots/{snapshot_id}/blocks/{block_id}/rewrite-suggestion` — `suggest_slide_deck_block_rewrite` — AI-assisted block rewrite
- POST `/teaching-packs/runs/{run_id}/snapshots/{snapshot_id}/translate` — `translate_slide_deck_snapshot` — Translate slide deck
- GET `/teaching-packs/runs/{run_id}/artifacts/{artifact_id}/versions` — `list_artifact_versions` — Version history
- POST `/teaching-packs/runs/{run_id}/artifacts/{artifact_id}/versions/{id}/restore` — `restore_artifact_version` — Restore previous version
- GET `/teaching-packs/runs/{run_id}/exports` — `list_exports` — Export records
- GET `/teaching-packs/runs/{run_id}/artifacts/{artifact_id}/export-status` — `get_export_status` — Staleness check
- GET `/teaching-packs/runs/{run_id}/evidence` — `get_run_evidence` — Release evidence
- GET `/teaching-packs/units/{parent_run_id}` — `get_unit_view` — Unit view with session progress
- GET `/teaching-packs/units/{parent_run_id}/status` — `stream_unit_status` — Unit SSE stream
- POST `/teaching-packs/units/{parent_run_id}/approve-all` — `approve_all_sessions` — Bulk approve
- POST `/teaching-packs/units/{parent_run_id}/sessions/{id}/spawn-anyway` — `spawn_anyway` — Force-spawn session
- POST `/teaching-packs/units/{parent_run_id}/export` — `export_unit` — Queue unit packaging
- POST `/teaching-sessions/{session_id}/slide` — `advance_slide` — Teacher advances slide
- POST `/teaching-sessions/{session_id}/branch` — `select_branch` — Teacher selects branch
- GET `/teaching-sessions/{session_id}/branches` — `get_precomputed_branches` — Precomputed branch options
- POST `/teaching-sessions/{session_id}/branch-suggestions` — `suggest_branch_content` — AI branch suggestion
- POST `/teaching-sessions/{session_id}/branch-suggestions/apply` — `apply_branch_suggestion` — Apply AI suggestion
- POST `/teaching-sessions/{session_id}/responses` — `submit_response` — Student response
- GET `/teaching-sessions/{session_id}/state` — `get_current_state` — Session state (reconnect)
- GET `/teaching-sessions/{session_id}/stream` — `stream_session_events` — SSE broadcast
- POST `/auth/login` — `login` — JWT authentication
- GET `/auth/me` — `get_me` — Current user
- GET `/health` — `health_check` — Load balancer
- GET `/ops/slo` — `get_slo_snapshot` — SLO metrics (admin)
- POST `/webhook/notify` — `send_notification` — Gate notification dispatch
- POST `/webhook/telegram` — `telegram_webhook` — Telegram bot ingress
- POST `/webhook/zalo` — `zalo_webhook` — Zalo webhook ingress
- POST `/webhook/error` — `frontend_error` — Frontend error ingestion
- POST `/media-assets` — `upload_media_asset` — Upload image/diagram
- GET `/media-assets` — `list_media_assets` — List assets
- POST `/media-assets/{id}/generate-alt-text` — `generate_media_asset_alt_text` — AI alt text
- GET `/notifications` — `list_notifications` — Teacher notifications

## Internal structure

### main.py (245 lines) — Composition Root
- Lifespan: initializes DB engine → checkpointer → store → builds `build_teaching_pack_graph()` → starts background tasks (worker + sweeper)
- Middleware: RequestID → JWT → CORS
- 14 routers registered with prefixes

### routers/ (23 files)
| Router | Prefix | Key Routes |
|--------|--------|-----------|
| `teaching_pack_runs` | `/teaching-packs` | CRUD: create, resume, request-revision, get, list |
| `teaching_pack_stream` | `/teaching-packs` | SSE: `/runs/{id}/status` |
| `teaching_pack_lifecycle` | `/teaching-packs` | cancel, soft-delete, restore |
| `teaching_pack_previews` | `/teaching-packs` | snapshot preview, block edit, AI rewrite, translate, version history |
| `unit_runs` | `/teaching-packs` | get unit view, approve-all, spawn-anyway, export |
| `exports` | `/teaching-packs` | export records, staleness check |
| `release_evidence` | `/teaching-packs` | release evidence audit |
| `teaching_session_live` | `/teaching-sessions` | SSE, slide advance, branch selection, student responses |
| `auth_router` | `/auth` | login (JWT), /me |
| `notifications` | `/notifications` | teacher notifications + admin recovery |
| `webhooks` | `/webhook` | Telegram, Zalo, notify, frontend error |
| `media_assets` | `/media-assets` | upload, list, retrieve, AI alt text |
| `ops` | `/ops` | SLO metrics snapshot |
| `runs` | `/run` | Legacy (decommissioned: POST returns 410) |

### auth/ (6 files)
- JWT-based via PyJWT: `JWTMiddleware` validates Bearer token, `get_current_user`/`require_teacher`/`require_admin` FastAPI DI
- Roles: TEACHER, ADMIN, SCHOOL_ADMIN, SYSTEM_ADMIN
- `ownership.py` — Cross-tenant ownership checks (SYSTEM_ADMIN always authorized, SCHOOL_ADMIN same-org, TEACHER owner match)
- `session_token.py` — Separate session-role tokens for teaching sessions (NOT account JWT)

### Teaching Pack Orchestration
- `teaching_pack_store.py` — `TeachingPackRunStore`: run CRUD, event log, gate management, status transitions
- `teaching_pack_executor.py` — Bridges worker jobs → `graph.ainvoke()` (start) or `graph.ainvoke(Command(resume=...))` (resume)
- `teaching_pack_worker.py` — Lease-based job polling, heartbeat, retry with backoff, batch concurrency (1-10)
- `teaching_pack_db.py` — FastAPI DI for async DB sessions
- `teaching_pack_gate_registry.py` — 6 gate names with allowed actions validation
- `teaching_pack_quality_gate.py` — `GatewayTeachingPackQualityGate`: L1 (schema) + L2 (PII, age, fact-check, pedagogical) + L3 (HTML)
- `teaching_pack_event_bus.py` — In-process version-counter + anyio.Event for SSE
- `teaching_pack_completion.py` — Post-graph completion (render snapshots, open content gate, write exports)
- `recovery_sweeper.py` — Background sweeper: stuck job reclaim + gate timeout escalation (24h)

### Teaching Session System
- `teaching_session/models.py` — SQLAlchemy models: TeachingSession, SessionAuditEvent, ClassRosterEntry
- `teaching_session/service.py` — Session creation with retention tier validation, room code generation
- `teaching_session/live_sync.py` — Redis Pub/Sub + Postgres fallback for SSE

### Database (SQLAlchemy + Alembic)
- 29 migration files (001_initial through 029_precomputed_branches)
- Core tables: users, runs, artifacts, run_status_history, run_contracts, gate_interrupts, gate_responses, run_events, run_jobs, teaching_sessions, teaching_session_events, media_assets, cost_logs, + more

### observability/ — Langfuse integration (graceful no-op)
### webhooks/ — Telegram (HMAC-SHA256), Zalo (shared secret) inbound verification

## Depends on

- **`agents`** — imports `build_teaching_pack_graph`, `TeachingPackState`, `teaching_pack_thread_config`, `events.emit_run_event`, `teaching_pack.stages` (`main.py:150`, `teaching_pack_executor.py`)
- **`contracts`** — imports 72+ Pydantic models: `RunContract`, `ArtifactContent`, `LessonSequence`, `JudgeOutput`, etc. (all store/model files)
- **`quality`** — imports `validate_schema`, `html_hard_blocks`, `detect_pii` via `teaching_pack_quality_gate.py`
- external: `fastapi`, `sqlalchemy`, `pydantic-settings`, `langgraph`, `redis`, `langfuse`

## Used by

- **`web`** — all API calls originate from the Next.js frontend via `APIClient`
- **`tests`** — 145 test files in `services/gateway/tests/`

## Data & side effects

- Reads/writes: PostgreSQL (runs, events, gates, sessions, media assets), Redis (circuit breaker, session pub/sub)
- Network calls: LLM calls via 9Router (indirect, through agents pipeline), Telegram Bot API (outbound webhooks)
- Config/env vars: `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET`, `JWT_ALGORITHM`, `JWT_EXPIRY_HOURS`, `LANGFUSE_*`, `WORKER_MODE`, `WORKER_CONCURRENCY`

## Notes / discrepancies vs existing docs

- AGENTS.md §11 lists gateway on port `:8001` but the Makefile uses `:8101` for local dev (`LOCAL_GATEWAY_PORT := 8101`). The `docker-compose.yml` maps `8001:8001`. Both are correct (different environments) but this should be documented explicitly.
- The gateway is a **job-queue adapter** between HTTP and LangGraph. Teachers never call the graph directly — they create jobs in DB, the worker picks them up, runs the graph, and the completion recorder translates graph output back to DB state.
- The teaching session system is architecturally distinct from the teaching pack pipeline — it's a live delivery overlay with its own auth (session-role tokens), its own event log, and Redis-backed Pub/Sub.

---

_Traced from source on 2026-07-10. Files examined in depth: all 325 files in services/gateway. The most important files are main.py (composition root), teaching_pack_executor.py (graph bridge), and teaching_pack_store.py (persistence layer)._
