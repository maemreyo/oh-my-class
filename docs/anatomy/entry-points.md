# Entry Points: oh-my-class

Every HTTP route, CLI command, background worker, and scheduled job in the system.

## HTTP Routes (Gateway — FastAPI :8001 Docker / :8101 local dev)

| Method | Path | Module | Handler | Purpose |
|--------|------|--------|---------|---------|
| POST | `/teaching-packs/runs` | `gateway` | `create_teaching_pack_run` | Create a new teaching pack run (202) |
| POST | `/teaching-packs/runs/{run_id}/resume` | `gateway` | `resume_teaching_pack_run` | Resume gated run (teacher decision) |
| POST | `/teaching-packs/runs/{run_id}/artifacts/{artifact_id}/request-revision` | `gateway` | `request_artifact_revision` | Scoped artifact revision (202) |
| GET | `/teaching-packs/runs/{run_id}` | `gateway` | `get_teaching_pack_run` | Get run status + pending gate |
| GET | `/teaching-packs/runs/{run_id}/status` | `gateway` | `stream_teaching_pack_status` | SSE stream of run events |
| POST | `/teaching-packs/runs/{run_id}/cancel` | `gateway` | `cancel_teaching_pack_run` | Cancel a run |
| DELETE | `/teaching-packs/runs/{run_id}` | `gateway` | `delete_teaching_pack_run` | Soft-delete a run |
| POST | `/teaching-packs/runs/{run_id}/restore` | `gateway` | `restore_teaching_pack_run` | Restore a soft-deleted run |
| GET | `/teaching-packs/runs/{run_id}/snapshots/{snapshot_id}/preview` | `gateway` | `preview_rendered_snapshot` | Rendered HTML preview |
| POST | `/teaching-packs/runs/{run_id}/approved-snapshots` | `gateway` | `approve_rendered_snapshots` | Approve snapshots |
| PATCH | `/teaching-packs/runs/{run_id}/snapshots/{snapshot_id}/blocks/{block_id}` | `gateway` | `edit_slide_deck_snapshot_block` | Edit slide deck block |
| POST | `/teaching-packs/runs/{run_id}/snapshots/{snapshot_id}/blocks/{block_id}/rewrite-suggestion` | `gateway` | `suggest_slide_deck_block_rewrite` | AI-assisted block rewrite |
| GET | `/teaching-packs/runs/{run_id}/snapshots/{snapshot_id}/translate` | `gateway` | `translate_slide_deck_snapshot` | Translate slide deck |
| GET | `/teaching-packs/runs/{run_id}/artifacts/{artifact_id}/versions` | `gateway` | `list_artifact_versions` | Version history |
| POST | `/teaching-packs/runs/{run_id}/artifacts/{artifact_id}/versions/{id}/restore` | `gateway` | `restore_artifact_version` | Restore previous version |
| GET | `/teaching-packs/runs/{run_id}/exports` | `gateway` | `list_exports` | Export records |
| GET | `/teaching-packs/runs/{run_id}/artifacts/{artifact_id}/export-status` | `gateway` | `get_export_status` | Staleness check |
| GET | `/teaching-packs/runs/{run_id}/evidence` | `gateway` | `get_run_evidence` | Release evidence |
| GET | `/teaching-packs/units/{parent_run_id}` | `gateway` | `get_unit_view` | Unit view with session progress |
| GET | `/teaching-packs/units/{parent_run_id}/status` | `gateway` | `stream_unit_status` | Unit SSE stream |
| POST | `/teaching-packs/units/{parent_run_id}/approve-all` | `gateway` | `approve_all_sessions` | Bulk approve |
| POST | `/teaching-packs/units/{parent_run_id}/sessions/{id}/spawn-anyway` | `gateway` | `spawn_anyway` | Force-spawn session |
| POST | `/teaching-packs/units/{parent_run_id}/export` | `gateway` | `export_unit` | Queue unit packaging |
| POST | `/teaching-sessions/{session_id}/slide` | `gateway` | `advance_slide` | Teacher advances slide |
| POST | `/teaching-sessions/{session_id}/branch` | `gateway` | `select_branch` | Teacher selects branch |
| GET | `/teaching-sessions/{session_id}/branches` | `gateway` | `get_precomputed_branches` | Precomputed branch options |
| POST | `/teaching-sessions/{session_id}/branch-suggestions` | `gateway` | `suggest_branch_content` | AI branch suggestion |
| POST | `/teaching-sessions/{session_id}/branch-suggestions/apply` | `gateway` | `apply_branch_suggestion` | Apply AI suggestion |
| POST | `/teaching-sessions/{session_id}/responses` | `gateway` | `submit_response` | Student response |
| GET | `/teaching-sessions/{session_id}/state` | `gateway` | `get_current_state` | Session state (reconnect) |
| GET | `/teaching-sessions/{session_id}/stream` | `gateway` | `stream_session_events` | SSE broadcast |
| POST | `/auth/login` | `gateway` | `login` | JWT authentication |
| GET | `/auth/me` | `gateway` | `get_me` | Current user |
| GET | `/health` | `gateway` | `health_check` | Load balancer |
| GET | `/ops/slo` | `gateway` | `get_slo_snapshot` | SLO metrics (admin) |
| POST | `/webhook/notify` | `gateway` | `send_notification` | Gate notification dispatch |
| POST | `/webhook/telegram` | `gateway` | `telegram_webhook` | Telegram bot ingress |
| POST | `/webhook/zalo` | `gateway` | `zalo_webhook` | Zalo webhook ingress |
| POST | `/webhook/error` | `gateway` | `frontend_error` | Frontend error ingestion |
| POST | `/media-assets` | `gateway` | `upload_media_asset` | Upload image/diagram |
| GET | `/media-assets` | `gateway` | `list_media_assets` | List assets |
| GET | `/media-assets/{id}/file` | `gateway` | `get_media_asset_file` | Retrieve asset |
| POST | `/media-assets/{id}/generate-alt-text` | `gateway` | `generate_media_asset_alt_text` | AI alt text |
| PUT | `/media-assets/{id}/alt-text` | `gateway` | `set_media_asset_alt_text` | Persist alt text |
| GET | `/notifications` | `gateway` | `list_notifications` | Teacher notifications |
| POST | `/notifications/{id}/read` | `gateway` | `read_notification` | Mark as read |
| POST | `/notifications/{id}/dismiss` | `gateway` | `dismiss` | Dismiss channel |
| GET | `/notifications/admin/runs` | `gateway` | `list_admin_runs` | Admin run management |
| POST | `/notifications/admin/runs/{id}/recover` | `gateway` | `recover_run` | Admin recovery |

## CLI Commands

| Command | Module | Purpose |
|---------|--------|---------|
| `pnpm --filter @oh-my-class/renderer dist/cli.js` | `renderer` | Artifacts to HTML via stdin/stdout JSON |
| `pnpm --filter @oh-my-class/exporters dist/cli.js` | `exporters` | Artifacts to GIFT/H5P/Anki/TSV via stdin/stdout JSON |
| `pnpm --filter @oh-my-class/exporters dist/vocabulary-batch/cli.js` | `exporters` | Vocabulary batch ZIP via stdin/stdout JSON |

## Background Workers

| Worker | Module | Schedule | Purpose |
|--------|--------|----------|---------|
| `TeachingPackWorker` | `gateway` | Continuous (1s idle sleep) | Lease-based job polling → LangGraph graph execution |
| `Recovery Sweeper` | `gateway` | Every 60s | Stuck job reclaim, gate timeout escalation (24h), unit reconciliation |
| `langfuse-worker` | `infra` | Always-on (Docker service) | Langfuse trace processing |

## Startup Sequence (lifespan)

1. Configure logging (JSON, INFO)
2. Validate production secrets
3. Create SQLAlchemy async engine + session factory
4. Initialize LangGraph checkpointer (MemorySaver/SqliteSaver/PostgresSaver by env)
5. Open teaching pack store (Postgres-backed for staging/prod, in-memory for dev)
6. Build `build_teaching_pack_graph(checkpointer, store, quality_gate)`
7. Start sweeper background task
8. Start worker background task (in_process mode)
