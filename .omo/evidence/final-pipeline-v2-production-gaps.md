# Final Evidence — Pipeline V2 Production Gaps

Date: 2026-06-28
Plan: `.omo/plans/pipeline-v2-production-gaps.md`

## Verdict

Final production-readiness verification is approved.

Tasks 1-10 are implemented and independently evidenced. Final audits F1-F4 are approved after the F2 blocker fixes for module size and Alembic migration heads.

## Task evidence summary

| Task | Capability | Evidence status |
|---|---|---|
| 1 | Live 9Router chat smoke harness for `http://127.0.0.1:20228/v1`, model `4omc` | PASS. Deterministic tests plus live `/v1/models` and `/v1/chat/completions` evidence recorded. Reasoning-model empty-content behavior is documented, not hidden. |
| 2 | Gateway release evidence includes 9Router provider status | PASS. Provider base URL/model/timestamp/pass-block status added. Migration 012 corrected release evidence schema drift. Live chat timeout recorded honestly as unavailable/fail, not mocked success. |
| 3 | Gateway-to-Eta renderer adapter | PASS. Subprocess adapter tests cover success, malformed input, non-zero exit, timeout, dirty CDN output, empty output, and missing binary. Renderer suite evidence recorded. |
| 4 | Eta-rendered snapshots persisted with version metadata and answer-key isolation | PASS. `create_snapshot()` validates answer-key isolation before persistence, removes answer keys from student HTML, stores renderer/template/theme versions and hashes, and blocks non-standalone approval. Duplicated mid-iteration evidence tail was removed; final file now reflects the corrected INVARIANT-05 behavior. |
| 5 | Canonical rubric registry contracts | PASS. Pydantic contracts enforce weight sums, duplicate version rejection, immutable/hashable versions, and JSON roundtrip. |
| 6 | Adaptive LLM judge integrated with deterministic hard blocks | PASS. Rubric provenance is attached, artifact/failure-context selection is tested, and hard blocks such as external assets/answer-key leakage cannot be overridden by high LLM scores. |
| 7 | Prompt compiler with overlay governance/provenance | PASS. Compilation, overlay determinism, unknown/missing variables, duplicate overlay IDs, secret-like overlays, and drift rejection are tested. |
| 8 | Prompt eval harness and scoped migration to compiled prompt metadata | PASS. Planner/content-creator/shared compiled JSON path emits prompt provenance tags. Existing unrelated raw prompt callers were intentionally not migrated. |
| 9 | Queued/delayed backpressure state and worker semantics | PASS. Active-limit queueing, queue-limit rejection, per-teacher isolation, queued/ineligible job skipping, promotion after capacity frees, idempotency, and queued cancellation are covered. |
| 10 | Queued-job Alembic migration | PASS. `eligible_at` column/index migration and model/store behavior verified; task 9 direct-DB gap closed. |

## Final audits

| Audit | Verdict | Evidence |
|---|---|---|
| F1 Plan compliance | APPROVE | Each todo maps to code, tests, and evidence files `task-1` through `task-10`. |
| F2 Code quality | APPROVE | Post-fix audit verified all F2-touched modules are <=250 pure LOC, package boundaries are clean, route imports/paths are compatible, INVARIANT-05 is enforced before persistence, ruff is clean, targeted tests pass, Alembic has a single head, and no test weakening was found. |
| F3 Surface QA | APPROVE | Live provider smoke, gateway API routes, preview/snapshot metadata paths, renderer adapter surface, queue/backpressure behavior, and migration/database surfaces were exercised and recorded in task evidence. |
| F4 Scope fidelity | APPROVE | No teacher-gate bypass, no generated-schema hand edits, no paid fallback conversion, no public `RunStatus.QUEUED`, and no unrelated broad migration beyond scoped prompt paths. Existing `pipeline_v2_` filenames remain where already part of the service convention; new user-facing naming was not expanded beyond current module area. |

## F2 blocker resolution details

Final F2 rerun returned `APPROVE` with these checks:

- LOC: all F2-touched modules <=250 pure LOC.
  - `packages/quality/layer4_judge/judge_interface.py`: 234 pure LOC.
  - `services/gateway/pipeline_v2_snapshot_store.py`: 177 pure LOC.
  - `services/gateway/routers/pipeline_v2_runs.py`: 204 pure LOC.
- Alembic: single head `012_provider_evidence_column`; linear chain `007 -> 008 -> 009 -> 010 -> 011 -> 012`.
- Boundaries: `packages/quality` has no imports from `services`, `apps`, or `agents`.
- INVARIANT-05: `remove_answer_keys_from_html()` and `validate_answer_key_isolation()` run before `pg_insert`; `AnswerKeyLeakageError` blocks persistence on leakage.
- Routes: `/pipeline-v2` router mounting and sub-route compatibility preserved.
- Tests: F2 verifier reported all targeted suites passing, including quality, integration, snapshot, preview, artifact snapshot service, runs router/auth/edges, soft delete, and idempotency tests.
- Test integrity: no skipped/xfail/commented-out assertions or hollow assertion hacks found.

## Residual warnings documented, not hidden

- 9Router model `4omc` can route to a reasoning model with empty `content` and `reasoning_content`; smoke harness records response shape rather than assuming assistant text.
- One task-2 live chat probe timed out and was recorded as unavailable/fail evidence, not converted into a fake pass.
- Adaptive judge task evidence is deterministic fake-transport coverage; no live LLM judge call was required for the final F2 code-quality approval.
- Known unrelated warnings may still appear in broader local runs: Starlette/httpx TestClient deprecation, Next.js workspace-root warning, Vite CJS API deprecation, and `MODULE_TYPELESS_PACKAGE_JSON` for `apps/web/postcss.config.js`.

## Final status

Pipeline V2 production gaps plan is complete from the implementation/evidence perspective. The remaining worktree state is intentionally uncommitted because no commit was requested.
