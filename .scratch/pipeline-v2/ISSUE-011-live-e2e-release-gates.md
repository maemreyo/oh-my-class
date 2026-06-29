---
title: Pipeline V2 live E2E release gates and production readiness evidence
status: review-partial
labels: [pipeline-v2, e2e, release, 9router]
created: 2026-06-27
order: 11
blocked_by:
  - ISSUE-001-foundation-architecture
  - ISSUE-002-production-persistence
  - ISSUE-003-control-plane-executor
  - ISSUE-004-run-contract-setup-stage
  - ISSUE-005-research-engine
  - ISSUE-006-adaptive-llm-transport
  - ISSUE-007-artifact-workflow
  - ISSUE-008-rendered-preview-approval
  - ISSUE-009-quality-healing-safety
  - ISSUE-010-ui-ux-cutover
adr_refs:
  - docs/adr/010-pipeline-v2-testing-and-observability.md
---

## Problem

The current codebase has high automated test pass rates but live full-flow failures. Pipeline V2 must not claim production readiness without real end-to-end evidence using production-path services and live 9Router behavior.

## Scope

Build and run the V2 release validation suite.

Agent-ready tasks:

1. Add deterministic regression E2E suite for orchestration, gates, persistence, status, and export.
2. Add live 9Router E2E suite for production proof.
3. Add real Postgres integration fixtures for run store, checkpointer, event log, and snapshots.
4. Add release evidence reporting that records run ids, timings, statuses, trace ids, events, generated artifacts, and export outputs.
5. Validate Langfuse unavailable mode does not block runs.
6. Validate SSE refresh/reconnect.
7. Validate no long HTTP request for create/resume.
8. Validate privacy/safety invariants.

## Required Live 9Router Scenarios

1. Vietnamese Grade 5 Math: equivalent fractions with common denominator misconception.
2. English Grade 7: travel phrasal verbs, low-pressure speaking practice, why-wrong MCQ explanations.
3. Science factual/citation scenario with research-backed claims.
4. Missing grade/subject request that triggers clarification.
5. Ambiguous artifact scope that triggers contract confirmation.
6. High-impact search direction that triggers search plan confirmation.
7. Scoped teacher rejection of one artifact and successful regeneration.
8. Timeout/malformed JSON path that triggers adaptive streaming or typed healing.
9. Rendered standalone HTML export and student-safe artifact endpoint.

## Out Of Scope

- Supporting deferred artifact/export types.
- Load testing beyond basic performance budgets.

## Acceptance Criteria

- Deterministic E2E suite passes.
- Real Postgres integration suite passes.
- Live 9Router release matrix completes with documented evidence.
- No production-readiness claim is made without live run ids and artifacts.
- Langfuse traces correlate by run id/stage/artifact where enabled.
- Student-facing previews contain no teacher-only answer keys.
- Rendered HTML contains no external assets.

## Test Plan

This issue is the test plan. It must produce a release evidence report under `docs/reports/` or `.scratch/pipeline-v2/artifacts/`.

## Observability

- Capture compact metrics: total duration, per-stage duration, LLM durations, search/fetch counts, retry/healing counts, artifact statuses, and export status.
- Do not include secrets, raw prompts, raw fetched pages, or student PII in reports.

## Required Edge Cases And Tests

- Release evidence includes run id, teacher/org context id hash, statuses, event sequence range, trace ids if Langfuse enabled, artifact ids, snapshot ids, and export files.
- Live E2E covers tenant authorization: non-owner teacher cannot view/resume/export another run.
- Live E2E covers idempotency: duplicate create/resume does not duplicate work.
- Live E2E covers cancellation of queued and running runs.
- Live E2E covers worker restart or simulated lease expiry if the test harness can safely trigger it.
- Live E2E covers Langfuse unavailable and 9Router transient failure paths.
- Live E2E covers prompt/template/rubric version metadata in artifacts/events.
- Live E2E covers generated frontend/API type compatibility by exercising the UI or generated client.
- Live E2E covers deletion/soft-delete access revocation.
- Live E2E covers notification creation for gates/completion/failure.
- Report must explicitly list skipped scenarios and why; skipped production-readiness scenarios require follow-up issues.

## Rollback

If any release-gate scenario fails, V2 is not production-ready. Create follow-up issues for root-cause fixes rather than waiving the scenario.

## Ultrawork Review — 2026-06-27

Status: PARTIAL. Deterministic E2E and release evidence infrastructure exist. The active three-scenario live proof now exists, but several required production-readiness edge cases remain uncovered.

Evidence:
- E2E tests were added in `tests/e2e/test_pipeline_v2_deterministic.py` and `tests/e2e/test_pipeline_v2_scenarios.py`, with fixtures in `tests/e2e/conftest.py`.
- Release evidence models and storage are implemented in `services/gateway/release_evidence.py`, `release_evidence_store.py`, and route `services/gateway/routers/release_evidence.py`.
- Tests cover release evidence fields, event sequence, snapshot IDs, skipped scenarios, privacy, and report generation in `services/gateway/tests/test_release_evidence.py`.

Live active-surface evidence added 2026-06-28:
- Evidence report: `.scratch/pipeline-v2/artifacts/live-v2-preview-export-evidence-2026-06-28.md`.
- Edge-case evidence: `.scratch/pipeline-v2/artifacts/live-v2-edge-cases-2026-06-28.json`.
- Soft-delete evidence: `.scratch/pipeline-v2/artifacts/live-v2-soft-delete-2026-06-28.json`.
- Notification gap/fix evidence: `.scratch/pipeline-v2/artifacts/live-v2-notification-gap-2026-06-28.json` and `.scratch/pipeline-v2/artifacts/live-v2-notification-fixed-2026-06-28.json`.
- Vietnamese Math run: `f8dc8f4b-e472-4236-96e0-cd898ee06902`; snapshots `snap-db028626ef2e15f265a7b15b`, `snap-87a62e4d9b36bc265585da82`; exports under `.scratch/pipeline-v2/artifacts/exports/f8dc8f4b-e472-4236-96e0-cd898ee06902/`.
- English ESL run: `e66ae203-967e-4bc2-b051-6cd51e96cc22`; snapshots `snap-7e08f181e7b62f8671acaabe`, `snap-4cce99650dde4591c7c48024`, `snap-257c34a0f1e41f0c05399032`; exports under `.scratch/pipeline-v2/artifacts/exports/e66ae203-967e-4bc2-b051-6cd51e96cc22/`.
- Science citation/research run: `212d4666-5c3c-4197-96f2-48cedbdd5494`; snapshots `snap-44c83a3bf371406ed89a7a9c`, `snap-a8703926a08a3794534b2211`, `snap-e50cd91a144576e4954c914a`; exports under `.scratch/pipeline-v2/artifacts/exports/212d4666-5c3c-4197-96f2-48cedbdd5494/`.
- All listed student previews and exported HTML files were checked for `<!DOCTYPE html>`, `oh-my-class`, no external `http(s)://` asset references, and no student-facing answer-key markers.
- Live edge-case probe `LIVE_V2_EDGE_CASES_ffa5e4d8-374c-4764-bab8-4804a837d068` covered missing-field clarification, teacher-scoped create idempotency, non-owner status/cancel denial, and owner cancellation cleanup. Runs `d3d73bf2-ee46-44c1-853d-d12ee8cee3e8` and `7e4a7f3c-1de8-4af3-92e7-ccd73c39f438` ended `cancelled` after cleanup.
- Live soft-delete probe `LIVE_V2_SOFT_DELETE_2596fea2-f41e-441b-98e7-5433cf1a3e50` covered access revocation after `DELETE /teaching-packs/run/{run_id}`. Run `18e449be-f48d-469d-922b-9504355bc650` was hidden from status/resume after deletion, restored for cleanup, then cancelled.
- Live notification probe first showed no active-flow gate notification for run `9401a1d2-390e-4abc-bdfa-fbce69b17dd8`; after the fix, `LIVE_V2_NOTIFICATION_FIXED_CHECK` showed gated run `93e69793-a910-4ab2-b165-a403468cf37c` emitted one owned `clarification_required` notification through `GET /notifications`.
- Live scoped rejection/regeneration probe: `.scratch/pipeline-v2/artifacts/live-v2-scoped-rejection-fresh-schemafix-2026-06-29.json`.
- Scoped run `7b1bd4ab-388f-41dc-b68c-31ebc9b88bb7` reached first content approval, rejected only the quiz, opened a new second content approval gate, preserved the accepted lesson, approved regenerated snapshots, completed, and emitted exported files under `.scratch/pipeline-v2/artifacts/exports/7b1bd4ab-388f-41dc-b68c-31ebc9b88bb7/`.
- Scoped proof regression fixed: sequential `content_approval` gates for the same run now allow multiple historical `responded` rows while keeping the one-active-gate invariant via `uq_gate_interrupts_active`.
- Live search-plan confirmation probe: `.scratch/pipeline-v2/artifacts/live-v2-search-plan-confirmation-2026-06-29.json`.
- Search-plan run `0582f23d-61c6-4b3a-8f3c-b18d893242b0` reached `contract_confirmation`, accepted a teacher edit that left curriculum unset, opened `search_plan_confirmation` with query/reason payload, accepted search-plan approval, and queued the graph start job.
- Live no-long-request timing probe: `.scratch/pipeline-v2/artifacts/live-v2-no-long-request-2026-06-29.json`.
- Timing run `4fa1b299-79d4-4c38-a29d-e517209e2556` proved public HTTP create/resume return quickly while work remains gated/queued: first create `202` in `0.1088s` with `job_id: null` at `clarification_required`, duplicate create `202` in `0.0055s` reusing the same run, and clarification resume `202` in `0.0119s` with a queued resume job. Cleanup cancellation completed through the public route.
- Live Langfuse-unavailable probe: `.scratch/pipeline-v2/artifacts/live-v2-langfuse-unavailable-2026-06-29.json`.
- Langfuse-unavailable run `9e16199e-d273-4eee-95ab-ff1c0993ee23` used an isolated gateway on `http://127.0.0.1:8102` with `LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY` configured and `LANGFUSE_HOST=http://127.0.0.1:9`. Public create still returned `202` in `0.0996s`, persisted the run for the teacher, reached `clarification_required`, and cleanup cancellation completed through the public route.
- Live worker restart/lease-expiry probe: `.scratch/pipeline-v2/artifacts/live-v2-worker-lease-2026-06-29.json`.
- Worker-lease run `ab97408f-8e2c-4399-a1ec-a2096c39201a` was created through public HTTP and stopped at `clarification_required` with `job_id: null`. The probe inserted a simulated crashed-worker running job `job-lease-proof-afb3c504-1bb1-4815-9227-c416f792314f`, advanced the claim time past `lease_expires_at`, and proved `TeachingPackJobStore.claim_next(...)` reclaimed it for `simulated-restarted-worker`, incrementing attempts from `1` to `2`. Cleanup cancellation completed through the public route.
- Live UI/generated-client/SSE compatibility probe: `.scratch/pipeline-v2/artifacts/live-v2-ui-sse-compat-2026-06-29.json`.
- Browser run `584ae7e8-4bea-425e-92b4-67f9b6c6bf40` was created from the production web app on `http://localhost:3000` against `http://localhost:8101/teaching-packs/*`. The run detail page loaded the active Teaching Pack JSON status endpoint, replayed `teaching_pack.clarification_required.opened` through EventSource cookie auth, rendered the clarification gate, submitted `action: answer` through the generated-client resume path, and received `202`. Console errors after submit were `0`; cleanup cancellation completed through the public route.
- Additional production browser/visual QA used run `d858111a-939f-4b5e-b0cb-058ee68b9124` on `http://127.0.0.1:3000` with `NEXT_PUBLIC_GATEWAY_URL=http://127.0.0.1:8101`. The active run detail page rendered `awaiting_approval`, the `Confirm the teaching contract` gate, visible approve/reject/edit controls, and the replayed `teaching_pack.contract_confirmation.opened` event with `0` browser console errors. Screenshot evidence: `.scratch/pipeline-v2/artifacts/teaching-pack-gate-production-visual-qa.png`; cleanup cancellation returned `200`.
- Timeout/malformed-JSON review evidence: `.scratch/pipeline-v2/artifacts/live-v2-timeout-malformed-json-review-2026-06-29.json`.
- Deterministic coverage confirms the active content creator retries malformed JSON and timeout/provider exceptions per artifact up to 3 attempts, then fail-closes through `TeachingPackExecutor`/`TeachingPackWorker` if exhausted. Focused verification passed: `packages/agents/tests/sub_agents/test_content_creator.py`, `test_content_creator_per_artifact.py`, `services/gateway/tests/test_artifact_workflow.py`, `test_teaching_pack_executor.py`, and `test_teaching_pack_worker.py` (`80 passed`).
- Timeout/malformed fault-injection proof: `.scratch/pipeline-v2/artifacts/live-v2-timeout-malformed-fault-2026-06-29.json`.
- Public `/teaching-packs/runs` created run `5f14175b-7304-4d50-8a4a-7e1e73664474` and start job `job-91bd8657-5896-4418-bff9-f2a781fb276b`; the active `TeachingPackWorker`/`TeachingPackExecutor` path was driven with a fault-injected `TimeoutError`. The run failed closed, the job was marked `failed`, and `teaching_pack.run.failed` persisted `TimeoutError: fault-injected provider timeout`. Paired active content-creator regression covers malformed JSON retry/recovery and timeout retry/recovery scoped to one artifact.

Focused-slice closure added 2026-06-29:
- Security review blockers are closed: default auth dependencies no longer accept `auth-token` cookies, cookie auth is isolated to status-stream routes for browser EventSource, middleware cookie fallback is restricted to exact Teaching Pack status paths, and contract edits preserve immutable fields through an explicit allowlist.
- Security verification: `uv run pytest services/gateway/tests/test_teaching_pack_auth.py services/gateway/tests/test_teaching_pack_contract_resume.py services/gateway/tests/test_teaching_pack_stream_router.py services/gateway/tests/test_run_creation_security.py -q` → `31 passed`; broader focused suite → `102 passed`; fresh temporary gateway smoke returned non-SSE cookie-only create `401` and status-stream cookie auth reached ownership with `404` for a missing run; Oracle security review returned PASS.
- ISSUE-009 focused coherence/healing-routing blockers are closed: pack-level coherence now blocks objective drift, lesson vocabulary drift, and Vietnamese difficulty mismatch before content approval/export; factual uncertainty and pedagogical mismatch have explicit typed healing routes.
- ISSUE-009 verification: quality/healing contracts → `15 passed`; focused Teaching Pack suite → `105 passed`; manual `_render_quality` good/bad driver passed; Oracle focused-closure review returned PASS.

Gaps:
- The deterministic E2E fixture documents mocked/no-real-API behavior; it complements but does not replace live 9Router proof.
- ISSUE-011 required live release gates are now covered on the active `/teaching-packs/*` surface, with the timeout leg proven by safe fault injection at the graph boundary plus active content-creator malformed-JSON retry regressions. Broader production-readiness blockers remain in ISSUE-012/013/014/015 plus broader self-healing orchestration, adaptive judge/rubric governance, and final consolidated reporting.
