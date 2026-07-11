# Module: gateway

**Path:** `services/gateway`
**Role:** FastAPI HTTP gateway — exposes the REST API for teaching pack runs, sessions, notifications, and webhooks; embeds the LangGraph agent runtime; manages job execution, persistence, streaming, and teacher gate interactions.

## Public interface

### Health

| Method | Path | Handler | Notes |
|--------|------|---------|-------|
| GET | `/health` | `main.py:264` `health_check` | Load balancer probe |

### Auth (prefix `/auth`)

| Method | Path | Handler | Auth |
|--------|------|---------|------|
| POST | `/auth/login` | `routers/auth_router.py:28` `login` | None (returns JWT) |
| GET | `/auth/me` | `routers/auth_router.py:41` `get_me` | Placeholder (401) |

### Legacy Run Routes (prefix `/run`) — mostly decommissioned

| Method | Path | Handler | Status |
|--------|------|---------|--------|
| GET | `/run` | `routers/runs.py:203` `list_runs` | Active (in-memory) |
| POST | `/run` | `routers/runs.py:222` `create_run` | **410 Gone** — decommissioned |
| GET | `/run/{run_id}` | `routers/runs.py:234` `get_run` | Active |
| GET | `/run/{run_id}/status` | `routers/runs.py:252` `get_run_status` | SSE stream |
| GET | `/run/{run_id}/exports` | `routers/runs.py:300` `list_exports` | Active |
| GET | `/run/{run_id}/exports/{artifact_id}` | `routers/runs.py:330` `download_export` | Active |
| GET | `/run/{run_id}/artifacts` | `routers/artifacts.py:63` `list_artifacts` | Legacy, in-memory |
| GET | `/run/{run_id}/artifacts/{artifact_id}` | `routers/artifacts.py:82` `get_artifact` | Legacy, in-memory |
| POST | `/run/{run_id}/approve` | `routers/approvals.py:35` `approve` | **410 Gone** |
| POST | `/run/{run_id}/reject` | `routers/approvals.py:49` `reject` | **410 Gone** |
| POST | `/run/{run_id}/snapshots` | `routers/snapshots.py:62` `produce_snapshot` | Legacy |

### Teaching Pack Runs (prefix `/teaching-packs`)

| Method | Path | Handler | Notes |
|--------|------|---------|-------|
| POST | `/teaching-packs/run` | `routers/teaching_pack_runs.py:77` `create_teaching_pack_run` | 202 Accepted |
| POST | `/teaching-packs/runs` | same | Dual path alias |
| POST | `/teaching-packs/run/{run_id}/resume` | `routers/teaching_pack_runs.py:148` `resume_teaching_pack_run` | Gate resume |
| POST | `/teaching-packs/runs/{run_id}/resume` | same | Dual path alias |
| POST | `/teaching-packs/runs/{run_id}/artifacts/{artifact_id}/request-revision` | `routers/teaching_pack_runs.py:286` `request_artifact_revision` | Scoped revision |
| GET | `/teaching-packs/run/{run_id}` | `routers/teaching_pack_lifecycle.py:43` `get_teaching_pack_run` | Run status + pending gate |
| POST | `/teaching-packs/run/{run_id}/cancel` | `routers/teaching_pack_lifecycle.py:94` `cancel_teaching_pack_run` | Cancel run |
| DELETE | `/teaching-packs/run/{run_id}` | `routers/teaching_pack_lifecycle.py:138` `delete_teaching_pack_run` | Soft delete |
| POST | `/teaching-packs/run/{run_id}/restore` | `routers/teaching_pack_lifecycle.py:170` `restore_teaching_pack_run` | Restore soft-deleted |
| GET | `/teaching-packs/run/{run_id}/status` | `routers/teaching_pack_stream.py:59` `stream_teaching_pack_status` | SSE event stream |

### Teaching Pack Snapshots & Preview (prefix `/teaching-packs`)

| Method | Path | Handler | Notes |
|--------|------|---------|-------|
| GET | `/teaching-packs/run/{run_id}/snapshots/{snapshot_id}` | `routers/teaching_pack_previews.py:87` `get_rendered_snapshot_metadata` | Metadata only |
| GET | `/teaching-packs/run/{run_id}/snapshots/{snapshot_id}/preview` | `routers/teaching_pack_previews.py:102` `preview_rendered_snapshot` | Student/teacher/print HTML |
| POST | `/teaching-packs/run/{run_id}/approved-snapshots` | `routers/teaching_pack_previews.py:171` `approve_rendered_snapshots` | Batch approve |
| POST | `/teaching-packs/run/{run_id}/snapshots/{snapshot_id}/translate` | `routers/teaching_pack_previews.py:216` `translate_slide_deck_snapshot` | SDX-01 translation |
| PATCH | `/teaching-packs/run/{run_id}/snapshots/{snapshot_id}/blocks/{block_id}` | `routers/teaching_pack_previews.py:277` `edit_slide_deck_snapshot_block` | SDE-04 scoped edit |
| POST | `.../blocks/{block_id}/rewrite-suggestion` | `routers/teaching_pack_previews.py:431` `suggest_slide_deck_block_rewrite` | SDE-08 AI rewrite |
| POST | `.../blocks/{block_id}/rewrite-suggestion/cancelled` | `routers/teaching_pack_previews.py:521` `cancel_slide_deck_block_rewrite_suggestion` | Observability ping |
| GET | `/teaching-packs/run/{run_id}/artifacts/{artifact_id}/versions` | `routers/teaching_pack_previews.py:563` `list_artifact_versions` | SDE-05 version history |
| POST | `.../versions/{version_snapshot_id}/restore` | `routers/teaching_pack_previews.py:617` `restore_artifact_version` | SDE-05 restore |

### Teaching Pack Exports (prefix `/teaching-packs`)

| Method | Path | Handler | Notes |
|--------|------|---------|-------|
| GET | `/teaching-packs/run/{run_id}/exports` | `routers/exports.py:109` `list_exports` | DB-backed export records |
| GET | `.../artifacts/{artifact_id}/export-status` | `routers/exports.py:136` `get_export_status` | Staleness check |
| GET | `.../artifacts/{artifact_id}/export-status/by-format` | `routers/exports.py:169` `get_export_status_by_format` | Per-format staleness |
| POST | `.../artifacts/{artifact_id}/exports/regenerate` | `routers/exports.py:214` `regenerate_exports` | Teacher-triggered re-export |
| POST | `/teaching-packs/run/{run_id}/exports/teaching-pack` | `routers/exports.py:284` `export_teaching_pack_bundle` | Bundle all artifacts into one HTML |

### Teaching Briefs (prefix `/teaching-packs`)

| Method | Path | Handler | Notes |
|--------|------|---------|-------|
| POST | `/teaching-packs/briefs` | `routers/teaching_briefs.py:52` `create_teaching_brief` | 201 |
| GET | `/teaching-packs/briefs/{brief_id}` | `routers/teaching_briefs.py:67` `get_teaching_brief` | |
| PUT | `/teaching-packs/briefs/{brief_id}` | `routers/teaching_briefs.py:76` `autosave_teaching_brief` | |
| GET | `/teaching-packs/briefs/{brief_id}/contract-preview` | `routers/teaching_briefs.py:90` `preview_teaching_brief_contract` | |
| POST | `/teaching-packs/briefs/{brief_id}/launch` | `routers/teaching_briefs.py:124` `launch_teaching_brief` | 202 Accepted |

### Artifact Documents — V2 Editing/Review (prefix `/teaching-packs`)

| Method | Path | Handler | Notes |
|--------|------|---------|-------|
| GET | `.../runs/{run_id}/artifacts/{artifact_id}/versions` | `routers/artifact_documents.py:179` `list_artifact_document_versions` | V2 version list |
| POST | `.../artifacts/{artifact_id}/edit` | `routers/artifact_documents.py:200` `edit_artifact_document_route` | Registry-driven edit |
| POST | `.../artifacts/{artifact_id}/restore` | `routers/artifact_documents.py:234` `restore_artifact_document_route` | |
| POST | `.../artifacts/{artifact_id}/translate` | `routers/artifact_documents.py:266` `create_language_version_route` | Source-linked lineage |
| POST | `.../artifacts/{artifact_id}/variants` | `routers/artifact_documents.py:303` `create_content_variant_route` | Independently approvable |
| POST | `.../artifacts/{artifact_id}/rewrite-proposal` | `routers/artifact_documents.py:334` `propose_artifact_block_rewrite` | Ephemeral AI proposal |
| POST | `.../artifacts/{artifact_id}/notes` | `routers/artifact_documents.py:390` `create_review_note` | 201 |
| GET | `.../artifacts/{artifact_id}/notes` | `routers/artifact_documents.py:415` `list_review_notes` | |
| POST | `.../notes/{note_id}/resolve` | `routers/artifact_documents.py:427` `resolve_review_note` | |
| POST | `.../artifacts/{artifact_id}/approve` | `routers/artifact_documents.py:441` `approve_artifact` | 204 No Content |
| POST | `.../approve-all-current` | `routers/artifact_documents.py:472` `approve_all_current_route` | Bulk approve |
| POST | `.../artifacts/{artifact_id}/claim-evidence` | `routers/artifact_documents.py:494` `persist_claim_evidence` | Fail-closed per ADR-054 |
| GET | `.../versions/{version}/provenance` | `routers/artifact_documents.py:530` `get_decision_provenance` | |
| POST | `.../delegate` | `routers/artifact_documents.py:552` `delegate_reviewer` | Owner-only delegation |

### Content Briefs (prefix `/teaching-packs`)

| Method | Path | Handler | Notes |
|--------|------|---------|-------|
| POST | `.../runs/{run_id}/content-briefs` | `routers/content_briefs.py:78` `create_content_brief` | 201 |
| GET | `.../content-briefs/{content_brief_id}` | `routers/content_briefs.py:96` `get_content_brief` | |
| POST | `.../content-briefs/{id}/fill-failures` | `routers/content_briefs.py:113` `record_fill_failure` | Strategy review |
| POST | `.../content-briefs/{id}/strategy-change-requests` | `routers/content_briefs.py:133` `record_strategy_change_request` | |
| GET | `.../content-briefs/{id}/review` | `routers/content_briefs.py:156` `list_strategy_review` | |
| POST | `.../content-briefs/{id}/verify-compliance` | `routers/content_briefs.py:182` `verify_compliance` | 204 |

### Source Collections (prefix `/teaching-packs`)

| Method | Path | Handler | Notes |
|--------|------|---------|-------|
| POST | `/teaching-packs/source-collections` | `routers/source_collections.py:54` `create_source_collection` | 201 |
| GET | `/teaching-packs/source-collections/{id}` | `routers/source_collections.py:71` `get_source_collection` | |
| POST | `.../source-collections/{id}/entries` | `routers/source_collections.py:89` `add_source_collection_entry` | 201 |

### Media Assets (prefix `/media-assets`, no `/teaching-packs`)

| Method | Path | Handler | Notes |
|--------|------|---------|-------|
| POST | `/media-assets` | `routers/media_assets.py:77` `upload_media_asset` | 10MB limit |
| GET | `/media-assets` | `routers/media_assets.py:113` `list_media_assets` | |
| GET | `/media-assets/{asset_id}/file` | `routers/media_assets.py:125` `get_media_asset_file` | Binary |
| POST | `/media-assets/{asset_id}/generate-alt-text` | `routers/media_assets.py:139` `generate_media_asset_alt_text` | SDX-04 |
| PUT | `/media-assets/{asset_id}/alt-text` | `routers/media_assets.py:167` `set_media_asset_alt_text` | |

### Media Asset Versions (prefix `/teaching-packs`)

| Method | Path | Handler | Notes |
|--------|------|---------|-------|
| POST | `/teaching-packs/media-asset-versions` | `routers/media_asset_versions.py:70` `create_media_asset_version` | 201, checksummed |
| POST | `.../media-asset-versions/{id}/replace` | `routers/media_asset_versions.py:104` `replace_media_asset_version` | 201 |
| GET | `.../media-asset-versions/{id}` | `routers/media_asset_versions.py:134` `get_media_asset_version` | |
| GET | `.../media-asset-versions/{id}/versions` | `routers/media_asset_versions.py:144` `list_media_asset_versions` | |
| GET | `.../media-asset-versions/{id}/file` | `routers/media_asset_versions.py:155` `get_media_asset_version_file` | Verified checksum |
| DELETE | `.../media-asset-versions/{id}` | `routers/media_asset_versions.py:176` `delete_media_asset_version` | 204 |
| POST | `.../media-asset-versions/{id}/dependencies` | `routers/media_asset_versions.py:200` `record_media_asset_dependency` | 201 |
| POST | `.../visual-source-suggestions` | `routers/media_asset_versions.py:218` `create_visual_source_suggestion` | 201 |
| GET | `.../visual-source-suggestions` | `routers/media_asset_versions.py:239` `list_visual_source_suggestions` | |
| POST | `.../visual-source-suggestions/{id}/convert` | `routers/media_asset_versions.py:253` `convert_visual_source_suggestion` | |
| POST | `.../visual-source-suggestions/{id}/dismiss` | `routers/media_asset_versions.py:283` `dismiss_visual_source_suggestion` | |

### Slide Deck Live Publication (prefix `/teaching-packs`)

| Method | Path | Handler | Notes |
|--------|------|---------|-------|
| POST | `.../run/{run_id}/publish-to-live` | `routers/slide_deck_live_publication.py` | Publish approved deck to session |
| POST | `.../run/{run_id}/republish-to-live` | same | Re-pin to newer approved version |

### Release Evidence (prefix `/teaching-packs`)

| Method | Path | Handler | Notes |
|--------|------|---------|-------|
| GET | `.../run/{run_id}/evidence` | `routers/release_evidence.py` | Query audit records |
| POST | `.../run/{run_id}/evidence` | same | Generate + persist (admin) |
| GET | `/teaching-packs/release-evidence` | same | List recent (admin) |

### Units (prefix `/teaching-packs`)

| Method | Path | Handler | Notes |
|--------|------|---------|-------|
| GET | `.../units/{parent_run_id}` | `routers/unit_runs.py:97` `get_unit_view` | Unit aggregate view |
| GET | `.../units/{parent_run_id}/status` | `routers/unit_runs.py:176` `stream_unit_status` | Multiplexed SSE |
| POST | `.../units/{parent_run_id}/approve-all` | `routers/unit_runs.py:203` `approve_all_sessions` | |
| POST | `.../units/{parent_run_id}/sessions/{session_id}/spawn-anyway` | `routers/unit_runs.py:258` `spawn_anyway` | |
| POST | `.../units/{parent_run_id}/export` | `routers/unit_runs.py:313` `export_unit` | |

### Webhooks (prefix `/webhook`)

| Method | Path | Handler | Notes |
|--------|------|---------|-------|
| POST | `/webhook/notify` | `routers/webhooks.py:66` `send_notification` | |
| POST | `/webhook/telegram` | `routers/webhooks.py:92` `telegram_webhook` | HMAC-SHA256 verified |
| POST | `/webhook/zalo` | `routers/webhooks.py:112` `zalo_webhook` | Shared secret verified |
| POST | `/webhook/error` | `routers/webhooks.py:267` `frontend_error` | Client error reports |

### Notifications (prefix `/notifications`)

| Method | Path | Handler | Notes |
|--------|------|---------|-------|
| GET | `/notifications` | `routers/notifications.py:101` `list_notifications` | |
| POST | `/notifications/{id}/read` | `routers/notifications.py:115` `read_notification` | |
| POST | `/notifications/{id}/dismiss` | `routers/notifications.py:133` `dismiss` | |
| GET | `/notifications/admin/runs` | `routers/notifications.py:155` `list_admin_runs` | Admin only |
| GET | `/notifications/admin/runs/{run_id}/summary` | `routers/notifications.py:219` `get_run_summary` | Admin only |
| POST | `/notifications/admin/runs/{run_id}/recover` | `routers/notifications.py:246` `recover_run` | Admin only |

### Ops (prefix `/ops`)

| Method | Path | Handler | Notes |
|--------|------|---------|-------|
| GET | `/ops/slo` | `routers/ops.py:17` `get_slo_snapshot` | Admin only |

### Teaching Session Live (prefix `/teaching-sessions`) — session-token auth, not JWT

| Method | Path | Handler | Notes |
|--------|------|---------|-------|
| POST | `/teaching-sessions/join` | `routers/teaching_session_live.py` | Token issuance |
| GET | `/teaching-sessions/{session_id}/stream` | same | SSE broadcast |
| GET | `/teaching-sessions/{session_id}/state` | same | Polling fallback |
| GET | `/teaching-sessions/{session_id}/content` | same | Current snapshot HTML |
| POST | `/teaching-sessions/{session_id}/slide` | same | Navigate slide |
| POST | `/teaching-sessions/{session_id}/responses` | same | Student response capture |
| POST | `/teaching-sessions/{session_id}/end` | same | End session |

## Internal structure

### Entry point & lifecycle

- **`main.py`** — FastAPI app factory. Lifespan initializes: SQLAlchemy engine (`postgresql+asyncpg://...`), LangGraph checkpointer, teaching pack graph (`build_teaching_pack_graph`), in-process worker loop, recovery sweeper (60s interval). Middleware: JWT, RequestID, CORS.
- **`secrets_guard.py`** — Validates production secrets at startup.
- **`logging_config.py`** — Structured JSON logging setup.

### Agent runtime embedding

- **`main.py:159`** — `build_teaching_pack_graph(checkpointer=..., store=..., quality_gate=...)` constructs the LangGraph `StateGraph` at startup and stores it in `app.state.teaching_pack_graph`.
- **`teaching_pack_executor.py:85-176`** — `TeachingPackExecutor` wraps the graph: calls `graph.ainvoke(state, config)` for new runs and `graph.ainvoke(Command(resume=...), config)` for gate resumptions. Delegates to `TeachingPackFailureSink`/`TeachingPackCompletionSink` protocols.
- **`teaching_pack_worker.py:37-168`** — `TeachingPackWorker` polls `run_jobs` table via claim-lease pattern, dispatches to executor. `run_worker_batch()` processes N concurrent jobs per cycle.

### Job execution & orchestration

- **`teaching_pack_worker.py:171-208`** — `run_worker_batch()` claims jobs, starts them in a task group. Each job runs `TeachingPackWorker.run_claimed()` with heartbeat lease refresh.
- **`unit_orchestrator.py`** — Reconciles unit parent/child run states.

### Quality gates (gateway-owned)

- **`teaching_pack_quality_gate.py:15-278`** — `GatewayTeachingPackQualityGate` implements the quality gate interface. Calls into `packages/quality` for Layer 2 (FACT checker, PII, age, pedagogical metrics) and Layer 3 (HTML validation).
- **`quality_gates.py:39-274`** — Deterministic validation: placeholder scanning, answer-key leakage, PII detection, accessibility checks, export readiness, healing strategy classification.
- **`quality_workflow.py:27-90`** — Event-writing wrappers for quality results and export readiness.

### Persistence layer

- **`models.py`** — SQLAlchemy ORM models (schema: `public`): `users`, `runs`, `artifacts`, `teaching_briefs`, `class_profiles`, `decomposition_feedback`, `decomposition_templates`, `teacher_decomposition_preferences`, `media_assets`, `cost_logs` (schema: `litellm`).
- **`teaching_pack_models.py`** — Teaching-pack-specific ORM models: `run_status_history`, `run_contracts`, `contract_revisions`, `gate_interrupts`, `gate_responses`, `run_events`, `run_jobs`. Also re-exports: `ArtifactWorkflow`, `ArtifactSnapshot`, `VocabularyCluster*`.
- **`teaching_pack_artifact_models.py`** — `ArtifactWorkflow` table.
- **`teaching_pack_snapshot_models.py`** — `ArtifactSnapshot` table.
- **`teaching_pack_job_store.py`** — `TeachingPackJobStore` — claim/lease/mark lifecycle for `run_jobs`; `RunJobStatus.DEAD_LETTER` (#124) is an inspectable/replayable holding state (excluded from `claim_next`/`list_pending` like `FAILED`, but distinct from it) — `mark_dead_letter()` records `last_error`/`error_classification`/`dead_lettered_at`, `replay_dead_letter()` resets a dead-lettered job to `pending` with a clean attempt count.
- **`teaching_pack_store.py`** — `TeachingPackRunStore` — run status transitions, event log, observability events.
- **`teaching_pack_control_store.py`** — `TeachingPackControlStore` — gate interrupt/response management, contract CRUD.
- **`teaching_pack_snapshot_store.py`** — `TeachingPackSnapshotStore` — snapshot CRUD, approval, optimistic locking.
- **`teaching_pack_export_store.py`** — `TeachingPackExportStore` — export records, staleness checks.
- **`teaching_pack_db.py`** — Session factory + `get_teaching_pack_session` dependency.
- **`artifact_document_store.py`** — `ArtifactDocumentStore` — V2 `ArtifactDocument`/`AnswerSet`/variant/dependency/approval persistence (`persist`, `create_edit` with an advisory-lock optimistic-lock retry); `get_preview_source` (`:187`) returns the linked V2 snapshot or falls back to the legacy V1 `ArtifactSnapshot` (`legacy=True`), emitting an `artifact_document_legacy_read` observability event on the fallback path (#463 rollout metric).
- **`artifact_document_content_store.py`** — `GatewayArtifactDocumentContentStore` — the agents-facing `ArtifactContentStore` port implementation the gateway composes at startup (`main.py:93,119,165,189`) that persists through `ArtifactDocumentStore`/Postgres instead of the LangGraph store; converts via `common.contracts.artifact_projection_mapper`.

### Auth

- **`auth/models.py`** — `User`, `Token`, `TokenPayload`, `LoginRequest` (Pydantic). Roles: TEACHER, ADMIN, SCHOOL_ADMIN, SYSTEM_ADMIN.
- **`auth/dependencies.py`** — `get_current_user` (JWT Bearer), `require_teacher`, `require_admin`. SSE variant `get_current_user_for_status_stream` accepts cookie fallback.
- **`auth/jwt_handler.py`** — JWT creation/verification.
- **`auth/config.py`** — JWT secret/algorithm configuration.
- **`auth/ownership.py`** — Run ownership verification helpers.

### Middleware

- **`middleware/auth_middleware.py`** — `JWTMiddleware` — auto-decodes JWT on every request, sets `request.state.user`. Exempts public prefixes (webhooks, teaching-session live).
- **`middleware/request_id.py`** — `RequestIDMiddleware` — attaches UUID per request.
- **`middleware/error_handler.py`** — Global exception handlers (NotFoundError, AuthorizationError → structured JSON).

### Supporting services

- **`backpressure.py`** — Rate limiting per teacher (concurrent runs, queue depth).
- **`recovery_sweeper.py`** — Periodic sweep: stuck jobs → requeue (under `max_attempts`) or dead-letter (#124, at/over `max_attempts` — was `FAILED` before #124), expired gate interrupts → escalate.
- **`soft_delete.py`** — Soft delete + restore for runs.
- **`renderer_adapter.py`** — Bridges to `packages/renderer` for HTML rendering.
- **`research_*.py`** — Research engine, provider (9Router), safety, URL handling, gate.
- **`media_storage.py`** — File-system media storage with teacher-scoped keys.
- **`teaching_session/`** — Teaching session data model, retention, event log, live sync, session auth.
- **`webhooks/`** — Telegram/Zalo webhook signature verification, config.
- **`observability/`** — Observability event infrastructure.
- **`slo_metrics.py`** + **`slo_alerting.py`** — SLO computation and alerting.
- **`budget.py`** + **`budget_db.py`** — Per-teacher budget tracking.

## Depends on

- **`agents`** — LangGraph runtime, graph construction, events, slide deck engine (26 files)
- **`contracts`** — Pydantic schemas for artifact, quality, slide deck, teaching brief
- **`quality`** — Layer 2/3 quality checks (FACT checker, PII, HTML validation)
- **`renderer`** — HTML rendering via adapter + export writer

### packages/agents (LangGraph runtime)

| What | Where imported | Evidence |
|------|---------------|----------|
| `build_teaching_pack_graph` | `main.py:159` | Constructs the authoritative stage graph at startup |
| `get_checkpointer` | `main.py:158` | MemorySaver/SqliteSaver/PostgresSaver per environment |
| `open_teaching_pack_store`, `get_development_store`, `sync_connection_string` | `main.py:161-164` | LangGraph store for multi-tenant memory |
| `LangGraphArtifactContentStore` | `main.py:93` | Bridges artifact store to LangGraph content orchestrator; `GatewayArtifactDocumentContentStore` (gateway-owned, `artifact_document_content_store.py`) is the alternative V2-backed composition (#463) |
| `teaching_pack_thread_config`, `LangGraphRunnableConfig` | `teaching_pack_executor.py:11` | Thread config for graph invocation |
| `Command` (from `langgraph.types`) | `teaching_pack_executor.py:8` | Gate resume via `Command(resume=...)` |
| `EmptyInputError` | `teaching_pack_executor.py:7` | Missing checkpoint handling |
| `safe_error_summary` | `teaching_pack_executor.py:10` | Agent LLM error formatting |
| `get_run_events`, `has_terminal_event`, `subscribe`, `unsubscribe` | `routers/runs.py:13` | In-memory event bus for SSE |
| `drain_observability_events` | `teaching_pack_worker.py:235` | Persist pipeline observability events |
| `ObservabilityEvent`, `ObservabilityEventType` | `routers/teaching_pack_previews.py:17` | Slide deck editor observability |
| `features` (feature flags) | `routers/teaching_pack_previews.py:18` | Gating slide deck editor/AI rewrite |
| `translate_slide_deck` | `routers/teaching_pack_previews.py:19` | SDX-01 translation engine |
| `generate_slide_deck_block_rewrite`, `resolve_rewrite_instruction` | `routers/teaching_pack_previews.py:21-22` | SDE-08 AI block rewrite |
| `apply_scoped_slide_deck_block_edit`, `slide_deck_block_edit_event` | `routers/teaching_pack_previews.py:26-27` | SDE-04 scoped block edit |
| `TransentProviderError` | `teaching_pack_worker.py:86` | Retryable LLM provider errors; `TeachingPackWorker._handle_job_error` retries with capped backoff up to `TeachingPackWorkerConfig.max_transient_attempts` (default 3), then dead-letters (`classification="transient_exhausted"`) — a permanent/unclassified error dead-letters immediately (`classification="permanent"`, 0 retries) (#124) |

### common/contracts (Pydantic schemas)

| What | Where imported | Evidence |
|------|---------------|----------|
| `ArtifactContent` | `quality_gates.py:8`, `teaching_pack_previews.py:11` | Artifact schema validation |
| `ArtifactQualityReport`, `QualityFailureClass`, `QualityIssue`, `HealingDecision`, `HealingStrategy`, `ExportReadinessReport` | `quality_gates.py:9-16`, `teaching_pack_quality_gate.py:4`, `quality_workflow.py:16` | Quality gate report types |
| `ArtifactWorkflowState` | `teaching_pack_quality_gate.py:3` | Workflow state for gate evaluation |
| `TeachingBrief`, `materiality_reasons` | `routers/teaching_briefs.py:9` | Brief contract + materiality logic |
| `ContentBrief`, `AnswerPolicy`, `MethodologySource` | `routers/content_briefs.py:13-14` | Content brief contracts |
| `StrategyChangeRequest`, `SpecialistOutputDeclaration`, `enforce_content_brief_compliance` | `routers/content_briefs.py:16-23` | Strategy review enforcement |
| `SlideDeckData`, `SlideDeckDisplayPreferences`, `resolve_slide_deck_display_preferences` | `routers/teaching_pack_previews.py:13-15` | Slide deck contracts |
| `SourceCollection`, `SourceCollectionEntry`, `SourceAuthority` | `routers/source_collections.py:13-16` | Source collection contracts |
| `ArtifactDocument`, `ArtifactPayload`, `DocumentAuthority`, `DocumentLanguage` | `routers/artifact_documents.py:14-18` | V2 artifact document contracts |
| `ClaimEvidence` | `routers/artifact_documents.py:19` | Claim evidence contracts |
| `DecisionProvenance` | `routers/artifact_documents.py:20` | Decision provenance contracts |
| `MediaAssetVersion`, `MediaAssetOwnerScope` | `routers/media_asset_versions.py:12` | Media asset version contracts |
| `VisualSourceSuggestion` | `routers/media_asset_versions.py:13` | Visual source suggestion contracts |
| `LessonSequence` | `routers/unit_runs.py:11` | Unit lesson sequence contracts |
| `UnitView`, `UnitAggregate`, `UnitParentMeta`, `UnitSessionProgress` | `routers/unit_runs.py:12-17` | Unit view contracts |

### packages/quality (quality gate layers)

| What | Where imported | Evidence |
|------|---------------|----------|
| `check_age_appropriateness` | `teaching_pack_quality_gate.py:5` | Layer 2 age check |
| `FACTChecker`, `SourceDocument`, `VerificationTag` | `teaching_pack_quality_gate.py:6` | Layer 2 fact verification |
| `check_pedagogical_metrics` | `teaching_pack_quality_gate.py:7` | Layer 2 pedagogical metrics |
| `detect_pii` | `teaching_pack_quality_gate.py:8` | Layer 2 PII detection |
| `HTMLValidator` | `teaching_pack_quality_gate.py:9` | Layer 3 HTML validation |

### packages/renderer (HTML rendering)

| What | Where imported | Evidence |
|------|---------------|----------|
| `render_artifact_content` | `routers/teaching_pack_previews.py:67` (via `renderer_adapter.py`) | Renders ArtifactContent → standalone HTML |
| `TeachingPackBundleWriter` | `routers/exports.py:45` (via `teaching_pack_export_writer.py`) | Bundles all artifacts into one HTML |

### Third-party

| What | Where imported | Evidence |
|------|---------------|----------|
| `FastAPI`, `APIRouter`, `Depends`, `HTTPException`, `status` | Throughout `routers/` | Web framework |
| `sqlalchemy` (async) | Throughout stores and models | ORM + async sessions |
| `pydantic` (BaseModel) | Throughout routers (request/response schemas) | Data validation |
| `anyio` | `main.py:14`, `teaching_pack_worker.py:7` | Async concurrency (task groups, sleep) |
| `orjson` | `routers/runs.py:8`, `routers/teaching_session_live.py` | Fast JSON serialization |
| `httpx2` | `routers/webhooks.py:11` | Async HTTP client for outbound webhooks |
| `redis` | `routers/teaching_session_live.py:28` | Redis pub/sub for live session sync |
| `langgraph` | `teaching_pack_executor.py:7-8` | LangGraph runtime (Command, EmptyInputError) |

## Used by

_No confirmed callers discovered during this trace._

The gateway is the top-level HTTP service — nothing in the codebase imports from it (enforced by INVARIANT-02: services/* and apps/* may import from packages/* and common/*, but not the reverse). External consumers:

- **`apps/web`** — Next.js frontend. Targets gateway via `NEXT_PUBLIC_GATEWAY_URL` (`:8101` local dev, `:8001` Docker).
- **Telegram/Zalo bots** — POST webhooks to `/webhook/telegram` and `/webhook/zalo`.
- **External notification services** — POST to `/webhook/notify`.
- **Load balancers / monitoring** — GET `/health`, GET `/ops/slo`.

Internal cross-module calls within the gateway:

- **`teaching_pack_worker.py`** → `teaching_pack_executor.py` — Worker dispatches claimed jobs to executor.
- **`teaching_pack_executor.py`** → `packages.agents.teaching_pack.graph` — Executor invokes the LangGraph graph.
- **`teaching_pack_quality_gate.py`** → `packages.quality.*` — Quality gate delegates to Layer 2/3 checks.
- **`main.py`** → `recovery_sweeper.py` — Background sweeper requeues stuck jobs, escalates expired gates.
- **`main.py`** → `unit_orchestrator.py` — Background reconciliation of unit parent/child states.

## Data & side effects

### Database tables (schema: `public`)

| Table | Model | File:line |
|-------|-------|-----------|
| `users` | `User` | `models.py:62` |
| `runs` | `Run` | `models.py:75` |
| `artifacts` | `Artifact` | `models.py:212` |
| `teaching_briefs` | `TeachingBriefModel` | `models.py:125` |
| `class_profiles` | `ClassProfileModel` | `models.py:141` |
| `decomposition_feedback` | `DecompositionFeedbackModel` | `models.py:160` |
| `decomposition_templates` | `DecompositionTemplateModel` | `models.py:176` |
| `teacher_decomposition_preferences` | `TeacherPreferenceModel` | `models.py:200` |
| `media_assets` | `MediaAssetModel` | `models.py:228` |
| `run_status_history` | `RunStatusHistory` | `teaching_pack_models.py:96` |
| `run_contracts` | `RunContract` | `teaching_pack_models.py:113` |
| `contract_revisions` | `ContractRevision` | `teaching_pack_models.py:133` |
| `gate_interrupts` | `GateInterrupt` | `teaching_pack_models.py:155` |
| `gate_responses` | `GateResponse` | `teaching_pack_models.py:182` |
| `run_events` | `RunEvent` | `teaching_pack_models.py:204` |
| `run_jobs` | `RunJob` | `teaching_pack_models.py:227` |
| `cost_logs` | `CostLog` (schema: `litellm`) | `models.py:254` |

Plus tables from re-exported models: `artifact_workflows`, `artifact_snapshots`, `vocabulary_cluster_*`.

### Network calls

| Target | Where | Purpose |
|--------|-------|---------|
| Telegram Bot API | `routers/webhooks.py` (via `webhooks/telegram.py`) | Verify webhook signature |
| Zalo API | `routers/webhooks.py` (via `webhooks/zalo.py`) | Verify webhook signature |
| Outbound webhook URLs | `routers/webhooks.py:52-62` | Dispatch notifications to configured URLs |
| Redis | `routers/teaching_session_live.py`, `teaching_session/live_sync.py` | Pub/Sub for live session sync |
| LLM providers (via `packages/agents`) | `teaching_pack_executor.py` (graph invocation) | All LLM calls go through 9Router |
| Renderer (`packages/renderer`) | `renderer_adapter.py`, `teaching_pack_export_writer.py` | ArtifactContent → standalone HTML |

### File system

| Path | Purpose |
|------|---------|
| `media_storage.py` → teacher-scoped storage | Image/diagram uploads under `teacher-media/{teacher_id}/` |
| `teaching_pack_export_writer.py` | Export file storage |
| `alembic/` | Database migration scripts |

### Environment variables

| Variable | Default | Where read | Purpose |
|----------|---------|------------|---------|
| `DATABASE_URL` | `postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class` | `main.py:168` | Database connection |
| `OMC_ENVIRONMENT` | `development` | `main.py:167` | Controls checkpointer type + store |
| `OMC_ENABLE_SIX_LAYER_QUALITY` | `true` | `main.py:63` | Toggle quality gate |
| `WORKER_MODE` | `in_process` | `main.py:67` | Worker execution mode |
| `WORKER_CONCURRENCY` | `1` | `main.py:68` | Max concurrent jobs (capped at 10) |
| `LITELLM_PROXY_URL` | (optional) | `packages/agents/` | LiteLLM proxy for production |
| `LLM_BASE_URL` | (optional) | `packages/agents/` | 9Router sidecar URL |

### Background tasks (started in lifespan)

| Task | File:line | Interval | Purpose |
|------|-----------|----------|---------|
| `_run_teaching_pack_worker` | `main.py:92` | Continuous (1s idle sleep) | Poll and execute queued jobs |
| `_run_teaching_pack_sweeper` | `main.py:79` | 60s | Requeue stuck jobs, escalate expired gates, reconcile units |

## Notes / discrepancies vs existing docs

1. **Legacy `/run` routes coexist with `/teaching-packs` routes.** The legacy routes (`runs.py`, `artifacts.py`, `approvals.py`, `snapshots.py`) use an in-memory `app.state.runs` dict and are mostly decommissioned (POST creation returns 410, approval endpoints return 410). The teaching-pack routes are the authoritative path, backed by PostgreSQL via SQLAlchemy.

2. **Port discrepancy documented correctly.** Local dev = `:8101` (Makefile), Docker = `:8001` (compose). This is intentional per AGENTS.md §11.

3. **Auth is demo-quality.** `auth_router.py:11-24` uses a hardcoded `DEMO_USERS` dict with placeholder passwords. Real auth (bcrypt, DB lookup) is TODO.

4. **Teaching session live routes use session-token auth, not JWT.** `teaching_session_live.py` is exempted from `JWTMiddleware` via `PUBLIC_PREFIXES` — these routes gate on session-role tokens instead.

5. **Quality gate is optional.** `main.py:62-63` checks `OMC_ENABLE_SIX_LAYER_QUALITY` env var; the quality gate is wired as `None` when disabled.

6. **123+ files in the gateway module.** This is the largest service module in the codebase. The `teaching_session/` sub-package, `webhooks/` sub-package, and `observability/` sub-package add significant internal structure.

7. **`cost_logs` table is in schema `litellm`**, not `public`. This is the only table in a non-public schema.

8. **Recursive teacher-only leakage guard added (#463).** `teaching_pack_snapshot_validators.py` now exposes `teacher_only_value_paths(value)`, a recursive scan for the answer-bearing key set (`answer`, `answer_set`, `accepted_answers`, `correct_option_ids`, `explain`, `rationale`, `wrong_reasons`, `rubric_solution`) anywhere in a JSON value. It's enforced at two write seams: `TeachingPackSnapshotStore.create_snapshot` (`teaching_pack_snapshot_store.py:87-89`, raises `AnswerKeyLeakageError`) and `FileSystemTeachingPackExportWriter.export` (`teaching_pack_export_writer.py:58-64`, raises `ExportAdapterError`) — the property-test-style boundary #463's scope calls for, applied at the two points student-facing bytes actually leave the system rather than only at the V2 `ArtifactDocument` construction seam (see `contracts.md`'s `artifact_projection_mapper.py` entry for the construction-time half of the same guarantee).

9. **Canonical grade-band/curriculum resolution (#462).** `run_contract_setup.py` now resolves `RunContract.grade_band` via `common.contracts.grade_band.grade_band_for_label` (rejecting ambiguous input as an `unsupported` field instead of guessing, `run_contract_setup.py:76-78`) and `RunContract.curriculum_framework` via `common.contracts.education_policy.curriculum_framework_for`, replacing the previous `f"Grade {class_info['grade']}"` string-interpolation fallback.

---
_Traced from source on 2026-07-11. Files examined in depth: `main.py`, `routers/` (all 17 router files), `teaching_pack_executor.py`, `teaching_pack_worker.py`, `models.py`, `teaching_pack_models.py`, `teaching_pack_quality_gate.py`, `quality_gates.py`, `quality_workflow.py`, `auth/` (all 5 files). 123 total files in module._
