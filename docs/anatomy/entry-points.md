# Entry Points

**Generated:** 2026-07-11 · **Mode:** full trace

All external-facing interfaces across the system: HTTP routes, SSE streams, CLI commands, frontend pages, and background tasks.

---

## HTTP Routes (gateway)

Gateway runs on **`:8101`** in local dev (Makefile) and **`:8001`** in Docker (compose).

### Health

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| GET | `/health` | `main.py:264` `health_check` | Load balancer probe |

### Auth (prefix `/auth`)

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| POST | `/auth/login` | `routers/auth_router.py:28` `login` | Returns JWT (demo users) |
| GET | `/auth/me` | `routers/auth_router.py:41` `get_me` | Placeholder (returns 401) |

### Teaching Pack Runs (prefix `/teaching-packs`)

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| POST | `/teaching-packs/run` | `routers/teaching_pack_runs.py:77` `create_teaching_pack_run` | Create a new run (202 Accepted) |
| POST | `/teaching-packs/runs` | same | Dual path alias |
| POST | `/teaching-packs/run/{run_id}/resume` | `routers/teaching_pack_runs.py:148` `resume_teaching_pack_run` | Resume after HITL gate |
| POST | `/teaching-packs/runs/{run_id}/resume` | same | Dual path alias |
| POST | `/teaching-packs/runs/{run_id}/artifacts/{artifact_id}/request-revision` | `routers/teaching_pack_runs.py:286` `request_artifact_revision` | Scoped revision |
| GET | `/teaching-packs/run/{run_id}` | `routers/teaching_pack_lifecycle.py:43` `get_teaching_pack_run` | Run status + pending gate |
| POST | `/teaching-packs/run/{run_id}/cancel` | `routers/teaching_pack_lifecycle.py:94` `cancel_teaching_pack_run` | Cancel a running job |
| DELETE | `/teaching-packs/run/{run_id}` | `routers/teaching_pack_lifecycle.py:138` `delete_teaching_pack_run` | Soft delete |
| POST | `/teaching-packs/run/{run_id}/restore` | `routers/teaching_pack_lifecycle.py:170` `restore_teaching_pack_run` | Restore soft-deleted run |

### Teaching Pack Snapshots & Preview (prefix `/teaching-packs`)

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| GET | `/teaching-packs/run/{run_id}/snapshots/{snapshot_id}` | `routers/teaching_pack_previews.py:87` `get_rendered_snapshot_metadata` | Metadata only |
| GET | `/teaching-packs/run/{run_id}/snapshots/{snapshot_id}/preview` | `routers/teaching_pack_previews.py:102` `preview_rendered_snapshot` | Student/teacher/print HTML |
| POST | `/teaching-packs/run/{run_id}/approved-snapshots` | `routers/teaching_pack_previews.py:171` `approve_rendered_snapshots` | Batch approve |
| POST | `/teaching-packs/run/{run_id}/snapshots/{snapshot_id}/translate` | `routers/teaching_pack_previews.py:216` `translate_slide_deck_snapshot` | SDX-01 translation |
| PATCH | `/teaching-packs/run/{run_id}/snapshots/{snapshot_id}/blocks/{block_id}` | `routers/teaching_pack_previews.py:277` `edit_slide_deck_snapshot_block` | SDE-04 scoped edit |
| POST | `.../blocks/{block_id}/rewrite-suggestion` | `routers/teaching_pack_previews.py:431` `suggest_slide_deck_block_rewrite` | SDE-08 AI rewrite |
| POST | `.../blocks/{block_id}/rewrite-suggestion/cancelled` | `routers/teaching_pack_previews.py:521` `cancel_slide_deck_block_rewrite_suggestion` | Observability ping |

### Teaching Pack Artifact Versions (prefix `/teaching-packs`)

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| GET | `/teaching-packs/run/{run_id}/artifacts/{artifact_id}/versions` | `routers/teaching_pack_previews.py:563` `list_artifact_versions` | SDE-05 version history |
| POST | `.../versions/{version_snapshot_id}/restore` | `routers/teaching_pack_previews.py:617` `restore_artifact_version` | SDE-05 restore |

### Teaching Pack Exports (prefix `/teaching-packs`)

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| GET | `/teaching-packs/run/{run_id}/exports` | `routers/exports.py:109` `list_exports` | DB-backed export records |
| GET | `.../artifacts/{artifact_id}/export-status` | `routers/exports.py:136` `get_export_status` | Staleness check |
| GET | `.../artifacts/{artifact_id}/export-status/by-format` | `routers/exports.py:169` `get_export_status_by_format` | Per-format staleness |
| POST | `.../artifacts/{artifact_id}/exports/regenerate` | `routers/exports.py:214` `regenerate_exports` | Teacher-triggered re-export |
| POST | `/teaching-packs/run/{run_id}/exports/teaching-pack` | `routers/exports.py:284` `export_teaching_pack_bundle` | Bundle all artifacts into one HTML |

### Teaching Briefs (prefix `/teaching-packs`)

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| POST | `/teaching-packs/briefs` | `routers/teaching_briefs.py:52` `create_teaching_brief` | Create brief (201) |
| GET | `/teaching-packs/briefs/{brief_id}` | `routers/teaching_briefs.py:67` `get_teaching_brief` | Fetch brief |
| PUT | `/teaching-packs/briefs/{brief_id}` | `routers/teaching_briefs.py:76` `autosave_teaching_brief` | Autosave |
| GET | `/teaching-packs/briefs/{brief_id}/contract-preview` | `routers/teaching_briefs.py:90` `preview_teaching_brief_contract` | Preview contract |
| POST | `/teaching-packs/briefs/{brief_id}/launch` | `routers/teaching_briefs.py:124` `launch_teaching_brief` | Launch run (202 Accepted) |

### Artifact Documents V2 (prefix `/teaching-packs`)

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| GET | `.../runs/{run_id}/artifacts/{artifact_id}/versions` | `routers/artifact_documents.py:179` `list_artifact_document_versions` | V2 version list |
| POST | `.../artifacts/{artifact_id}/edit` | `routers/artifact_documents.py:200` `edit_artifact_document_route` | Registry-driven edit |
| POST | `.../artifacts/{artifact_id}/restore` | `routers/artifact_documents.py:234` `restore_artifact_document_route` | Restore version |
| POST | `.../artifacts/{artifact_id}/translate` | `routers/artifact_documents.py:266` `create_language_version_route` | Source-linked lineage |
| POST | `.../artifacts/{artifact_id}/variants` | `routers/artifact_documents.py:303` `create_content_variant_route` | Independently approvable |
| POST | `.../artifacts/{artifact_id}/rewrite-proposal` | `routers/artifact_documents.py:334` `propose_artifact_block_rewrite` | Ephemeral AI proposal |
| POST | `.../artifacts/{artifact_id}/notes` | `routers/artifact_documents.py:390` `create_review_note` | Create review note (201) |
| GET | `.../artifacts/{artifact_id}/notes` | `routers/artifact_documents.py:415` `list_review_notes` | List review notes |
| POST | `.../notes/{note_id}/resolve` | `routers/artifact_documents.py:427` `resolve_review_note` | Resolve note |
| POST | `.../artifacts/{artifact_id}/approve` | `routers/artifact_documents.py:441` `approve_artifact` | Approve (204 No Content) |
| POST | `.../approve-all-current` | `routers/artifact_documents.py:472` `approve_all_current_route` | Bulk approve |
| POST | `.../artifacts/{artifact_id}/claim-evidence` | `routers/artifact_documents.py:494` `persist_claim_evidence` | Fail-closed (ADR-054) |
| GET | `.../versions/{version}/provenance` | `routers/artifact_documents.py:530` `get_decision_provenance` | Decision provenance |
| POST | `.../delegate` | `routers/artifact_documents.py:552` `delegate_reviewer` | Owner-only delegation |

### Content Briefs (prefix `/teaching-packs`)

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| POST | `.../runs/{run_id}/content-briefs` | `routers/content_briefs.py:78` `create_content_brief` | Create (201) |
| GET | `.../content-briefs/{content_brief_id}` | `routers/content_briefs.py:96` `get_content_brief` | Fetch |
| POST | `.../content-briefs/{id}/fill-failures` | `routers/content_briefs.py:113` `record_fill_failure` | Strategy review |
| POST | `.../content-briefs/{id}/strategy-change-requests` | `routers/content_briefs.py:133` `record_strategy_change_request` | Record change request |
| GET | `.../content-briefs/{id}/review` | `routers/content_briefs.py:156` `list_strategy_review` | List reviews |
| POST | `.../content-briefs/{id}/verify-compliance` | `routers/content_briefs.py:182` `verify_compliance` | Verify (204) |

### Source Collections (prefix `/teaching-packs`)

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| POST | `/teaching-packs/source-collections` | `routers/source_collections.py:54` `create_source_collection` | Create (201) |
| GET | `/teaching-packs/source-collections/{id}` | `routers/source_collections.py:71` `get_source_collection` | Fetch |
| POST | `.../source-collections/{id}/entries` | `routers/source_collections.py:89` `add_source_collection_entry` | Add entry (201) |

### Media Assets (prefix `/media-assets`)

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| POST | `/media-assets` | `routers/media_assets.py:77` `upload_media_asset` | Upload (10 MB limit) |
| GET | `/media-assets` | `routers/media_assets.py:113` `list_media_assets` | List |
| GET | `/media-assets/{asset_id}/file` | `routers/media_assets.py:125` `get_media_asset_file` | Binary download |
| POST | `/media-assets/{asset_id}/generate-alt-text` | `routers/media_assets.py:139` `generate_media_asset_alt_text` | SDX-04 alt text |
| PUT | `/media-assets/{asset_id}/alt-text` | `routers/media_assets.py:167` `set_media_asset_alt_text` | Set alt text |

### Media Asset Versions (prefix `/teaching-packs`)

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| POST | `/teaching-packs/media-asset-versions` | `routers/media_asset_versions.py:70` `create_media_asset_version` | Create (201, checksummed) |
| POST | `.../media-asset-versions/{id}/replace` | `routers/media_asset_versions.py:104` `replace_media_asset_version` | Replace (201) |
| GET | `.../media-asset-versions/{id}` | `routers/media_asset_versions.py:134` `get_media_asset_version` | Fetch |
| GET | `.../media-asset-versions/{id}/versions` | `routers/media_asset_versions.py:144` `list_media_asset_versions` | List versions |
| GET | `.../media-asset-versions/{id}/file` | `routers/media_asset_versions.py:155` `get_media_asset_version_file` | Verified checksum |
| DELETE | `.../media-asset-versions/{id}` | `routers/media_asset_versions.py:176` `delete_media_asset_version` | Delete (204) |
| POST | `.../media-asset-versions/{id}/dependencies` | `routers/media_asset_versions.py:200` `record_media_asset_dependency` | Record dependency (201) |
| POST | `.../visual-source-suggestions` | `routers/media_asset_versions.py:218` `create_visual_source_suggestion` | Create (201) |
| GET | `.../visual-source-suggestions` | `routers/media_asset_versions.py:239` `list_visual_source_suggestions` | List |
| POST | `.../visual-source-suggestions/{id}/convert` | `routers/media_asset_versions.py:253` `convert_visual_source_suggestion` | Convert to asset |
| POST | `.../visual-source-suggestions/{id}/dismiss` | `routers/media_asset_versions.py:283` `dismiss_visual_source_suggestion` | Dismiss |

### Slide Deck Live Publication (prefix `/teaching-packs`)

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| POST | `.../run/{run_id}/publish-to-live` | `routers/slide_deck_live_publication.py` | Publish approved deck to session |
| POST | `.../run/{run_id}/republish-to-live` | same | Re-pin to newer approved version |

### Release Evidence (prefix `/teaching-packs`)

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| GET | `.../run/{run_id}/evidence` | `routers/release_evidence.py` | Query audit records |
| POST | `.../run/{run_id}/evidence` | same | Generate + persist (admin) |
| GET | `/teaching-packs/release-evidence` | same | List recent (admin) |

### Units (prefix `/teaching-packs`)

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| GET | `.../units/{parent_run_id}` | `routers/unit_runs.py:97` `get_unit_view` | Unit aggregate view |
| GET | `.../units/{parent_run_id}/status` | `routers/unit_runs.py:176` `stream_unit_status` | Multiplexed SSE |
| POST | `.../units/{parent_run_id}/approve-all` | `routers/unit_runs.py:203` `approve_all_sessions` | Bulk approve |
| POST | `.../units/{parent_run_id}/sessions/{session_id}/spawn-anyway` | `routers/unit_runs.py:258` `spawn_anyway` | Force spawn |
| POST | `.../units/{parent_run_id}/export` | `routers/unit_runs.py:313` `export_unit` | Export all sessions |

### Webhooks (prefix `/webhook`)

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| POST | `/webhook/notify` | `routers/webhooks.py:66` `send_notification` | Dispatch to configured URLs |
| POST | `/webhook/telegram` | `routers/webhooks.py:92` `telegram_webhook` | Telegram bot updates (HMAC-SHA256) |
| POST | `/webhook/zalo` | `routers/webhooks.py:112` `zalo_webhook` | Zalo bot updates (shared secret) |
| POST | `/webhook/error` | `routers/webhooks.py:267` `frontend_error` | Client error reports |

### Notifications (prefix `/notifications`)

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| GET | `/notifications` | `routers/notifications.py:101` `list_notifications` | List |
| POST | `/notifications/{id}/read` | `routers/notifications.py:115` `read_notification` | Mark read |
| POST | `/notifications/{id}/dismiss` | `routers/notifications.py:133` `dismiss` | Dismiss |
| GET | `/notifications/admin/runs` | `routers/notifications.py:155` `list_admin_runs` | Admin: list runs |
| GET | `/notifications/admin/runs/{run_id}/summary` | `routers/notifications.py:219` `get_run_summary` | Admin: run summary |
| POST | `/notifications/admin/runs/{run_id}/recover` | `routers/notifications.py:246` `recover_run` | Admin: recover stuck run |

### Ops (prefix `/ops`)

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| GET | `/ops/slo` | `routers/ops.py:17` `get_slo_snapshot` | SLO snapshot (admin) |

### Teaching Session Live (prefix `/teaching-sessions`)

Session-token auth, not JWT. Exempted from `JWTMiddleware` via `PUBLIC_PREFIXES`.

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| POST | `/teaching-sessions/join` | `routers/teaching_session_live.py` | Token issuance |
| GET | `/teaching-sessions/{session_id}/stream` | same | SSE broadcast |
| GET | `/teaching-sessions/{session_id}/state` | same | Polling fallback |
| GET | `/teaching-sessions/{session_id}/content` | same | Current snapshot HTML |
| POST | `/teaching-sessions/{session_id}/slide` | same | Navigate slide |
| POST | `/teaching-sessions/{session_id}/responses` | same | Student response capture |
| POST | `/teaching-sessions/{session_id}/end` | same | End session |

### Legacy Run Routes (prefix `/run`) — mostly decommissioned

| Method | Path | Handler | Status |
|--------|------|---------|--------|
| GET | `/run` | `routers/runs.py:203` `list_runs` | Active (in-memory) |
| POST | `/run` | `routers/runs.py:222` `create_run` | **410 Gone** |
| GET | `/run/{run_id}` | `routers/runs.py:234` `get_run` | Active |
| GET | `/run/{run_id}/exports` | `routers/runs.py:300` `list_exports` | Active |
| GET | `/run/{run_id}/exports/{artifact_id}` | `routers/runs.py:330` `download_export` | Active |
| GET | `/run/{run_id}/artifacts` | `routers/artifacts.py:63` `list_artifacts` | Legacy, in-memory |
| GET | `/run/{run_id}/artifacts/{artifact_id}` | `routers/artifacts.py:82` `get_artifact` | Legacy, in-memory |
| POST | `/run/{run_id}/approve` | `routers/approvals.py:35` `approve` | **410 Gone** |
| POST | `/run/{run_id}/reject` | `routers/approvals.py:49` `reject` | **410 Gone** |
| POST | `/run/{run_id}/snapshots` | `routers/snapshots.py:62` `produce_snapshot` | Legacy |

---

## SSE Streams

| Endpoint | Module | Description |
|----------|--------|-------------|
| `GET /teaching-packs/run/{run_id}/status` | gateway | Pipeline events for a teaching pack run |
| `GET /run/{run_id}/status` | gateway (legacy) | Legacy run status stream |
| `GET /teaching-packs/units/{parent_run_id}/status` | gateway | Multiplexed unit progress events |
| `GET /teaching-sessions/{session_id}/stream` | gateway | Live classroom session events (Redis pub/sub) |

---

## CLI Commands

| Command | Module | Description |
|---------|--------|-------------|
| `node packages/renderer/dist/agent-renderer.js` | renderer (via agents) | Render ArtifactContent JSON from stdin to standalone HTML on stdout. Invoked by `nodes/finalize.py:28` as a subprocess. |
| `omc-render` (bin) | renderer | Alias for `agent-renderer.js`. CLI entry via `package.json` bin field. |

### Export CLI bridge (subprocess)

| Command | Module | Description |
|---------|--------|-------------|
| `node packages/exporters/dist/index.js` | exporters | CLI bridge invoked by `teaching_pack_export_writer.py` via subprocess. Reads `{ format, run_id, artifacts, output_dir }` from stdin, writes exported files to `output_dir`, returns `{ path }` on stdout. Handles: gift, h5p, qti, pptx, anki_apkg, flashcard_tsv. |
| `node packages/exporters/dist/vocabulary-batch/cli.js` | exporters | Vocabulary batch ZIP via stdin/stdout JSON. |

---

## Frontend Routes (web)

Next.js App Router at `apps/web/src/app/`.

### Dashboard routes (layout: `(dashboard)/layout.tsx`)

| Path | Component | Description |
|------|-----------|-------------|
| `/runs` | `(dashboard)/runs/page.tsx` | Runs list with client-side filtering |
| `/runs/new` | `(dashboard)/runs/new/page.tsx` | Teaching brief creator (TSP-01) |
| `/runs/[runId]` | `(dashboard)/runs/[runId]/page.tsx` | Run detail with gate shell + SSE status |
| `/units/[parentRunId]` | `(dashboard)/units/[parentRunId]/page.tsx` | Unit workspace with session cards |
| `/approvals` | `(dashboard)/approvals/page.tsx` | Pending approvals list |
| `/effectiveness` | `(dashboard)/effectiveness/page.tsx` | Effectiveness metrics |

### Editor routes (layout: `(deck-editor)/layout.tsx`)

| Path | Component | Description |
|------|-----------|-------------|
| `/runs/[runId]/decks/[deckId]/edit` | `(deck-editor)/runs/[runId]/decks/[deckId]/edit/page.tsx` | Full-screen slide deck editor (SDE-03) |

### Session routes

| Path | Component | Description |
|------|-----------|-------------|
| `/sessions/[sessionId]/cockpit` | `sessions/[sessionId]/cockpit/page.tsx` | Live teaching cockpit (role-gated via session token) |

### Error pages

| Path | Component | Description |
|------|-----------|-------------|
| `error.tsx` | `app/error.tsx` | Route-level error boundary |
| `global-error.tsx` | `app/global-error.tsx` | Root error boundary |
| `not-found.tsx` | `app/not-found.tsx` | 404 page |

---

## Preview Server (renderer)

| Endpoint | Module | Description |
|----------|--------|-------------|
| `GET /api/preview/:runId` | renderer | Express route mounted via `mountPreviewServer()`. Serves rendered artifact HTML from in-memory `PreviewStore` with TTL expiry. |

---

## Background Tasks (gateway lifespan)

| Task | File | Interval | Description |
|------|------|----------|-------------|
| Teaching Pack Worker | `main.py:92` `_run_teaching_pack_worker` | Continuous (1s idle sleep) | Polls `run_jobs` table via claim-lease pattern, dispatches to `TeachingPackExecutor` |
| Recovery Sweeper | `main.py:79` `_run_teaching_pack_sweeper` | 60s | Requeues stuck jobs, escalates expired gate interrupts, reconciles unit parent/child states |

---

## LangGraph Pipeline Entry Points (agents)

The teaching-pack pipeline is the sole graph entry. It is not invoked directly via HTTP. Instead, `TeachingPackExecutor` (gateway) calls `graph.ainvoke(state, config)` for new runs and `graph.ainvoke(Command(resume=...), config)` for gate resumptions.

| Entry | Module | Description |
|-------|--------|-------------|
| `build_teaching_pack_graph()` | agents | Constructs the compiled LangGraph StateGraph at gateway startup |
| `graph.ainvoke(state, config)` | agents (via gateway executor) | Invokes the 10-stage or 12-stage pipeline |
| `graph.ainvoke(Command(resume=...), config)` | agents (via gateway executor) | Resumes after HITL gate interrupt |

---

## Summary

| Type | Count |
|------|-------|
| Active HTTP routes (gateway) | ~85 |
| Legacy/decommissioned routes | ~10 |
| SSE stream endpoints | 4 |
| CLI commands | 3 (renderer + 2 exporter CLIs) |
| Frontend pages | 8 (6 dashboard + 1 editor + 1 cockpit) |
| Preview server routes | 1 |
| Background tasks | 2 |
| LangGraph pipeline entries | 1 (graph invocation via executor) |
