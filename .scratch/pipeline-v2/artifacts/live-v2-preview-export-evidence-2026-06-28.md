# Pipeline V2 live preview/export evidence — 2026-06-28

## Scope

Active public surface: `/teaching-packs/*` on isolated gateway `http://127.0.0.1:8101`.

Runtime config:

- `LLM_BASE_URL=http://localhost:20228/v1`
- `NINEROUTER_BASE_URL=http://localhost:20228/v1`
- `OMC_9ROUTER_BASE_URL=http://127.0.0.1:20228`
- planner/researcher/content-creator/reviewer model: `4omc`
- `MAX_TOKENS_CONTENT_CREATOR=32768`
- `JWT_SECRET=dev-test-secret-minimum-32-characters`

## Live run 1 — Vietnamese Math

- Marker: `LIVE_V2_PREVIEW_EXPORT_PROBE_7b14a363-c33c-4b14-933c-0b173ce726c8`
- Run ID: `f8dc8f4b-e472-4236-96e0-cd898ee06902`
- Teacher ID: `teacher-live-6ded04bf`
- Contract gate: `gate-fdc3faca-e80b-45df-bfc9-b2c4c6427233` → `responded`
- Content gate: `gate-eb47126a-261e-4f18-90a1-ac14c64771b8` → `responded`
- Start job: `job-d1f8b099-a2c0-47c8-80e5-495dfba13727` → `completed`, attempts `1`
- Resume job: `job-3458f66e-e353-46cc-9c9a-546e2f187348` → `completed`, attempts `1`
- Final run status: `COMPLETED`

## Snapshot preview checks — Vietnamese Math

Student preview invariants were checked before approval:

| Snapshot | Artifact | Type | Doctype | Brand | External assets | Answer-key leakage |
|---|---|---|---|---|---|---|
| `snap-db028626ef2e15f265a7b15b` | `lesson-1` | `lesson` | yes | yes | no | no |
| `snap-87a62e4d9b36bc265585da82` | `quiz-2` | `quiz` | yes | yes | no | no |

Both snapshots were approved through `POST /teaching-packs/runs/{run_id}/approved-snapshots`.

## Exported HTML — Vietnamese Math

Completed event `teaching_pack.run.completed` included exported files:

- `.scratch/pipeline-v2/artifacts/exports/f8dc8f4b-e472-4236-96e0-cd898ee06902/snap-db028626ef2e15f265a7b15b.html`
- `.scratch/pipeline-v2/artifacts/exports/f8dc8f4b-e472-4236-96e0-cd898ee06902/snap-87a62e4d9b36bc265585da82.html`

Filesystem verification of both exports:

- files exist
- contain `<!DOCTYPE html>`
- contain `oh-my-class`
- contain no `http://` or `https://` asset references
- contain no `Answer key`, `Correct answer`, or `Đáp án` leakage in the exported student files

## Regressions fixed during proof

1. Generated content artifacts can omit `artifact_id`; active graph now normalizes generated artifacts before snapshot rendering.
2. Student preview fallback lacked the required `oh-my-class` brand and could stringify answer/explanation fields from question components; preview rendering now emits the brand and only includes student-visible fields.
3. Standalone snapshot validation now requires the brand string, not only doctype/no-external-assets.
4. Vietnamese answer labels (`Đáp án`) are removed from student HTML by the answer-key sanitizer.

## Live run 2 — English ESL

- Marker family: `LIVE_V2_ESL_RENDER_FIX`
- Run ID: `e66ae203-967e-4bc2-b051-6cd51e96cc22`
- Teacher ID: `u-001`
- Contract gate: `gate-d8e0c762-9787-4513-8f8d-46f204e39c3b`
- Content gate: `gate-d3c03047-42f5-4886-878b-429c2608adba`
- Start job: `job-84688d98-dde1-4811-955f-fbeb77983f3b` → `completed`, attempts `1`
- Resume job: `job-7f5cc54f-e264-4e86-a445-584a2f10835e` → `completed`, attempts `1`
- Final run status: `COMPLETED`

Student preview invariants were checked before approval:

| Snapshot | Artifact | Type | Doctype | Brand | External assets | Answer-key leakage |
|---|---|---|---|---|---|---|
| `snap-7e08f181e7b62f8671acaabe` | `lesson-1` | `lesson` | yes | yes | no | no |
| `snap-4cce99650dde4591c7c48024` | `worksheet-2` | `worksheet` | yes | yes | no | no |
| `snap-257c34a0f1e41f0c05399032` | `quiz-3` | `quiz` | yes | yes | no | no |

Completed event `teaching_pack.run.completed` included exported files:

- `.scratch/pipeline-v2/artifacts/exports/e66ae203-967e-4bc2-b051-6cd51e96cc22/snap-7e08f181e7b62f8671acaabe.html`
- `.scratch/pipeline-v2/artifacts/exports/e66ae203-967e-4bc2-b051-6cd51e96cc22/snap-4cce99650dde4591c7c48024.html`
- `.scratch/pipeline-v2/artifacts/exports/e66ae203-967e-4bc2-b051-6cd51e96cc22/snap-257c34a0f1e41f0c05399032.html`

Filesystem verification of all three exports passed: files exist, contain `<!DOCTYPE html>`, contain `oh-my-class`, contain no `http://` or `https://` asset references, and contain no `Answer key`, `Correct answer`, `Đáp án`, `Answer:`, `Correct:`, or `Solution:` leakage in student files.

## Live run 3 — Science citation/research scenario

- Marker family: `LIVE_V2_SCIENCE_RENDER_FIX`
- Run ID: `212d4666-5c3c-4197-96f2-48cedbdd5494`
- Teacher ID: `u-001`
- Contract gate: `gate-d6a7006a-0b74-4eb5-84fa-053f7395976a`
- Content gate: `gate-a900e25e-7ce9-4ce8-b83c-266e3157d767`
- Start job: `job-b27d73be-ba9e-4881-aeb7-826bc879aad9` → `completed`, attempts `1`
- Resume job: `job-fe234d37-5c81-46c9-a4ad-e55e1dd9e4aa` → `completed`, attempts `1`
- Final run status: `COMPLETED`

Student preview invariants were checked before approval:

| Snapshot | Artifact | Type | Doctype | Brand | External assets | Answer-key leakage |
|---|---|---|---|---|---|---|
| `snap-44c83a3bf371406ed89a7a9c` | `lesson-1` | `lesson` | yes | yes | no | no |
| `snap-a8703926a08a3794534b2211` | `worksheet-2` | `worksheet` | yes | yes | no | no |
| `snap-e50cd91a144576e4954c914a` | `quiz-3` | `quiz` | yes | yes | no | no |

Completed event `teaching_pack.run.completed` included exported files:

- `.scratch/pipeline-v2/artifacts/exports/212d4666-5c3c-4197-96f2-48cedbdd5494/snap-44c83a3bf371406ed89a7a9c.html`
- `.scratch/pipeline-v2/artifacts/exports/212d4666-5c3c-4197-96f2-48cedbdd5494/snap-a8703926a08a3794534b2211.html`
- `.scratch/pipeline-v2/artifacts/exports/212d4666-5c3c-4197-96f2-48cedbdd5494/snap-e50cd91a144576e4954c914a.html`

Filesystem verification of all three exports passed: files exist, contain `<!DOCTYPE html>`, contain `oh-my-class`, contain no `http://` or `https://` asset references, and contain no `Answer key`, `Correct answer`, `Đáp án`, `Answer:`, `Correct:`, or `Solution:` leakage in student files.

## Regressions fixed during matrix proof

5. Normal quiz templates no longer render hidden/reveal answer blocks into student HTML; teacher-only answer content remains in answer-key/teacher-only paths.
6. Generated answer-key sections are normalized with `teacher_only=True` before graph quality and snapshot persistence.
7. A failed run job no longer kills the background worker; bad runs are marked failed and later jobs continue.
8. Inferred `RunContract.topic` values are capped to the schema's 200-character limit before Pydantic validation, preventing long live requests from crashing `POST /teaching-packs/runs`.

## Verification commands

- `uv run pytest packages/agents/tests/teaching_pack -q` → `22 passed`
- `uv run pytest services/gateway/tests/test_teaching_pack_snapshot_html_contract.py services/gateway/tests/test_teaching_pack_snapshot_store.py services/gateway/tests/test_teaching_pack_previews.py packages/agents/tests/teaching_pack -q` → `42 passed`
- `uv run python -m py_compile ...` over changed Python implementation/test files → success
- `pnpm --filter @oh-my-class/renderer test -- --runInBand` → `231 passed`
- `pnpm --filter @oh-my-class/renderer build` → success
- `uv run pytest services/gateway/tests/test_run_contract_setup.py services/gateway/tests/test_teaching_pack_snapshot_html_contract.py services/gateway/tests/test_teaching_pack_snapshot_store.py services/gateway/tests/test_teaching_pack_previews.py packages/agents/tests/teaching_pack/test_nodes.py services/gateway/tests/test_teaching_pack_worker.py -q` → `46 passed`
- Export invariant script over ESL and Science exported HTML → 6 files passed.

## Remaining release-matrix gap

The active three-scenario proof now covers Vietnamese Math, English ESL, and Science citation/research scenarios.

Additional live low-cost edge-case proof was recorded in `.scratch/pipeline-v2/artifacts/live-v2-edge-cases-2026-06-28.json`:

- missing grade/subject request stopped at `awaiting_approval` with no start job, covering the clarification-gate path
- duplicate create with the same teacher and `Idempotency-Key` returned the same run
- duplicate create with a different teacher and the same `Idempotency-Key` returned a different run, proving teacher-scoped idempotency
- non-owner status and cancel calls returned hidden `404 run_not_found`
- owner cancel calls cleaned up both gated runs

Soft-delete access-revocation proof was recorded in `.scratch/pipeline-v2/artifacts/live-v2-soft-delete-2026-06-28.json`:

- run `18e449be-f48d-469d-922b-9504355bc650` was created through public HTTP and stopped at `awaiting_approval`
- `DELETE /teaching-packs/run/{run_id}` returned `202` with `deleted: true`
- status and resume calls after deletion returned hidden `404 run_not_found`
- restore returned `202`, and owner cancellation cleaned up the run

Notification creation proof was first recorded as a gap in `.scratch/pipeline-v2/artifacts/live-v2-notification-gap-2026-06-28.json`, then fixed and re-proven in `.scratch/pipeline-v2/artifacts/live-v2-notification-fixed-2026-06-28.json`:

- gated create regression `services/gateway/tests/test_run_creation_security.py::test_gated_create_emits_teacher_notification` failed before wiring because no `Notification` row existed
- active gated create now calls the in-app notification helper after opening the setup gate
- live run `93e69793-a910-4ab2-b165-a403468cf37c` stopped at `awaiting_approval`
- `GET /notifications` for teacher `live-notification-teacher-1059cea2-5586-4500-bdac-b4c12d1dc30c` returned one `clarification_required` notification with `gate_name: clarification_required`
- cleanup cancellation returned `200`

Scoped artifact rejection/regeneration proof was recorded in `.scratch/pipeline-v2/artifacts/live-v2-scoped-rejection-fresh-schemafix-2026-06-29.json` after fixing the gate-history uniqueness constraint:

- fresh public-flow run `7b1bd4ab-388f-41dc-b68c-31ebc9b88bb7` used live 9Router model `4omc` on isolated gateway `http://127.0.0.1:8101`
- first `content_approval` gate was reached, the quiz artifact was rejected with scoped feedback, and a second `content_approval` gate opened with a new gate id
- accepted non-quiz lesson artifact was preserved while the quiz was regenerated
- second-gate student previews passed standalone checks: `<!DOCTYPE html>`, `oh-my-class`, no `http(s)://` external assets, and no answer-key markers
- second-gate approval completed the run and emitted `teaching_pack.run.completed` with exported files:
  - `.scratch/pipeline-v2/artifacts/exports/7b1bd4ab-388f-41dc-b68c-31ebc9b88bb7/snap-af2ec4dce89bbc6fa46f247e.html`
  - `.scratch/pipeline-v2/artifacts/exports/7b1bd4ab-388f-41dc-b68c-31ebc9b88bb7/snap-a69e9a6b41a80580020e5dbb.html`
- filesystem verification of both scoped-run exports passed: files exist, contain `<!DOCTYPE html>`, contain `oh-my-class`, contain no `http://` or `https://`, and contain no `Answer key`, `Correct answer`, `Đáp án`, `Answer:`, `Correct:`, or `Solution:` leakage

The database uniqueness bug found during scoped proof was fixed by replacing `uq_gate_interrupts_status` with a partial unique index that permits multiple historical `responded` gates while still allowing only one active gate per `(run_id, gate_name)`. Regression: `services/gateway/tests/test_teaching_pack_control_store.py::TestTeachingPackControlStore::test_allows_sequential_same_name_gate_responses`.

Search-plan confirmation proof was recorded in `.scratch/pipeline-v2/artifacts/live-v2-search-plan-confirmation-2026-06-29.json`:

- public-flow run `0582f23d-61c6-4b3a-8f3c-b18d893242b0` opened `contract_confirmation`, accepted a teacher edit that left curriculum unset, then opened `search_plan_confirmation`
- search-plan gate payload included planned queries and confirmation reason `ambiguous_curriculum`
- `teaching_pack.search_plan_confirmation.opened` was emitted
- approving the search-plan gate through `POST /teaching-packs/runs/{run_id}/resume` created the start job with the persisted contract
- route regressions cover both branches: contract approval opens a search-plan gate when required, and search-plan approval queues the graph start job

No-long-request timing proof was recorded in `.scratch/pipeline-v2/artifacts/live-v2-no-long-request-2026-06-29.json`:

- public-flow run `4fa1b299-79d4-4c38-a29d-e517209e2556` returned first create `202` in `0.1088s`, stopped at `clarification_required`, and returned `job_id: null`
- duplicate create with the same teacher and idempotency key returned `202` in `0.0055s` and reused the same run
- clarification resume returned `202` in `0.0119s` and queued resume job `job-5f3b3464-a5b5-4ad0-8095-19593f024f60`
- cleanup cancellation completed through the public route

Langfuse-unavailable proof was recorded in `.scratch/pipeline-v2/artifacts/live-v2-langfuse-unavailable-2026-06-29.json`:

- isolated gateway `http://127.0.0.1:8102` ran with `LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY` configured and `LANGFUSE_HOST=http://127.0.0.1:9`
- public-flow run `9e16199e-d273-4eee-95ab-ff1c0993ee23` returned create `202` in `0.0996s`, persisted for teacher `teacher-langfuse-fc013a02-d08b-4a3f-8e10-422ba6374701`, and reached `clarification_required`
- no start job was queued before the gate, and cleanup cancellation completed through the public route

Worker restart/lease-expiry proof was recorded in `.scratch/pipeline-v2/artifacts/live-v2-worker-lease-2026-06-29.json`:

- public-flow run `ab97408f-8e2c-4399-a1ec-a2096c39201a` returned create `202` in `0.0963s`, reached `clarification_required`, and returned `job_id: null`
- simulated crashed-worker job `job-lease-proof-afb3c504-1bb1-4815-9227-c416f792314f` was inserted as `running` with owner `simulated-crashed-worker` and an expired lease at the simulated claim time
- `TeachingPackJobStore.claim_next(...)` reclaimed the job for `simulated-restarted-worker`, incremented attempts from `1` to `2`, and set a fresh lease
- cleanup cancellation completed through the public route

UI/generated-client/SSE compatibility proof was recorded in `.scratch/pipeline-v2/artifacts/live-v2-ui-sse-compat-2026-06-29.json`:

- production web app `http://localhost:3000` used `http://localhost:8101` as `NEXT_PUBLIC_GATEWAY_URL`
- browser-created run `584ae7e8-4bea-425e-92b4-67f9b6c6bf40` returned `202` with `job_id: null` and status `awaiting_approval`
- the run detail page loaded `GET /teaching-packs/runs/{run_id}` with `200`, replayed `teaching_pack.clarification_required.opened` into the Events panel, and rendered the clarification gate
- EventSource worked with cookie auth, the UI submitted `action: answer` through `POST /teaching-packs/runs/{run_id}/resume`, and the gateway returned `202`
- the persisted gate response was `{"action": "answer", "answer": "Grade 5 Math"}`; browser console errors after submit were `0`; cleanup cancellation completed through the public route

Additional production browser/visual QA was captured after the UI/gate fixes:

- production Next was run against `NEXT_PUBLIC_GATEWAY_URL=http://127.0.0.1:8101`
- browser run `d858111a-939f-4b5e-b0cb-058ee68b9124` loaded `/runs/{run_id}` through the active Teaching Pack JSON status endpoint
- the page rendered `awaiting_approval`, the `Confirm the teaching contract` gate, visible approve/reject/edit actions, and the replayed `teaching_pack.contract_confirmation.opened` event
- console errors were `0`, `GET /teaching-packs/runs/{run_id}` returned `200`, and screenshot evidence is `.scratch/pipeline-v2/artifacts/teaching-pack-gate-production-visual-qa.png`
- cleanup cancellation completed through the public route with status `cancelled`

Timeout/malformed-JSON review evidence was recorded in `.scratch/pipeline-v2/artifacts/live-v2-timeout-malformed-json-review-2026-06-29.json`:

- the active `/teaching-packs/*` graph path calls `packages/agents/sub_agents/content_creator/nodes.py::content_creator_node` directly from `packages/agents/teaching_pack/nodes.py::_artifact_workflow`
- deterministic tests confirm malformed JSON is retried with a repair prompt scoped to the failing artifact, timeout/provider exceptions are retried the same way, and exhausted attempts fail closed through `TeachingPackExecutor`/`TeachingPackWorker`
- focused verification passed: `uv run pytest packages/agents/tests/sub_agents/test_content_creator.py packages/agents/tests/sub_agents/test_content_creator_per_artifact.py services/gateway/tests/test_artifact_workflow.py services/gateway/tests/test_teaching_pack_executor.py services/gateway/tests/test_teaching_pack_worker.py -q` → `80 passed`
- `uv run python -m py_compile packages/agents/sub_agents/content_creator/nodes.py packages/agents/teaching_pack/nodes.py services/gateway/artifact_workflow.py services/gateway/healing_executors.py services/gateway/teaching_pack_executor.py services/gateway/teaching_pack_worker.py` succeeded

Timeout/malformed fault-injection proof was recorded in `.scratch/pipeline-v2/artifacts/live-v2-timeout-malformed-fault-2026-06-29.json`:

- public `/teaching-packs/runs` created run `5f14175b-7304-4d50-8a4a-7e1e73664474` and start job `job-91bd8657-5896-4418-bff9-f2a781fb276b`
- a safe graph-boundary fault injected `TimeoutError: fault-injected provider timeout` through the active `TeachingPackWorker`/`TeachingPackExecutor` path
- the run transitioned to `FAILED`, the job was marked `failed`, and both `teaching_pack.status.changed` and `teaching_pack.run.failed` persisted the timeout summary
- paired active content-creator tests cover malformed JSON retry/recovery, exhausted malformed JSON failure without placeholders, and timeout retry/recovery for the target artifact

ISSUE-011 active-surface live release gates are covered. Remaining full-Pipeline V2 blockers live outside ISSUE-011: persisted recovery orchestration beyond the active graph routing seam, UI/UX cutover QA, auth/governance/versioning, ops/admin recovery, prompt/rubric governance, and final consolidated release reporting.

Pack-level coherence progress for ISSUE-009:

- active render-quality now calls `packages/agents/teaching_pack/quality.py::quality_issues` before snapshots/content approval
- a lesson/quiz mismatch with disjoint content terms is blocked with `pack.coherence: quiz_not_aligned_with_lesson`
- coherence now also blocks objective drift, lesson key-vocabulary drift for quiz/worksheet artifacts, and Vietnamese quiz difficulty distribution mismatch when metadata signals are present
- typed healing routes now explicitly map factual uncertainty to research enrichment and pedagogical mismatch to blueprint replan
- render-quality recovery routing now sends objective drift and Vietnamese difficulty mismatch to `planning_blueprint`, factual uncertainty to `post_blueprint_research`, and artifact-local coherence drift to `artifact_workflow` before teacher approval can run
- quality helpers were extracted from `packages/agents/teaching_pack/nodes.py`; `nodes.py` is now below the 250 pure-LOC ceiling, with `quality.py`, `quality_routing.py`, and `scoped_regeneration.py` owning focused responsibilities
- focused verification passed: `uv run pytest packages/agents/tests/teaching_pack/test_render_quality.py -q` → `6 passed`; focused graph/node/quality smoke after test split → `44 passed`; broader focused Teaching Pack/quality/security suite → `132 passed`; quality/healing contracts → `15 passed`; manual `_render_quality` driver accepted a good pack, routed objective drift to `planning_blueprint`, and routed vocabulary drift to `artifact_workflow`

Focused Teaching Pack security closure:

- default auth dependencies no longer accept `auth-token` cookies; cookie auth is isolated to the status-stream dependency needed by browser EventSource
- middleware cookie fallback is restricted to exact Teaching Pack status-stream paths
- contract edit payloads can update only explicitly allowlisted teacher-facing fields; immutable fields such as `run_id`, `teacher_id`, and `config_hash` are preserved
- focused verification passed: auth/contract/stream/security suite → `31 passed`; broader focused suite after security and coherence work → `102` then `105 passed`; fresh temporary gateway smoke showed cookie-only non-SSE create returns `401`, while cookie status-stream access reaches ownership with `404` for a missing run
