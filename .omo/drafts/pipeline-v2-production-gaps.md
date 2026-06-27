---
slug: pipeline-v2-production-gaps
status: awaiting-approval
intent: clear
pending-action: execute .omo/plans/pipeline-v2-production-gaps.md after explicit start signal
approach: Productionize Pipeline V2 through five independently verifiable slices: live 9Router evidence, Eta-rendered snapshot creation, adaptive judge/rubric registry, prompt compiler/overlay governance, and queued backpressure worker flow.
---

# Draft: pipeline-v2-production-gaps

## Components (topology ledger)
<!-- Lock the SHAPE before depth. One row per top-level component that can succeed or fail independently. -->
<!-- id | outcome (one line) | status: active|deferred | evidence path -->
| C1-live-9router | Gateway/agent LLM evidence proves `http://127.0.0.1:20228/v1` exposes and can use model `4omc`; no mock-only proof for production claims. | active | `curl -sS --max-time 5 http://127.0.0.1:20228/v1/models` returned `4omc`; `packages/agents/llm/chat.py`; `packages/agents/tools/ninerouter_web.py`; `services/gateway/research_provider_9router.py` |
| C2-eta-snapshots | Pipeline V2 snapshot creation uses the async Eta renderer surface instead of legacy/manual HTML, preserving standalone/student-vs-teacher preview invariants. | active | `packages/renderer/src/renderer.ts`; `packages/renderer/src/agent-renderer.ts`; `services/gateway/pipeline_v2_snapshot_store.py`; `services/gateway/routers/pipeline_v2_previews.py` |
| C3-adaptive-judge | Quality review uses a versioned rubric registry and adaptive judge path grounded in canonical contracts; deterministic gates still fail closed. | active | `common/contracts/judge_output.py`; `common/contracts/quality.py`; `services/gateway/quality_gates.py`; `packages/quality/layer4_judge/*` |
| C4-prompt-governance | Prompt use is compiler-mediated, hash/version tracked, overlay-aware, and regression-evaluable without leaking secrets or bypassing prompt gates. | active | `packages/agents/prompts/registry.py`; `packages/agents/prompts/drift.py`; `packages/agents/prompts/seed.py`; `packages/agents/llm/prompt_metadata.py`; `packages/agents/llm/prompt_gate.py` |
| C5-queued-backpressure | Run creation queues/delays excess work within configured limits and workers dequeue when capacity returns instead of only hard-blocking teachers. | active | `services/gateway/backpressure.py`; `services/gateway/run_creation.py`; `services/gateway/routers/pipeline_v2_runs.py`; `services/gateway/pipeline_v2_worker.py`; `services/gateway/pipeline_v2_job_store.py` |

## Open assumptions (announced defaults)
<!-- Record any default you adopt instead of asking, so the user can veto it at the gate. -->
<!-- assumption | adopted default | rationale | reversible? -->
| Live provider base | Use `http://127.0.0.1:20228/v1` and model `4omc` for live smoke/evidence. | User specified port/model; live models endpoint confirms `4omc`. | Yes, config/env can change it. |
| Existing 9Router web tool defaults | Keep search/fetch paths at the existing `4omc.search` and `4omc.fetch` request contracts unless live evidence proves the endpoint changed. | Existing provider tests and typed models already use these contracts; changing them would mix research-tool work with chat model proof. | Yes. |
| Renderer bridge | Use the existing TypeScript CLI surface in `packages/renderer/src/agent-renderer.ts` or a small Node script wrapper from gateway tests rather than importing TS into Python. | Preserves package boundaries; Python gateway may invoke the renderer as an external process without `packages/renderer` importing services. | Yes. |
| Rubric source of truth | Put Python rubric/judge validation contracts in `common/contracts`; keep TS generated schemas derived, not hand-edited. | AGENTS invariant requires Pydantic validation contracts in `common/contracts`; generated TS files are marked do-not-edit. | Yes but contract names become durable. |
| Prompt overlays | Treat overlays as registered, typed modules/layers with IDs, versions, content hashes, and allowlisted variables; do not permit ad hoc string concatenation in LLM callers. | Existing registry/drift/prompt gate already support provenance and prompt-size/secret protection. | Yes. |
| Backpressure behavior | Add `RunJobStatus.QUEUED` plus nullable `RunJob.eligible_at` (`DateTime(timezone=True)`, DB `timestamptz`) via Alembic; keep `RunJobKind` unchanged and keep public `RunStatus.PENDING` for queued runs until the worker promotes/claims work. Reject once active and queued capacity are both exhausted. | The job model currently has no queued state or eligibility column, while avoiding a new public run status minimizes API churn. | Mostly; migration required. |
| Test strategy | Tests-after for this production-hardening plan, plus live smoke and agent-executed surface QA at final verification. | Work spans existing behavior and integration seams; deterministic tests lock edge cases while live `9Router` evidence proves the provider. | Yes. |

## Findings (cited - path:lines)
- `packages/agents/tools/ninerouter_web.py:13` still defaults to `http://localhost:20128/v1`; production live proof must support overriding this to `http://127.0.0.1:20228/v1` without changing tests to mocks only.
- `packages/agents/tools/ninerouter_web.py:20` and `packages/agents/tools/ninerouter_web.py:29` type search/fetch as `4omc.search` and `4omc.fetch`; live chat evidence for `4omc` should be added separately from research web-tool contracts.
- `curl -sS --max-time 5 http://127.0.0.1:20228/v1/models` returned a model list containing `{ "id": "4omc", "owned_by": "combo" }`, so the specified live target exists locally.
- `packages/agents/llm/chat.py:100` creates an OpenAI-compatible `AsyncOpenAI` client from `LLM.base_url`, so live `4omc` smoke can use the same transport policy by configuring env/settings.
- `services/gateway/research_provider_9router.py:24` adapts the `NineRouterWebClient` into gateway research providers; this is the seam for live search/fetch evidence and edge-case tests.
- `packages/renderer/src/renderer.ts:32` exposes the desired async Eta renderer `renderArtifact<T>()`; `packages/renderer/src/renderer.ts:55` is only legacy sync/manual HTML and should not be the new snapshot path.
- `packages/renderer/src/agent-renderer.ts:219` already reads JSON from stdin and writes rendered HTML to stdout, making it a practical process boundary for Python gateway integration.
- `services/gateway/routers/pipeline_v2_previews.py:54` serves stored student/teacher rendered HTML directly from snapshots, so snapshot creation must store both variants and metadata correctly before preview routes are meaningful.
- `services/gateway/pipeline_v2_snapshot_store.py:40` stores `renderer_version`, `template_version`, `theme_version`, `rendered_html`, `student_rendered_html`, and `standalone_valid`; this is the persistence target for Eta-rendered snapshots.
- `common/contracts/quality.py:8` owns failure classes/healing strategies; new judge/rubric validation contracts belong in `common/contracts` per invariant.
- `services/gateway/quality_gates.py:39` implements deterministic artifact validation and `services/gateway/quality_gates.py:66` validates snapshots; LLM judge must augment, not bypass, these fail-closed gates.
- `common/schemas/src/generated/judge_output.ts:4` says generated schemas must not be edited manually, so any JudgeOutput/rubric schema change must regenerate TS schemas.
- `packages/agents/prompts/registry.py:95` provides versioned prompt registration; `packages/agents/prompts/drift.py:39` detects drift; `packages/agents/llm/prompt_metadata.py:49` builds provenance metadata; `packages/agents/llm/prompt_gate.py:26` enforces prompt-size/secret gates.
- `services/gateway/backpressure.py:36` already has `max_queued_runs_per_teacher`, but `services/gateway/backpressure.py:50` only returns allowed/rejected based on active counts; queued capacity is not part of the decision yet.
- `services/gateway/run_creation.py:105` enqueues a START job for ready runs and `services/gateway/run_creation.py:162` briefly enqueues then cancels gate-blocked jobs; delayed queue semantics should be modeled explicitly rather than overloaded.
- `services/gateway/pipeline_v2_worker.py:42` claims the next job and `services/gateway/pipeline_v2_worker.py:58` loops until idle; it is the right dequeue path once queued jobs become eligible.
- `services/gateway/pipeline_v2_models.py:65` defines `RunJobStatus` without `queued`; `services/gateway/pipeline_v2_models.py:203` defines `RunJob` without `eligible_at`; `services/gateway/pipeline_v2_job_store.py:81` currently claims `pending`/expired `running` jobs ordered by creation time.
- `services/gateway/pipeline_v2_store.py:220` forwards snapshot creation to `PipelineV2SnapshotStore.create_snapshot`; this is a persistence wrapper, not an Eta rendering caller, so implementation must inspect and rewire upstream snapshot creation/callers before changing storage.
- `services/gateway/pipeline_v2_snapshot_store.py:268` already validates renderer/template/theme version mismatches; the remaining gap is the caller that supplies rendered HTML and version metadata.
- `packages/agents/llm/chat.py:78` is the central JSON chat transport and `packages/agents/llm/chat.py:112` has a small direct helper surface, so prompt compiler migration is scoped to newly touched judge/planner/content-generation paths and shared metadata support, not every historical caller.

## Decisions (with rationale)
- D1. Keep implementation slices independent: provider proof, renderer snapshots, judge/rubrics, prompt governance, and backpressure can be tested and rolled back separately.
- D2. Do not rename new files/functions with `pipeline_v2_` unless an existing convention already requires it; user explicitly called that naming unclean.
- D3. Use config/env for the live 9Router target; do not hard-code `20228` globally because existing docs and defaults still mention `20128`.
- D4. For snapshots, prefer Eta renderer output through the stable TS surface and persist the resulting HTML/metadata in the existing snapshot store; do not duplicate template rendering in Python.
- D5. For judge/rubrics, add canonical Python contracts and registry in shared/common or quality package surfaces, then expose version metadata to gateway quality review; do not hand-edit generated Zod.
- D6. For prompts, compile registered modules plus overlays through a typed compiler that emits prompt metadata and rejects undeclared variables/secrets before LLM calls.
- D7. For backpressure, add `RunJobStatus.QUEUED` and nullable `RunJob.eligible_at` via Alembic migration; keep `RunJobKind` unchanged (`START`/`RESUME`) and keep public `RunStatus.PENDING` for queued runs. `claim_next` must only claim `PENDING` jobs whose `eligible_at` is null or due; queued jobs become pending/eligible only when capacity allows.
- D8. Verification must include deterministic unit/integration tests, full affected Python/TS suites, and a live `4omc` smoke/evidence file.
- D9. Agent-executed manual QA means scripted surface use through curl/browser/API/CLI by the agent, not a human tester. Final verification must name exact commands and endpoints.
- D10. Renderer process contract: success is exit 0 with HTML on stdout and diagnostics-only stderr; failure is non-zero exit with a bounded stderr/stdout summary captured by Python; timeout defaults to 30 seconds and is configurable for tests.
- D11. Prompt caller migration is scoped to newly touched judge/planner/content-generation paths plus shared `complete_json_chat` metadata support; unrelated historical call sites are not migrated unless they block those paths.

## Scope IN
- Live 9Router smoke/evidence harness for OpenAI-compatible chat at `http://127.0.0.1:20228/v1`, model `4omc`, plus research provider smoke where applicable.
- Configurable provider target defaults with tests that do not require live service for CI.
- Gateway snapshot creation path that uses Eta-rendered standalone HTML and records renderer/template/theme versions.
- Student/teacher preview preservation and snapshot standalone quality validation.
- Versioned rubric registry and adaptive LLM judge interface tied to `JudgeOutput` and deterministic gate output.
- Prompt compiler with typed variables, overlay governance, hash/version drift checks, evaluation fixtures, and metadata propagation.
- Queued/delayed backpressure processing including queued count limits, eligibility/dequeue behavior, and API responses/events.
- Alembic migration for queued job status/eligibility changes and migration tests.
- Comprehensive tests for happy paths, capacity edges, malformed input, stale versions, unreachable provider, non-standalone snapshots, prompt drift, overlay misuse, and judge fail-closed behavior.
- Final evidence ledger under `.omo/evidence/` plus release evidence where the existing evidence route supports it.

## Scope OUT (Must NOT have)
- Must not bypass teacher gates or self-approve blueprint/content approvals.
- Must not move Pydantic validation contracts out of `common/contracts`.
- Must not make `packages/agents` import from `services/*` or `apps/*`.
- Must not replace deterministic fail-closed quality gates with an LLM-only judge.
- Must not fake live 9Router proof; live evidence must say skipped/blocked only if service is unreachable, not claim pass.
- Must not hand-edit generated `common/schemas/src/generated/*` files except via the schema generator.
- Must not add paid fallbacks or direct-provider bypasses for 9Router.
- Must not add speculative compatibility paths for unreleased draft shapes.
- Must not weaken existing tests or delete failing tests.
- Must not fix unrelated verification failures outside the five production-hardening slices; document them as known issues instead.

## Open questions
- None blocking. Defaults above are reversible and match the user’s stated production-ready/live-provider preference.

## Approval gate
status: awaiting-approval
pending action: execute .omo/plans/pipeline-v2-production-gaps.md via implementation worker after explicit start signal
brief: Implement five production-hardening slices with tests-after and live `4omc` evidence. No product code has been changed by this planning step.
<!-- When exploration is exhausted and unknowns are answered, set status: awaiting-approval. -->
<!-- That durable record is the loop guard: on a later turn read it and resume at the gate instead of re-running exploration. -->
