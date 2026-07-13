# EPIC #460 — next eight issues implementation

Base commit: `cd750d9ec4c0bfd0ae8813431134179bb76dda45`

Issues covered in dependency order: #465, #471, #464, #466, #467, #468, #472, #469.

## Architectural direction

The patch keeps the existing dependency direction:

```text
services / LangGraph runtime
          ↓
packages.agents.teaching_pack orchestration adapters
          ↓
common.contracts.content_factory pure contracts and policies
```

The existing specialist generators remain renderer-compatible. A family-specific depth adapter runs at the typed orchestration boundary before schema validation and persistence. This avoids duplicating five orchestration paths while ensuring the production path cannot bypass the new contracts.

## Issue-to-change map

### #465 Content Intelligence Graph

- `build_content_brief` consumes a versioned objective-decomposition snapshot.
- Knowledge-component scope is resolved through the existing graph query port.
- Every artifact pins `knowledge_db_version`, source IDs, ContentBrief ID, and stable objective lineage.
- Tenant access errors from the graph remain fail-closed.

### #471 durable worker and effects

- `RunEvent` and `RunEventOutbox` are inserted in the same transaction.
- Outbox claim uses ordered `FOR UPDATE SKIP LOCKED` leases.
- Publication is at-least-once with `(run_id, sequence)` dedupe identity, bounded exponential retry, lease recovery, and durable acknowledgement.
- Standalone and in-process workers drain the same outbox implementation.

### #464 typed Content Orchestrator

- Pydantic `OrchestratorRequest`, `OrchestratorResult`, and `GenerationBudget` contracts.
- ContentBrief is assembled before dispatch and is validated against run/artifact identity.
- Specialist modules declare real ContentBrief fields per family and return v2 lineage.
- Timeout and unsupported-capability failures are typed and fail before persistence.
- Silent strategy changes are rejected through `enforce_content_brief_compliance`.

### #466 Lesson Design and Presentation

- Time-bounded phase plan with explicit objective IDs, teacher/student actions, materials, checks for understanding, anticipated responses, misconception repair, differentiation, transitions, closure, and contingency reserve.
- Presentation output receives objective/methodology/move lineage and accessibility policy.

### #467 Assessment and Practice

- Every generated item receives objective, knowledge-component, cognitive demand, difficulty, misconception, evidence statement, response/scoring, and verification authority.
- Selected-response options are checked for duplicate/equivalent distractor collisions.
- Practice artifacts progress through worked example → guided → independent → retrieval → interleaved → transfer.
- Solver-supported subject packs retain solver traces; constructed responses use analytic-rubric authority.

### #468 Synthesis

- Explicit synthesis plan records retained/omitted claims, evidence IDs, authority, terminology policy, audience, word budget, discourse structure, and warnings.
- Material source claims are triangulated by independent evidence IDs.
- Roadmaps use topological prerequisite order and fail on cycles.
- Infographic semantics include alt text, long descriptions, grayscale-safe meaning, and no-image fallback.

### #472 tenant/privacy/security

- Mandatory `TenantContext` at the production artifact fanout boundary.
- Tenant-scoped storage keys and content-store read/write guard.
- Personal installations receive an explicit stable `teacher:<id>` organization rather than an unscoped fallback.
- Run rows gain mandatory `organization_id` with expand/backfill/contract migration.
- Telemetry redaction keeps IDs, hashes, counts, versions, and status while removing raw prompts, content, excerpts, answers, and student evidence.

### #469 Pack Coherence

- A deterministic stable-ID coherence gate runs before layer quality/export.
- It blocks unknown objective lineage, teacher-only leakage, answer keys without source assessment, terminology contradictions, and mixed graph snapshots.
- Findings name affected entities, evidence, owner, teacher options, and minimal repair scope.
- Paraphrases do not fail when stable objective IDs agree.

## Verification

```bash
make check-content-intelligence
make check-specialist-registry
make check-content-factory-v2
make check-runtime-resilience
make check-architecture
```

The automation script additionally runs `git diff --check`, compiles every changed Python file, verifies no changed production file contains placeholder markers, and refuses to close any issue if a command fails.

## Explicit non-goals

- No benchmark/certification claims for #470, #473, or #474.
- No deployment-specific object-store vendor selection.
- No attempt to replace the existing SlideDeckEngine or subject capability packs.
- No closure of EPIC #460 itself.
