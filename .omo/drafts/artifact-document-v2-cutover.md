---
slug: artifact-document-v2-cutover
status: awaiting-approval
intent: clear
pending-action: write .omo/plans/artifact-document-v2-cutover.md
approach: Replace the production LangGraph V1 writer with a gateway-composed V2 persistence adapter; preserve V1 only through a visibly legacy read adapter.
---

# Draft: artifact-document-v2-cutover

## Components (topology ledger)
<!-- Lock the SHAPE before depth. One row per top-level component that can succeed or fail independently. -->
<!-- id | outcome (one line) | status: active|deferred | evidence path -->
| v2-write-adapter | Queued generation persists immutable ArtifactDocument and optional AnswerSet atomically through the gateway-owned store. | active | packages/agents/teaching_pack/content_orchestrator.py; services/gateway/artifact_document_store.py |
| answer-separation | Student document serialization excludes answers and derived answer keys resolve from persisted AnswerSet versions. | active | packages/agents/teaching_pack/generate_one_artifact.py; common/contracts/answer_set.py |
| projection-compatibility | Quality, preview, renderer, and exports consume V2-backed projections while V1 snapshots remain visibly legacy-readable. | active | packages/agents/teaching_pack/quality_runtime.py; services/gateway/teaching_pack_completion.py |
| invalidation | Edits invalidate answers, answer keys, snapshots, and exports without mutating historical versions. | active | services/gateway/artifact_document_edit_service.py; services/gateway/artifact_document_models.py |
| live-evidence | Queued-run, transaction-failure, answer-leakage, and V1-read tests prove the live path. | active | services/gateway/tests; tests/integration |

## Open assumptions (announced defaults)
<!-- Record any default you adopt instead of asking, so the user can veto it at the gate. -->
<!-- assumption | adopted default | rationale | reversible? -->
| Production cutover | V2-only writes immediately; V1 is read-only with legacy markers and fallback metrics. | #463 requires no new V1 authority and bounds V1 as a compatibility adapter. | No, but required by issue. |
| Migration seam | Keep the agents-facing projection port temporarily, with a gateway V2 adapter behind it. | Avoids rewriting quality, renderer, and export consumers during the persistence cutover. | Yes, remove after downstream V2 consumers migrate. |
| Test strategy | TDD for all new cutover and security boundaries. | #463 explicitly requires transaction, leakage, live-path, invalidation, migration, and export evidence. | No. |

## Findings (cited - path:lines)
 - The live graph persists `ArtifactContent` through `ArtifactContentStore`, and its LangGraph adapter serializes V1 JSON into `BaseStore`: `packages/agents/teaching_pack/content_orchestrator.py:48`, `packages/agents/teaching_pack/content_orchestrator.py:108`.
 - Gateway composition currently supplies that LangGraph adapter, while V2 persistence exists independently: `services/gateway/main.py`, `services/gateway/artifact_document_store.py:57`.
 - `ArtifactDocumentStore.persist()` already groups immutable documents, optional answer sets, variants, dependencies, approvals, and snapshots in one session: `services/gateway/artifact_document_store.py:103`.
 - Generation derives answers from V1 projections and places them in metadata; the derived answer-key path therefore must move to persisted `AnswerSet` lookup: `packages/agents/teaching_pack/generate_one_artifact.py`.
 - Existing quality/completion/export stages hydrate V1-shaped projections from the graph port: `packages/agents/teaching_pack/quality_runtime.py`; `services/gateway/teaching_pack_completion.py`; `services/gateway/teaching_pack_export_writer.py`.
 - V1 preview fallback already exists through `ArtifactDocumentStore.get_preview_source()`: `services/gateway/artifact_document_store.py`.

## Decisions (with rationale)
 - Use a gateway-owned V2-backed adapter behind the existing agents package port for this issue; agents must not import gateway storage.
 - Construct and validate an atomic specialist result before persistence, with `ArtifactDocument`, optional `AnswerSet`, variants, dependencies, quality state, and provenance.
 - Student documents and their metadata are answer-free by construction; teacher answer-key artifacts derive only from persisted AnswerSet entity versions.
 - V1 fixtures remain readable with an explicit legacy marker, metrics, and a documented V1 writer deletion date.
 - Put bidirectional V1 projection mapping in `common/contracts`, so agents and gateway share typed, package-neutral conversion rules; reject unmappable shapes instead of silently dropping fields.
 - Continue deriving AnswerSet from the generated V1 projection inside agents until specialists natively emit V2. Pass it separately to the persistence port and remove it from student projection metadata before conversion or persistence.
 - Rework derived answer-key generation to resolve answer data through a package-owned answer-set read port rather than dependency metadata.
 - Treat edit invalidation as new work in #463: versioned edits keep history immutable and mark derived answer keys, snapshots, and exports stale.
 - Block V2 activation when a startup query detects active V1 runs, rather than risking mixed persistence for an in-flight run.

## Scope IN
 - #463 acceptance criteria and its required transaction, leakage, queued-run, invalidation, migration, and export evidence.
 - Python/TypeScript contract parity, gateway migration, runbook/ADR/anatomy synchronization required by #463.

## Scope OUT (Must NOT have)
 - Specialist pedagogy redesign, Content Intelligence Graph (#465), durable-worker changes (#471), or generic orchestration redesign (#464).
 - A long-lived production dual-writer or silent fallback to V1 persistence.

## Open questions
 - None. The issue’s V2-only-write invariant resolves the only material rollout fork.

## Approval gate
 status: awaiting-approval
 pending action: write .omo/plans/artifact-document-v2-cutover.md
 approach: V2-only production persistence via a gateway-owned adapter, V1 read compatibility only, TDD evidence at transaction/security/live-path boundaries.
<!-- When exploration is exhausted and unknowns are answered, set status: awaiting-approval. -->
<!-- That durable record is the loop guard: on a later turn read it and resume at the gate instead of re-running exploration. -->
