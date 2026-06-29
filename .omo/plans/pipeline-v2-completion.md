# pipeline-v2-completion - Work Plan

## TL;DR

Goal: finish Pipeline V2 on the active `/teaching-packs/*` surface, not the stale `pipeline_v2_*` names from the older gap report.

Current truth:
- Active gateway routes: `services/gateway/routers/teaching_pack_runs.py`, `teaching_pack_previews.py`, `teaching_pack_stream.py`, `teaching_pack_lifecycle.py`.
- Active graph: `packages/agents/teaching_pack/graph.py` + `nodes.py`.
- Active persistence: `services/gateway/teaching_pack_*` models/stores/jobs/snapshots.
- The old `packages/agents/pipeline_v2` and `services/gateway/pipeline_v2_*` files referenced by the 2026-06-27 gap report are not present in this current tree.

Definition of complete:
- All `.scratch/pipeline-v2/ISSUE-001` through `ISSUE-015` requirements are either implemented on the active surface or explicitly superseded by a documented active-surface equivalent.
- Live 9Router release matrix in ISSUE-011 has run ids, snapshot ids, exported HTML files, and evidence under `.scratch/pipeline-v2/artifacts/`.
- No `<promise>DONE</promise>` until full flow passes through the public HTTP/UI surface and artifacts exist on disk.

## Ordered Work

- [ ] 1. Reconcile docs to active surface
  - Update Pipeline V2 evidence/index notes so requirements refer to `teaching_pack_*`, not absent `pipeline_v2_*` modules.
  - Acceptance: grep/search shows no current completion plan asks implementers to edit absent `pipeline_v2_*` files.

- [ ] 2. Active graph: replace deterministic placeholder content with real stage adapters
  - Files: `packages/agents/teaching_pack/nodes.py`, service adapter seam as needed.
  - Progress: `planning_blueprint`, `post_blueprint_research`, and `artifact_workflow` now delegate to existing planner, researcher, and content creator seams.
  - Must preserve `packages/agents` boundary: no imports from `services/*` inside packages.
  - Acceptance: graph produces artifacts from real generation adapter or fails closed with typed metadata; no placeholder success.

- [x] 3. Renderer snapshot integration
  - Files: `packages/agents/teaching_pack/snapshots.py`, `services/gateway/artifact_snapshot_service.py`, `renderer_adapter.py`, completion recorder.
  - Acceptance: snapshots use renderer adapter/Eta path or documented equivalent; student preview redacts teacher-only content; teacher preview can include answer keys intentionally.

- [x] 4. Content approval payload and resume semantics
  - Files: `teaching_pack_runs.py`, `teaching_pack_executor.py`, `teaching_pack_worker.py`, graph teacher approval node.
  - Acceptance: teacher action payload is persisted, passed via `Command(resume=...)`, and export uses exactly approved snapshot ids.

- [ ] 5. Artifact workflow parity
  - Implement bounded artifact workflow status, retries, validation, and event visibility on active surface.
  - Acceptance: one artifact failure preserves passed artifacts; malformed JSON retry is artifact-scoped; unsupported artifacts fail before generation.

- [ ] 6. Quality/healing/safety
  - Wire deterministic gates before approval; add healing executors for schema, answer-key, PII, presentation, factual uncertainty, pedagogical mismatch, timeout.
  - Progress: deterministic schema/placeholder/answer-key/accessibility gates now run in the active graph before content approval.
  - Progress: pack-level coherence now runs in the active graph before content approval. `packages/agents/teaching_pack/quality.py` blocks a quiz that does not share lesson terms with the lesson, and `packages/agents/tests/teaching_pack/test_nodes.py` covers the mismatch regression.
  - Progress: active Teaching Pack node responsibilities were split so `nodes.py` is back under the 250 pure-LOC ceiling; quality checks and scoped-regeneration helpers live in focused modules.
  - Progress: pack coherence now also blocks objective drift, lesson vocabulary drift for quiz/worksheet, and Vietnamese quiz difficulty distribution mismatch when metadata signals are present.
  - Progress: factual uncertainty and pedagogical mismatch are explicit typed quality failure classes with deterministic healing routes: research enrichment and blueprint replan.
  - Progress: active graph render-quality now routes pack-coherence failures before teacher approval: objective drift and Vietnamese difficulty mismatch return to `planning_blueprint`, factual uncertainty returns to `post_blueprint_research`, and artifact-local coherence drift returns to `artifact_workflow`.
  - Evidence: `uv run pytest services/gateway/tests/test_quality_gates.py services/gateway/tests/test_healing_executors.py common/contracts/tests/test_quality.py -q` → 15 passed; focused Teaching Pack suite → 105 passed; focused graph/node/quality smoke after test split → 44 passed; broader focused quality/security suite → 132 passed; manual `_render_quality` driver accepted a good pack, routed objective drift to `planning_blueprint`, and routed vocabulary drift to `artifact_workflow`; Oracle ISSUE-009 focused review returned PASS.
  - Residual: persisted end-to-end self-healing orchestration for every recovery branch is deferred to the full Pipeline V2 healing-orchestration slice.
  - Acceptance: hard blocks fail without LLM spend; healing attempts bounded and persisted.

- [ ] 7. Research and transport live proof
  - Run/live-proof research search/fetch and adaptive LLM transport against 9Router on configured port.
  - Progress: active Researcher now compacts fetched 4omc.fetch pages into bounded `excerpt` fields before LLM synthesis; raw fetched `content` is not placed in the prompt payload.
  - Progress: adaptive transport policy now selects strict JSON strategy explicitly from request/capability tags (`native_schema`, `json_object`, `prompt_json`, `text_extract`) and records the chosen strategy in trace metadata.
  - Evidence: `uv run pytest packages/agents/tests/sub_agents/test_researcher.py packages/agents/tests/sub_agents/test_researcher_evidence.py -q` → 21 passed; broader Teaching Pack/research regression slice → 180 passed after clearing only stale test-prefixed DB rows.
  - Evidence: `uv run pytest packages/agents/tests/llm/test_transport_policy.py packages/agents/tests/llm/test_json_strategy_policy.py packages/agents/tests/sub_agents/test_researcher.py packages/agents/tests/sub_agents/test_researcher_evidence.py -q` → 35 passed.
  - Evidence: broader LLM/Teaching Pack regression slice including transport, researcher, Teaching Pack gateway, and E2E deterministic/scenario tests → 206 passed.
  - Acceptance: live Vietnamese Math, English ESL, Science citation scenarios produce compact cited briefs and transport metadata.

- [ ] 8. UI/UX cutover and SSE live streaming
  - Files under `apps/web` and gateway streaming route.
  - Progress: gateway status SSE now uses an in-process committed-event wake-up signal with replay fallback; focused stream tests cover replay, event-bus wake, and generator receipt of a committed visible event without reconnect.
  - Evidence: `uv run pytest services/gateway/tests/test_teaching_pack_runs_router.py services/gateway/tests/test_teaching_pack_stream_router.py -q` → 8 passed; broader Teaching Pack regression slice → 171 passed.
  - Acceptance: EventSource reconnect/replay, gate shell structured views, preview student/teacher toggle, loading/error states, browser QA screenshots.

- [ ] 9. Auth/governance/ops/admin/prompt governance completion
  - Cover ISSUE-012..015 gaps: schema adapters, generated type drift enforcement, DB budget persistence, queue/delayed status, admin list/filter, notification emitters, prompt compiler/evals/rubrics.
  - Acceptance: tests and evidence for each issue edge case.

- [x] 9a. Focused Teaching Pack security review blockers
  - Closed broad `auth-token` cookie fallback by keeping default `get_current_user` header-only and adding a dedicated status-stream dependency for EventSource cookie auth.
  - Restricted middleware cookie fallback to exact `/teaching-packs/run/{run_id}/status` and `/teaching-packs/runs/{run_id}/status` paths.
  - Closed contract-edit mass assignment by allowlisting teacher-editable contract fields in `services/gateway/teaching_pack_contract_edits.py`.
  - Evidence: focused auth/contract/stream suite → 31 passed; broader focused suite → 102 passed; fresh gateway HTTP smoke proved non-SSE cookie-only create returns 401 while status-stream cookie auth reaches ownership check; Oracle security review returned PASS.

- [ ] 10. Full release matrix and final artifacts
  - Run ISSUE-011 live matrix through public surface with real Postgres + real 9Router.
  - Progress: one fresh active-surface Vietnamese Math live probe completed through `/teaching-packs/*` using real 9Router `4omc`, persisted content approval, approved snapshots, and filesystem HTML exports.
  - Progress: fresh English ESL and Science citation/research scenarios also completed through `/teaching-packs/*` after renderer answer-leakage and long-topic contract setup fixes.
  - Evidence: `.scratch/pipeline-v2/artifacts/live-v2-preview-export-evidence-2026-06-28.md`.
  - Edge-case evidence: `.scratch/pipeline-v2/artifacts/live-v2-edge-cases-2026-06-28.json`.
  - Soft-delete evidence: `.scratch/pipeline-v2/artifacts/live-v2-soft-delete-2026-06-28.json`.
  - Notification evidence: `.scratch/pipeline-v2/artifacts/live-v2-notification-gap-2026-06-28.json` and `.scratch/pipeline-v2/artifacts/live-v2-notification-fixed-2026-06-28.json`.
  - Run evidence: `f8dc8f4b-e472-4236-96e0-cd898ee06902`; snapshots `snap-db028626ef2e15f265a7b15b`, `snap-87a62e4d9b36bc265585da82`; exports under `.scratch/pipeline-v2/artifacts/exports/f8dc8f4b-e472-4236-96e0-cd898ee06902/`.
  - ESL run evidence: `e66ae203-967e-4bc2-b051-6cd51e96cc22`; snapshots `snap-7e08f181e7b62f8671acaabe`, `snap-4cce99650dde4591c7c48024`, `snap-257c34a0f1e41f0c05399032`; exports under `.scratch/pipeline-v2/artifacts/exports/e66ae203-967e-4bc2-b051-6cd51e96cc22/`.
  - Science run evidence: `212d4666-5c3c-4197-96f2-48cedbdd5494`; snapshots `snap-44c83a3bf371406ed89a7a9c`, `snap-a8703926a08a3794534b2211`, `snap-e50cd91a144576e4954c914a`; exports under `.scratch/pipeline-v2/artifacts/exports/212d4666-5c3c-4197-96f2-48cedbdd5494/`.
  - Preview/export invariants verified for all three runs: doctype present, `oh-my-class` present, no external asset URLs, no student answer-key leakage.
  - Additional edge-case proof: `LIVE_V2_EDGE_CASES_ffa5e4d8-374c-4764-bab8-4804a837d068` covered missing-field clarification, teacher-scoped create idempotency, non-owner status/cancel denial, and owner cancellation cleanup through public HTTP routes. Probe runs `d3d73bf2-ee46-44c1-853d-d12ee8cee3e8` and `7e4a7f3c-1de8-4af3-92e7-ccd73c39f438` ended `cancelled` after cleanup.
  - Soft-delete proof: `LIVE_V2_SOFT_DELETE_2596fea2-f41e-441b-98e7-5433cf1a3e50` covered access revocation after deletion through public HTTP. Run `18e449be-f48d-469d-922b-9504355bc650` was hidden from status/resume after deletion, restored for cleanup, then cancelled.
  - Notification proof: `LIVE_V2_NOTIFICATION_GAP_CHECK` first proved active setup gates did not emit `/notifications` rows. After wiring gated run creation to the in-app notification helper, `LIVE_V2_NOTIFICATION_FIXED_CHECK` proved run `93e69793-a910-4ab2-b165-a403468cf37c` emitted one owned `clarification_required` notification and was cleaned up by cancellation.
  - Scoped rejection proof: `LIVE_V2_SCOPED_REJECTION_FRESH_SCHEMAFIX` covered first content approval, scoped quiz rejection, second content approval, accepted lesson preservation, regenerated quiz approval, and final HTML export through public HTTP. Run `7b1bd4ab-388f-41dc-b68c-31ebc9b88bb7` completed with exports under `.scratch/pipeline-v2/artifacts/exports/7b1bd4ab-388f-41dc-b68c-31ebc9b88bb7/`.
  - Scoped proof fixed a gate-history schema bug: `gate_interrupts` now uses partial unique index `uq_gate_interrupts_active` so multiple historical `responded` content gates are allowed while duplicate active gates are still blocked.
  - Search-plan confirmation proof: `LIVE_V2_SEARCH_PLAN_CONFIRMATION_EDIT` covered contract confirmation, teacher contract edit leaving curriculum unset, `search_plan_confirmation` gate opening with query/reason payload, search-plan approval through public resume, and start-job creation. Run `0582f23d-61c6-4b3a-8f3c-b18d893242b0`; evidence in `.scratch/pipeline-v2/artifacts/live-v2-search-plan-confirmation-2026-06-29.json`.
  - No-long-request timing proof: `LIVE_V2_NO_LONG_REQUEST_d35dc0a0-e8ee-43cd-9ff2-44a1c08bc765` covered public create/resume timing. Run `4fa1b299-79d4-4c38-a29d-e517209e2556` returned first create `202` in `0.1088s` with `job_id: null` at the clarification gate, duplicate create `202` in `0.0055s` reusing the same run, and clarification resume `202` in `0.0119s` with a queued resume job; evidence in `.scratch/pipeline-v2/artifacts/live-v2-no-long-request-2026-06-29.json`.
  - Langfuse-unavailable proof: `LIVE_V2_LANGFUSE_UNAVAILABLE_b7336fdb-d0f2-4c72-807f-4723a55f95c9` covered public create behavior while Langfuse env was configured to an unreachable host. Run `9e16199e-d273-4eee-95ab-ff1c0993ee23` returned `202`, persisted the run, reached `clarification_required`, and cleaned up by public cancellation; evidence in `.scratch/pipeline-v2/artifacts/live-v2-langfuse-unavailable-2026-06-29.json`.
  - Worker restart/lease-expiry proof: `LIVE_V2_WORKER_LEASE_dfeaf67d-071c-4f60-b66d-1e194a896430` covered public-created run state plus simulated stale running-job reclaim. Run `ab97408f-8e2c-4399-a1ec-a2096c39201a` stopped at `clarification_required`; simulated job `job-lease-proof-afb3c504-1bb1-4815-9227-c416f792314f` was reclaimed by `simulated-restarted-worker`, attempts incremented from `1` to `2`, and cleanup cancellation succeeded; evidence in `.scratch/pipeline-v2/artifacts/live-v2-worker-lease-2026-06-29.json`.
  - UI/generated-client/SSE proof: `LIVE_V2_UI_BROWSER_9cdc4645-3c2b-4996-83ca-573756d41fae` covered the production web app against active `/teaching-packs/*` routes. Browser-created run `584ae7e8-4bea-425e-92b4-67f9b6c6bf40` loaded Teaching Pack JSON status, replayed `teaching_pack.clarification_required.opened` into the UI through EventSource cookie auth, submitted clarification with `action: answer`, persisted the gate response, and cleaned up by public cancellation; evidence in `.scratch/pipeline-v2/artifacts/live-v2-ui-sse-compat-2026-06-29.json`.
  - Timeout/malformed-JSON review: deterministic coverage confirms active per-artifact retry/fail-closed behavior in `content_creator_node` and worker/executor failure persistence; evidence in `.scratch/pipeline-v2/artifacts/live-v2-timeout-malformed-json-review-2026-06-29.json`.
  - Timeout/malformed fault proof: `.scratch/pipeline-v2/artifacts/live-v2-timeout-malformed-fault-2026-06-29.json` covers public `/teaching-packs/runs` job creation plus active `TeachingPackWorker`/`TeachingPackExecutor` fail-closed behavior under an injected timeout. Run `5f14175b-7304-4d50-8a4a-7e1e73664474` failed closed, job `job-91bd8657-5896-4418-bff9-f2a781fb276b` was marked `failed`, and failure/status events persisted the timeout summary. Active content-creator regression now also covers timeout retry/recovery scoped to the target artifact alongside existing malformed-JSON retry/recovery.
  - ISSUE-011 active-surface live release gates are covered. Remaining full-Pipeline V2 blockers are outside ISSUE-011: persisted recovery orchestration beyond the active graph routing seam, broader UI/UX cutover QA, auth/governance/versioning, ops/admin recovery, prompt/rubric governance, and final consolidated release report.
  - Acceptance: evidence report under `.scratch/pipeline-v2/artifacts/`, exported HTML artifacts on disk, no external assets, no answer-key leakage in student previews.

## First active slice

Start with item 4/3 intersection because it is small and production-critical: lock exact approved snapshot export behavior and then wire real snapshot rendering/persistence behind content approval.
