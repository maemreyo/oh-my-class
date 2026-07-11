# artifact-document-v2-cutover - Work Plan

## TL;DR (For humans)
<!-- Fill this LAST, after the detailed plan below is written, so it summarizes the REAL plan. -->
<!-- Plain English for a non-engineer: NO file paths, NO todo numbers, NO wave/agent/tool names. -->

**What you'll get:** New teaching-pack runs persist immutable V2 documents and separate teacher-only answer sets atomically. Existing V1 artifacts stay previewable as visibly legacy content while student documents, snapshots, and exports remain answer-free.

**Why this approach:** A package-neutral V1↔V2 mapper protects the graph, quality, renderer, and exporter boundaries during the cutover. The gateway owns transactional writes while agents retain only neutral ports and compact references.

**What it will NOT do:** It will not redesign specialist pedagogy, add a long-lived production dual writer, or silently fall back to V1 persistence for new runs.

**Effort:** XL
**Risk:** High - type conversion, atomicity, and answer isolation cross generation, editing, preview, and export surfaces.
**Decisions to sanity-check:** Immediate V2-only new writes with V1 read-only compatibility; shared contract mapper; startup gate for active V1 runs.

Your next move: execute this plan. Full implementation detail follows below.

---

> TL;DR (machine): XL/high-risk V2 persistence cutover with atomic AnswerSet, answer-free student projections, V1 read compatibility, invalidation, and live-path evidence.

## Scope
### Must have
 - V2-only persistence for new queued teaching-pack runs through a gateway-owned adapter.
 - Explicit V1↔V2 projection mapping, atomic document/AnswerSet writes, answer-free persisted student documents, V1 legacy reads, and edit invalidation.
 - Agent-executed transaction, leakage, migration, invalidation, and queued-run evidence.
### Must NOT have (guardrails, anti-slop, scope boundaries)
 - No agents-to-gateway imports, no silent conversion data loss, no long-lived dual writer, and no pedagogical specialist rewrite.

## Verification strategy
> Zero human intervention - all verification is agent-executed.
- Test decision: TDD + pytest, existing FastAPI/TestClient and SQLAlchemy integration fixtures.
- Evidence: `.omo/evidence/task-<N>-artifact-document-v2-cutover.txt`.

## Execution strategy
### Parallel execution waves
> Target 5-8 todos per wave. Fewer than 3 (except the final) means you under-split.

### Dependency matrix
| Todo | Depends on | Blocks | Can parallelize with |
| --- | --- | --- | --- |

## Todos
> Implementation + Test = ONE todo. Never separate.
<!-- APPEND TASK BATCHES BELOW THIS LINE WITH edit/apply_patch - never rewrite the headers above. -->
- [ ] 1. Add explicit V1-to-V2 and V2-to-V1 projection mapping with lossless validation for each supported document payload.
  What to do / Must NOT do: Create a neutral `common/contracts` mapper that returns typed domain results or raises an explicit conversion error. Must NOT discard unsupported sections or answer-bearing values.
  Parallelization: Wave 1 | Blocked by: none | Blocks: 2, 3, 4
  References (executor has NO interview context - be exhaustive): `common/contracts/artifact.py`; `common/contracts/artifact_document.py`; `common/contracts/answer_set.py`; `packages/agents/teaching_pack/content_orchestrator.py:48`.
  Acceptance criteria (agent-executable): pytest verifies V1→V2→V1 parity for all supported artifacts and rejection for an unmappable component.
  QA scenarios (name the exact tool + invocation): `uv run pytest common/contracts/tests/test_artifact_projection_mapper.py -q`; happy: quiz and lesson round-trip; failure: unknown component produces typed conversion failure. Evidence `.omo/evidence/task-1-artifact-document-v2-cutover.txt`.
  Commit: Y | `feat(contracts): map legacy artifact projections to V2 documents`
- [ ] 2. Extend the agents persistence port with an atomic specialist result that separates V2 document, answer set, dependencies, variants, quality state, and provenance.
  What to do / Must NOT do: Keep the port package-owned and gateway-free. Must NOT store AnswerSet in student metadata or graph checkpoints.
  Parallelization: Wave 1 | Blocked by: 1 | Blocks: 3, 5
  References (executor has NO interview context - be exhaustive): `packages/agents/teaching_pack/content_orchestrator.py:48`; `packages/agents/teaching_pack/generate_one_artifact.py`; `common/contracts/answer_set.py`.
  Acceptance criteria (agent-executable): specialist generation produces a compact reference and never contains answer markers in its persisted student projection.
  QA scenarios (name the exact tool + invocation): `uv run pytest packages/agents/tests/teaching_pack/test_generate_one_artifact.py packages/agents/tests/teaching_pack/test_content_orchestrator.py -q`; happy: quiz yields separate answer set; failure: invalid answer derivation produces no persistence call. Evidence `.omo/evidence/task-2-artifact-document-v2-cutover.txt`.
  Commit: Y | `feat(agents): persist atomic V2 specialist results`
- [ ] 3. Implement the gateway V2-backed projection adapter and transactional document/AnswerSet persistence.
  What to do / Must NOT do: Compose `ArtifactDocumentStore` behind the agents port, convert using task 1, and explicitly scope transaction rollback. Must NOT write a new V1 LangGraph authority.
  Parallelization: Wave 2 | Blocked by: 1, 2 | Blocks: 4, 5
  References (executor has NO interview context - be exhaustive): `services/gateway/artifact_document_store.py:57`; `services/gateway/main.py`; `services/gateway/teaching_pack_executor.py`; `packages/agents/teaching_pack/content_orchestrator.py:108`.
  Acceptance criteria (agent-executable): injected AnswerSet insert failure leaves zero new document and answer rows; retry writes exactly one version pair.
  QA scenarios (name the exact tool + invocation): `uv run pytest services/gateway/tests/test_artifact_document_transaction.py services/gateway/tests/test_artifact_document_store.py -q`; happy: document and answer set persist; failure: answer insertion fails and transaction rolls back. Evidence `.omo/evidence/task-3-artifact-document-v2-cutover.txt`.
  Commit: Y | `feat(gateway): persist teaching artifacts through V2 documents`
- [ ] 4. Wire gateway composition, V1 legacy reads, and a startup gate that prevents V2 activation with in-flight V1 runs.
  What to do / Must NOT do: Make V2 the only new writer. Keep V1 as read-only preview input with a legacy marker and metric. Must NOT use silent runtime fallback.
  Parallelization: Wave 2 | Blocked by: 3 | Blocks: 5
  References (executor has NO interview context - be exhaustive): `services/gateway/main.py`; `services/gateway/artifact_document_store.py`; `services/gateway/teaching_pack_completion.py`; `services/gateway/teaching_pack_snapshot_models.py`.
  Acceptance criteria (agent-executable): live composition selects V2 writer; legacy snapshot returns a marked source; active V1 job blocks activation.
  QA scenarios (name the exact tool + invocation): `uv run pytest services/gateway/tests/test_v1_read_compatibility.py services/gateway/tests/test_v2_writer_activation.py -q`; happy: V2 active on empty queue; failure: pending legacy run returns typed activation error. Evidence `.omo/evidence/task-4-artifact-document-v2-cutover.txt`.
  Commit: Y | `feat(gateway): activate V2 writer with legacy read guard`
- [ ] 5. Make answer-key derivation and edit invalidation version-aware.
  What to do / Must NOT do: Resolve derived answer keys from persisted AnswerSet versions; on question, option, section, or document edit, mark derived answer keys, snapshots, and exports stale without changing historical rows. Must NOT rehydrate answer data into student artifacts.
  Parallelization: Wave 3 | Blocked by: 2, 3, 4 | Blocks: 6
  References (executor has NO interview context - be exhaustive): `packages/agents/teaching_pack/generate_one_artifact.py`; `services/gateway/artifact_document_edit_service.py`; `services/gateway/artifact_document_models.py`; `services/gateway/teaching_pack_export_writer.py`.
  Acceptance criteria (agent-executable): all edit scopes create a new document version and invalidate dependent material, preserving the prior version and answer set.
  QA scenarios (name the exact tool + invocation): `uv run pytest services/gateway/tests/test_answer_invalidation.py services/gateway/tests/test_artifact_document_editing.py -q`; happy: edit invalidates derived outputs; failure: stale base version raises conflict and invalidates nothing. Evidence `.omo/evidence/task-5-artifact-document-v2-cutover.txt`.
  Commit: Y | `feat(gateway): invalidate derived artifacts after V2 edits`
- [ ] 6. Prove the full V2 lifecycle and answer-leakage boundary through queued-run, preview, export, security, migration, and schema-parity tests.
  What to do / Must NOT do: Add recursive persisted-JSON and output scans for answer markers. Exercise real API-created queued run through V2 store, preview, and export with one stable document ID/version. Must NOT accept mock-only evidence.
  Parallelization: Wave 4 | Blocked by: 3, 4, 5 | Blocks: final verification
  References (executor has NO interview context - be exhaustive): `tests/integration`; `tests/security`; `services/gateway/routers`; `services/gateway/teaching_pack_completion.py`; `scripts/verify_schema_parity.py`.
  Acceptance criteria (agent-executable): integration output records V2 document/AnswerSet identity; student JSON/HTML/SSE/cache/export scans contain no answer fields; V1 fixture is legacy-previewable.
  QA scenarios (name the exact tool + invocation): `uv run pytest tests/integration/test_v2_generation_lifecycle.py tests/security/test_answer_leakage_vectors.py -q`; happy: queued run carries one V2 ID/version through preview/export; failure: seeded answer marker is blocked before persistence/export. Evidence `.omo/evidence/task-6-artifact-document-v2-cutover.txt`.
  Commit: Y | `test(v2-cutover): prove live persistence and answer isolation`

## Final verification wave
> Runs in parallel after ALL todos. ALL must APPROVE. Surface results and wait for the user's explicit okay before declaring complete.
- [ ] F1. Plan compliance audit
- [ ] F2. Code quality review
- [ ] F3. Real manual QA
- [ ] F4. Scope fidelity

## Commit strategy
One atomic commit per completed todo; preserve pre-existing staged/unstaged work and stage only files owned by the todo.

## Success criteria
Every #463 acceptance criterion is proven through the real queued-run surface: new writes are V2-only, documents and required answer sets are atomic, student outputs are answer-free, edits invalidate derived data immutably, and V1 reads are marked legacy.
