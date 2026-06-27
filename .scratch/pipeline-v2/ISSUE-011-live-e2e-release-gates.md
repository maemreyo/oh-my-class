---
title: Pipeline V2 live E2E release gates and production readiness evidence
status: ready-for-agent
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
