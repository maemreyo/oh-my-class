# pipeline-v2-production-gaps - Work Plan

## TL;DR (For humans)
**What you'll get:** Pipeline V2 will have production-grade proof that the live local 9Router model works, rendered teaching-pack snapshots from the real template engine, governed prompt changes, adaptive quality judging, and real queued/deferred processing under load.

**Why this approach:** The work is split by runtime seam so each slice can be tested, evidenced, and rolled back independently while preserving the existing fail-closed pipeline and teacher approval gates.

**What it will NOT do:** It will not fake live provider evidence, bypass teacher gates, add paid provider fallbacks, or replace deterministic validation with LLM-only judgment.

**Effort:** XL
**Risk:** High - the work crosses live provider I/O, Python gateway state, TypeScript rendering, shared schemas, database/job behavior, and final browser/API QA.
**Decisions to sanity-check:** Use `http://127.0.0.1:20228/v1` + `4omc` for live evidence; keep CI deterministic with mocked/unit seams; represent delayed work as queued jobs with `eligible_at`, then reject clearly once queued capacity is full.

Your next move: choose whether to start implementation now or run a high-accuracy plan review first. Full execution detail follows below.

---

> TL;DR (machine): XL/high-risk production-hardening plan across live 9Router evidence, Eta snapshots, adaptive judge/rubrics, prompt governance, and queued backpressure.

## Scope
### Must have
- Live 9Router evidence using `http://127.0.0.1:20228/v1` and model `4omc`, including a stored `.omo/evidence/` artifact that proves the model endpoint is reachable and returns a valid completion.
- Configurable LLM/provider target wiring so tests can run deterministically without the live service while production proof still uses the live sidecar.
- Gateway snapshot creation that renders artifacts through the existing Eta renderer surface and persists standalone teacher/student HTML plus renderer/template/theme metadata.
- Snapshot preview and approval behavior remains teacher-gated and fails closed for non-standalone or answer-key-leaking student HTML.
- Versioned adaptive judge/rubric contracts and registry grounded in canonical Pydantic contracts and existing `JudgeOutput` semantics.
- Prompt compiler and overlay governance that records prompt ID/version/hash/compiled hash, rejects undeclared variables or secret-like content, and adds an evaluation harness.
- Backpressure flow that queues/delays runs when active capacity is saturated but queued capacity remains, then workers dequeue when capacity returns. This includes an Alembic migration for `RunJobStatus.QUEUED` and nullable `RunJob.eligible_at` (`DateTime(timezone=True)`, DB `timestamptz`).
- Comprehensive edge-case tests and full verification across affected Python/TypeScript suites, plus final live-provider and agent-executed surface QA.

### Must NOT have (guardrails, anti-slop, scope boundaries)
- Must not bypass or self-approve teacher gates.
- Must not add direct paid-provider fallbacks or route around 9Router.
- Must not fake live provider evidence; blocked live evidence must be reported as blocked.
- Must not hand-edit generated schema files; regenerate them from Pydantic contracts.
- Must not make `packages/agents` import from `services/*` or `apps/*`.
- Must not use legacy/manual HTML as the new production snapshot renderer when the Eta renderer can render the artifact.
- Must not weaken, delete, or skip existing tests to get green output.
- Must not prefix new implementation names with `pipeline_v2_` unless an existing file/table/API convention already requires it.
- Must not fix unrelated verification failures outside these five production-hardening slices; document them as known issues instead.

## Verification strategy
> Zero human intervention - all verification is agent-executed.
- Test decision: tests-after, with targeted unit/integration tests per slice, then full affected suite runs. Add regression tests before fixing if a defect is discovered during implementation.
- Python tools: `uv run ruff check services/gateway packages/agents packages/quality common/contracts tests`, `uv run basedpyright services/gateway packages/agents packages/quality common/contracts` where local config supports it, `uv run pytest services/gateway/tests/ packages/agents/prompts/tests/ packages/quality/tests/ common/contracts/tests/ tests/e2e/ --tb=short`.
- TypeScript tools: `pnpm --filter renderer test`, `pnpm --filter web test`, `pnpm --filter web build`, schema generation tests where contracts change.
- Live evidence: OpenAI-compatible `/v1/models` and `/v1/chat/completions` calls against `http://127.0.0.1:20228/v1` with model `4omc`; store command, response shape, and redacted body in `.omo/evidence/`.
- Agent-executed surface QA: drive the HTTP/API/preview surface with curl/TestClient/browser automation as appropriate; no human tester is required. If the whole pipeline cannot complete locally, run the smallest live surface that uses the implemented adapter and report the blocked dependency.
- Evidence: `.omo/evidence/task-<N>-pipeline-v2-production-gaps.md` or `.json` per task, plus `.omo/evidence/final-pipeline-v2-production-gaps.md`.

## Execution strategy
### Parallel execution waves
> Target 5-8 todos per wave. Fewer than 3 (except the final) means you under-split.
- Wave 1: provider evidence/config, renderer adapter design, rubric contracts, prompt compiler foundations, backpressure queue data model can proceed in parallel after a dirty-worktree audit.
- Wave 2: integrate each slice into gateway/runtime seams and add deterministic edge-case tests.
- Wave 3: run full verification, live 9Router proof, preview/API surface QA, and release evidence generation.

### Dependency matrix
| Todo | Depends on | Blocks | Can parallelize with |
| --- | --- | --- | --- |
| 1 | None | 2, 11 | 3, 5, 7, 9 |
| 2 | 1 | 11, F3 | 4, 6, 8, 9 |
| 3 | None | 4, 11 | 1, 5, 7, 9 |
| 4 | 3 | 11, F3 | 2, 6, 8 |
| 5 | None | 6, 11 | 1, 3, 7, 9 |
| 6 | 5 | 11 | 2, 4, 8 |
| 7 | None | 8, 11 | 1, 3, 5, 9 |
| 8 | 7 | 11 | 2, 4, 6 |
| 9 | None | 10 | 1, 3, 5, 7 |
| 10 | 9 | 11 | 2, 4, 6, 8 |
| 11 | 1-10 | Final verification | None |

## Todos
> Implementation + Test = ONE todo. Never separate.
<!-- APPEND TASK BATCHES BELOW THIS LINE WITH edit/apply_patch - never rewrite the headers above. -->
- [x] 1. Add live 9Router chat smoke harness and configurable target
  What to do / Must NOT do: Add a small production-proof harness/config path for OpenAI-compatible chat against `http://127.0.0.1:20228/v1` model `4omc`. Reuse the same transport assumptions as agent LLM chat. CI tests must use a deterministic fake HTTP transport or monkeypatch; the live evidence command must be separate and explicit. Must not hard-code `20228` as the global default or add paid fallbacks.
  Parallelization: Wave 1 | Blocked by: none | Blocks: 2, 11
  References (executor has NO interview context - be exhaustive): `packages/agents/llm/chat.py:78`, `packages/agents/llm/chat.py:100`, `packages/agents/tools/ninerouter_web.py:13`, `packages/agents/tools/ninerouter_web.py:52`, `services/gateway/research_provider_9router.py:24`, `.omo/drafts/pipeline-v2-production-gaps.md`
  Acceptance criteria (agent-executable): A deterministic test proves base URL/model config flows into the OpenAI-compatible request; a live evidence command writes `.omo/evidence/task-1-pipeline-v2-production-gaps.md` containing `/v1/models` with `4omc` and a valid `/v1/chat/completions` response shape, or a clear blocked reason if the service is down.
  QA scenarios (name the exact tool + invocation): Happy: `curl -sS http://127.0.0.1:20228/v1/models` and chat completion with model `4omc`; Failure: point base URL to an unused port and assert the harness reports provider unavailable without claiming success. Evidence `.omo/evidence/task-1-pipeline-v2-production-gaps.md`.
  Commit: Y | feat(provider): add live 9router evidence harness

- [x] 2. Wire 9Router provider evidence into gateway release evidence without mocking production proof
  What to do / Must NOT do: Add gateway/service-level evidence collection that records live provider status and model identity in the existing release evidence flow. Keep live proof optional for CI but mandatory for production-readiness evidence. Must not convert live checks into fake/mock success.
  Parallelization: Wave 2 | Blocked by: 1 | Blocks: 11, F3
  References (executor has NO interview context - be exhaustive): `services/gateway/research_provider_9router.py:28`, `services/gateway/research_provider_9router.py:38`, `services/gateway/research_collector.py:85`, `services/gateway/routers/release_evidence.py`, `services/gateway/tests/test_release_evidence.py`, `.scratch/pipeline-v2/PIPERLINE-V2-GAP-REPORT.md`
  Acceptance criteria (agent-executable): Route/service test proves evidence includes provider base URL, model `4omc`, timestamp, and pass/blocked status; live run appends evidence to `.omo/evidence/task-2-pipeline-v2-production-gaps.md`.
  QA scenarios (name the exact tool + invocation): Happy: run the release evidence endpoint/service with live env and verify provider entry exists; Failure: run with unreachable provider and verify evidence says blocked/unavailable and does not mark pass. Evidence `.omo/evidence/task-2-pipeline-v2-production-gaps.md`.
  Commit: Y | feat(evidence): include live provider readiness proof

- [x] 3. Add a gateway-to-Eta renderer adapter for artifact snapshots
  What to do / Must NOT do: Introduce a small Python gateway adapter that invokes the existing TypeScript renderer boundary (`agent-renderer` or an equivalent package script) with artifact JSON and receives standalone HTML. Process contract: success exits 0 with HTML on stdout and diagnostics-only stderr; failure exits non-zero with a bounded stderr/stdout summary captured by Python; timeout defaults to 30 seconds and is configurable for tests. Normalize errors into typed gateway errors. Must not duplicate Eta/template rendering in Python and must not import services from renderer or packages from apps incorrectly.
  Parallelization: Wave 1 | Blocked by: none | Blocks: 4, 11
  References (executor has NO interview context - be exhaustive): `packages/renderer/src/renderer.ts:32`, `packages/renderer/src/agent-renderer.ts:219`, `packages/renderer/src/eta-engine.ts`, `packages/renderer/__tests__/renderer.test.ts`, `services/gateway/pipeline_v2_snapshot_store.py:40`, `AGENTS.md` package boundary rules
  Acceptance criteria (agent-executable): `pnpm --filter renderer test` passes before integration; gateway adapter unit tests render a minimal lesson/quiz fixture to HTML containing `<!DOCTYPE html>`, `oh-my-class`, no external `http(s)://` assets, and a clear error for malformed artifact JSON, non-zero process exit, and timeout.
  QA scenarios (name the exact tool + invocation): Happy: run adapter against a fixture and inspect saved evidence HTML hash/metadata; Failure: feed malformed artifact JSON and assert typed renderer failure. Evidence `.omo/evidence/task-3-pipeline-v2-production-gaps.md`.
  Commit: Y | feat(renderer): add eta snapshot adapter

- [x] 4. Persist Eta-rendered teacher/student snapshots with version metadata
  What to do / Must NOT do: First inspect all `PipelineV2SnapshotStore.create_snapshot`/`PipelineV2RunStore.create_snapshot` callers and identify the upstream caller(s) that currently supply rendered HTML/version metadata. Then replace/augment that creation path so it stores Eta-rendered `rendered_html`, student-safe HTML, `renderer_version`, `template_version`, `theme_version`, content/html hashes, and standalone validation results in `PipelineV2SnapshotStore`. Preserve preview routes and approval checks. Must not use `renderArtifactSync` as the new production path.
  Parallelization: Wave 2 | Blocked by: 3 | Blocks: 11, F3
  References (executor has NO interview context - be exhaustive): `services/gateway/pipeline_v2_snapshot_store.py:40`, `services/gateway/pipeline_v2_snapshot_store.py:234`, `services/gateway/routers/pipeline_v2_previews.py:54`, `services/gateway/routers/pipeline_v2_previews.py:83`, `services/gateway/quality_gates.py:66`, `packages/renderer/src/renderer.ts:55`
  Acceptance criteria (agent-executable): Evidence names the exact snapshot creation caller(s) changed; snapshot store/integration tests prove duplicate content with renderer/template/theme mismatch is blocked, non-standalone HTML cannot be approved, student preview has no answer-key text, and metadata endpoint returns the Eta versions.
  QA scenarios (name the exact tool + invocation): Happy: create snapshot from fixture, fetch metadata and student/teacher previews; Failure: inject external asset or answer-key leakage and assert validation/approval fails. Evidence `.omo/evidence/task-4-pipeline-v2-production-gaps.md`.
  Commit: Y | feat(snapshots): persist eta-rendered preview snapshots

- [x] 5. Add canonical rubric registry contracts for adaptive judging
  What to do / Must NOT do: Define Pydantic contracts for rubric criteria, rubric versions, judge strategy/adaptation metadata, and registry lookup in `common/contracts` or an appropriate lower-layer quality module. Regenerate TS schemas if generated outputs change. Must not hand-edit generated Zod files.
  Parallelization: Wave 1 | Blocked by: none | Blocks: 6, 11
  References (executor has NO interview context - be exhaustive): `common/contracts/judge_output.py`, `common/contracts/quality.py:8`, `common/schemas/src/generated/judge_output.ts:4`, `packages/quality/layer4_judge/geval.py`, `packages/quality/layer4_judge/majority_vote.py`, `common/contracts/tests/test_quality.py`
  Acceptance criteria (agent-executable): Contract tests prove rubric criterion weights are non-negative and each rubric’s total weight sums to `1.0 ± 0.001`; versions are immutable/hashable; duplicate rubric version IDs fail; generated schema checks pass if regeneration is needed.
  QA scenarios (name the exact tool + invocation): Happy: instantiate a valid default G-Eval rubric and dump/load it; Failure: invalid weight sum or duplicate rubric version raises validation error. Evidence `.omo/evidence/task-5-pipeline-v2-production-gaps.md`.
  Commit: Y | feat(quality): add versioned rubric contracts

- [x] 6. Integrate adaptive LLM judge with deterministic quality gates
  What to do / Must NOT do: Add a judge interface that selects rubric/version by artifact type/failure context, calls the LLM judge through existing LLM transport metadata, and returns `JudgeOutput` plus rubric provenance. Deterministic gates remain authoritative hard blocks. Must not let a high LLM score override missing doctype, external assets, answer-key leakage, PII, or teacher gate state.
  Parallelization: Wave 2 | Blocked by: 5 | Blocks: 11
  References (executor has NO interview context - be exhaustive): `services/gateway/quality_gates.py:39`, `services/gateway/quality_gates.py:66`, `services/gateway/quality_gates.py:116`, `common/contracts/judge_output.py`, `packages/agents/llm/chat.py:78`, `packages/quality/tests/test_layer4_judge.py`
  Acceptance criteria (agent-executable): Tests prove rubric selection by artifact type, LLM judge result carries rubric provenance, deterministic hard blocks fail even with passing judge score, and judge-unavailable path fails closed/escalates per configured strategy.
  QA scenarios (name the exact tool + invocation): Happy: judge a valid artifact with fake deterministic LLM response; Failure: judge returns pass for external-asset snapshot and final report still fails. Evidence `.omo/evidence/task-6-pipeline-v2-production-gaps.md`.
  Commit: Y | feat(quality): integrate adaptive judge registry

- [x] 7. Add prompt compiler with overlay governance and provenance
  What to do / Must NOT do: Build a compiler around `PromptRegistry` that accepts a registered module, typed variables, and approved overlays; emits compiled prompt text plus `PromptMetadata`; rejects unknown variables, duplicate overlay IDs, hash drift, and secret-like content before LLM calls. Must not introduce ad hoc string concatenation in callers.
  Parallelization: Wave 1 | Blocked by: none | Blocks: 8, 11
  References (executor has NO interview context - be exhaustive): `packages/agents/prompts/registry.py:35`, `packages/agents/prompts/registry.py:95`, `packages/agents/prompts/drift.py:39`, `packages/agents/prompts/seed.py:265`, `packages/agents/llm/prompt_metadata.py:49`, `packages/agents/llm/prompt_gate.py:26`, `packages/agents/prompts/tests/test_registry.py`
  Acceptance criteria (agent-executable): Prompt tests prove successful compilation, overlay order determinism, compiled hash generation, missing variable rejection, undeclared variable rejection, secret-like overlay rejection, and drift rejection.
  QA scenarios (name the exact tool + invocation): Happy: compile seeded judge/planner prompt with a safe overlay and assert metadata hashes; Failure: overlay contains a token-like string or unknown variable and compiler rejects before LLM transport. Evidence `.omo/evidence/task-7-pipeline-v2-production-gaps.md`.
  Commit: Y | feat(prompts): add governed prompt compiler

- [x] 8. Add prompt evaluation harness and migrate LLM callers to compiler metadata
  What to do / Must NOT do: Add deterministic eval fixtures for seeded judge/planner/content-creator prompt modules and migrate only newly touched judge/planner/content-generation LLM paths plus shared `complete_json_chat` metadata support to attach compiler metadata. Preserve existing prompt gate and transport policy. Must not send raw uncompiled prompt strings from newly touched call sites. Do not attempt a repo-wide migration of historical raw prompt callers unless one blocks these paths.
  Parallelization: Wave 2 | Blocked by: 7 | Blocks: 11
  References (executor has NO interview context - be exhaustive): `packages/agents/llm/chat.py:87`, `packages/agents/llm/chat.py:127`, `packages/agents/llm/prompt_metadata.py:77`, `packages/agents/prompts/seed.py:12`, `packages/agents/prompts/tests/test_registry.py`, `packages/agents/tests/llm/test_transport_policy.py`
  Acceptance criteria (agent-executable): Eval tests run without network and assert expected sections/schema metadata for the scoped modules; transport tests prove tags/metadata include prompt provenance for the migrated judge/planner/content-generation paths; evidence lists every migrated call site and explicitly states no repo-wide migration was attempted.
  QA scenarios (name the exact tool + invocation): Happy: run prompt eval harness on seeded modules and record pass summary; Failure: mutate fixture expected schema/hash and assert eval fails. Evidence `.omo/evidence/task-8-pipeline-v2-production-gaps.md`.
  Commit: Y | feat(prompts): add prompt eval provenance

- [x] 9. Implement queued/delayed backpressure state and worker dequeue semantics
  What to do / Must NOT do: Extend backpressure to count both active runs and queued jobs/runs. Add `RunJobStatus.QUEUED` and nullable `RunJob.eligible_at` to the model/API read shape; keep `RunJobKind` unchanged (`START`/`RESUME`) and public `RunStatus.PENDING` for queued runs. When active capacity is saturated but queued capacity remains, create a queued job/run event with `status=QUEUED` and `eligible_at` set or null per promotion design; workers claim only `PENDING` jobs whose `eligible_at` is null or due, and promotion from queued to pending occurs only when capacity allows. When queued capacity is exhausted, reject clearly. Must not silently create active work beyond limits.
  Parallelization: Wave 1 | Blocked by: none | Blocks: 10
  References (executor has NO interview context - be exhaustive): `services/gateway/backpressure.py:36`, `services/gateway/backpressure.py:50`, `services/gateway/pipeline_v2_models.py:65`, `services/gateway/pipeline_v2_models.py:203`, `services/gateway/pipeline_v2_job_store.py:41`, `services/gateway/pipeline_v2_job_store.py:81`, `services/gateway/run_creation.py:41`, `services/gateway/run_creation.py:105`, `services/gateway/pipeline_v2_worker.py:42`, `services/gateway/pipeline_v2_worker.py:58`, `services/gateway/tests/test_pipeline_v2_worker.py`, `services/gateway/tests/test_operations_hardening.py`
  Acceptance criteria (agent-executable): Tests cover under-limit start, active-limit queue, queue-limit reject, global-limit queue/reject, per-teacher isolation, worker skipping queued/ineligible jobs, worker starting queued jobs after capacity frees, idempotency behavior, and cancellation of queued jobs.
  QA scenarios (name the exact tool + invocation): Happy: create runs until active limit then observe queued response and later worker dequeue after completing/cancelling one active run; Failure: exceed queued limit and assert clear rejection with no job leak. Evidence `.omo/evidence/task-9-pipeline-v2-production-gaps.md`.
  Commit: Y | feat(backpressure): queue delayed pipeline runs

- [x] 10. Add and verify the queued-job Alembic migration
  What to do / Must NOT do: Add the Alembic migration for queued backpressure schema changes: `RunJobStatus.QUEUED` compatibility for the non-native enum string column, nullable `eligible_at` timestamptz on `public.run_jobs`, and any index needed for claim/promote queries. Include downgrade only if this repository’s existing migration style includes downgrades; otherwise follow repo convention. Must not add a public `RunStatus.QUEUED` unless implementation proves it is unavoidable and the plan is updated.
  Parallelization: Wave 2 | Blocked by: 9 | Blocks: 11
  References (executor has NO interview context - be exhaustive): `services/gateway/alembic/versions/010_run_budget_ledgers.py`, `services/gateway/pipeline_v2_models.py:65`, `services/gateway/pipeline_v2_models.py:203`, `services/gateway/pipeline_v2_job_store.py:81`, `services/gateway/tests/test_budget_db.py`, `services/gateway/tests/test_pipeline_v2_job_store_leases.py`
  Acceptance criteria (agent-executable): Migration applies cleanly to an empty/test DB and upgraded model queries can enqueue, list, skip, promote, and claim jobs with `eligible_at`; tests prove `eligible_at` is nullable and claim queries ignore queued/ineligible jobs.
  QA scenarios (name the exact tool + invocation): Happy: run Alembic upgrade against test DB and enqueue/claim a due job; Failure: create queued/future job and assert `claim_next` returns no job until promotion/due eligibility. Evidence `.omo/evidence/task-10-pipeline-v2-production-gaps.md`.
  Commit: Y | db(backpressure): add queued job eligibility migration

- [x] 11. Run full production-readiness verification and evidence consolidation
  What to do / Must NOT do: Run all relevant linters/tests/builds, live provider smoke, API/preview agent-executed surface QA, and evidence report generation. Fix defects found only in the owning slice. Pre-existing or unrelated failures outside the five slices are recorded as known issues and not fixed in this plan. Must not declare done from unit tests alone.
  Parallelization: Wave 3 | Blocked by: 1-10 | Blocks: Final verification
  References (executor has NO interview context - be exhaustive): `AGENTS.md` Manual QA Gate, `.scratch/pipeline-v2/PIPERLINE-V2-GAP-REPORT.md`, `services/gateway/tests/`, `packages/agents/prompts/tests/`, `packages/renderer/__tests__/`, `apps/web`, `.omo/drafts/pipeline-v2-production-gaps.md`
  Acceptance criteria (agent-executable): The evidence file records exact commands and outcomes for: `uv run ruff check services/gateway packages/agents packages/quality common/contracts tests`; `uv run basedpyright services/gateway packages/agents packages/quality common/contracts` when local config permits; `uv run pytest services/gateway/tests/ packages/agents/prompts/tests/ packages/quality/tests/ common/contracts/tests/ tests/e2e/ --tb=short`; `pnpm --filter renderer test`; `pnpm --filter web test`; `pnpm --filter web build`; live `/v1/models` and `/v1/chat/completions` against `http://127.0.0.1:20228/v1` model `4omc`; API/preview surface QA through exact curl/TestClient/browser commands. Any pre-existing unrelated failure is named with evidence and not hidden.
  QA scenarios (name the exact tool + invocation): Happy: run the full listed verification commands and live smoke; Failure: intentionally run one negative-provider/unreachable check and one invalid snapshot/prompt/backpressure failure case to prove fail-closed behavior. Evidence `.omo/evidence/task-11-pipeline-v2-production-gaps.md` and `.omo/evidence/final-pipeline-v2-production-gaps.md`.
  Commit: Y | test(pipeline): consolidate production readiness evidence

## Final verification wave
> Runs in parallel after ALL todos. ALL must APPROVE. Surface results and wait for the user's explicit okay before declaring complete.
- [x] F1. Plan compliance audit: verify every Must Have/Guardrail maps to code, tests, and evidence; reject if any todo was self-reported without command evidence.
- [x] F2. Code quality review: read changed files for boundary violations, oversized modules, duplicated rendering/judge/prompt logic, defensive slop, and forbidden provider fallbacks.
- [x] F3. Agent-executed surface QA: exercise live 9Router smoke, run creation/backpressure API, snapshot metadata/preview/approval path, and at least one rendered artifact through curl/TestClient/browser automation.
- [x] F4. Scope fidelity: confirm no teacher gate bypass, no generated-schema hand edits, no product-code naming regression against the user's no-`pipeline_v2_` preference beyond existing conventions, and no unrelated changes.

## Commit strategy
- Keep commits atomic by slice if the user asks for commits:
  1. `feat(provider): add live 9router evidence harness`
  2. `feat(renderer): persist eta-rendered snapshots`
  3. `feat(quality): add adaptive judge rubrics`
  4. `feat(prompts): govern compiled prompt overlays`
  5. `feat(backpressure): queue delayed pipeline runs`
  6. `db(backpressure): add queued job eligibility migration`
  7. `test(pipeline): consolidate readiness evidence`
- Before any commit, run `GIT_MASTER=1 git status`, `GIT_MASTER=1 git diff`, and `GIT_MASTER=1 git log --oneline -10`; stage only intended files.

## Success criteria
- Live local 9Router model `4omc` has recorded pass/blocked evidence from `http://127.0.0.1:20228/v1` without mocks.
- Pipeline V2 snapshot creation uses Eta-rendered standalone HTML and persisted metadata; previews/approval continue to enforce access and quality.
- Adaptive judge/rubric path is versioned, typed, tested, and cannot override deterministic hard blocks.
- Prompt compilation/overlay governance emits provenance metadata and rejects drift, unsafe variables, and secret-like content.
- Backpressure queues/delays within configured capacity and rejects clearly when both active and queued capacity are exhausted.
- All touched files pass lint/type/test verification or documented pre-existing unrelated failures.
- Agent-executed surface QA drives the implemented surfaces, not just source inspection.
