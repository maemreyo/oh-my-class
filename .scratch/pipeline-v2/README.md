# Pipeline V2 Issue Index

This folder contains the indexed issue set for the Pipeline V2 production rearchitecture.

Issue metadata uses `order` and `blocked_by` so agents know execution sequence. All issues remain in one folder to keep the V2 migration backlog together.

## Execution Order

1. `ISSUE-001-foundation-architecture.md` — establish V2 package boundaries, contracts, config loading, and stage graph skeleton.
2. `ISSUE-002-production-persistence.md` — Postgres run store, checkpointer wiring, event log, and artifact snapshot store.
3. `ISSUE-003-control-plane-executor.md` — background run executor, generic resume API, gate registry, and status state machine.
4. `ISSUE-004-run-contract-setup-stage.md` — smart Preflight, Quickstart, RunContract, conditional contract/clarification gates.
5. `ISSUE-005-research-engine.md` — independent Research Engine with search/fetch/rank/extract/brief synthesis.
6. `ISSUE-006-adaptive-llm-transport.md` — per-task adaptive streaming policy and privacy-conscious Langfuse metadata.
7. `ISSUE-007-artifact-workflow.md` — artifact-level generation, ArtifactWorkflowState, bounded parallelism, and per-artifact validation.
8. `ISSUE-008-rendered-preview-approval.md` — render before approval, persisted snapshots, artifact preview APIs, and UI approval flow.
9. `ISSUE-009-quality-healing-safety.md` — typed healing, safety gates, pack coherence, and export readiness.
10. `ISSUE-010-ui-ux-cutover.md` — frontend V2 hooks, stage progress, gate shell, search/contract/content UX.
11. `ISSUE-011-live-e2e-release-gates.md` — real Postgres + live 9Router release matrix and production readiness evidence.
12. `ISSUE-012-auth-governance-versioning.md` — tenant auth, data governance, retention, deletion, and contract/API versioning.
13. `ISSUE-013-operations-hardening.md` — idempotency, job leases, cancellation, stuck recovery, budgets, and backpressure.
14. `ISSUE-014-notifications-admin-recovery.md` — in-app notifications and predefined safe admin recovery actions.
15. `ISSUE-015-prompt-template-rubric-governance.md` — prompt, template, theme, and rubric registries/evals.

## Related ADRs

- `docs/adr/002-pipeline-v2-stage-architecture.md`
- `docs/adr/003-run-contract-and-conditional-hitl.md`
- `docs/adr/004-production-run-persistence.md`
- `docs/adr/005-generic-gate-resume-api.md`
- `docs/adr/006-research-engine.md`
- `docs/adr/007-adaptive-llm-transport.md`
- `docs/adr/008-artifact-workflow-and-rendered-snapshots.md`
- `docs/adr/009-quality-healing-and-safety-gates.md`
- `docs/adr/010-pipeline-v2-testing-and-observability.md`
- `docs/adr/011-operational-hardening.md`
- `docs/adr/012-data-governance-and-versioning.md`
- `docs/adr/013-prompt-template-rubric-governance.md`

## Testing Discipline

Every issue includes a `Required Edge Cases And Tests` section. Implementing agents must satisfy those edge cases before marking an issue complete. If an edge case is intentionally deferred, create a follow-up issue and document why it does not block the current issue.
