# Vocabulary Batch / Semantic Anchoring Epic

ADRs:

- `docs/adr/021-vocabulary-batch-pipeline-mode.md`
- `docs/adr/022-semantic-anchor-domain-model.md`

Goal: add a production-ready `vocabulary_batch` mode inside the existing Teaching Pack runtime. A teacher pastes free-form confusing-word clusters; the system normalizes the input, grounds lexical distinctions, synthesizes Semantic Anchor RCM content, generates lightweight practice, validates each cluster, supports teacher review/editing, and exports standalone teacher/student HTML plus optional practice exports.

This epic deliberately reuses existing platform capabilities: Teaching Pack runs/jobs/gates, BaseStore memory, renderer/exporter boundaries, quality gates, methodology registry, and the frontend approval/dashboard patterns. It must not create a separate vocabulary sidecar app.

## Issues

1. `001-contracts-and-methodology-mode.md` — vocabulary_batch mode, semantic anchoring methodology, and codegen contracts.
2. `002-cluster-workflow-persistence.md` — per-cluster workflow state, snapshots, evidence ledger, and status model.
3. `003-input-normalizer-and-ambiguity-report.md` — free-form teacher input parser with structured ambiguity reports.
4. `004-lexical-grounding-profile.md` — reusable Researcher lexical grounding profile and source notes.
5. `005-semantic-anchor-synthesis.md` — SemanticAnchorCluster synthesis via reusable content capability and RCM projection data.
6. `006-practice-generator-capability.md` — reusable PracticeGenerator and semantic-anchor PracticeSet.
7. `007-vocabulary-batch-orchestrator.md` — mode routing, per-cluster scheduling, configurable concurrency, and typed failure strategy.
8. `008-semantic-anchoring-quality-gate.md` — per-cluster quality gate with passed/needs_review/failed verdicts.
9. `009-projections-and-structured-editor.md` — teacher/student projections and structured field editing.
10. `010-batch-export-package.md` — offline index, per-cluster files, manifest, and status-aware export policy.
11. `011-teacher-preferences-and-lexical-memory.md` — per-teacher corrections and reviewed shared lexical knowledge.
12. `012-rollout-e2e-and-release-evidence.md` — feature flag, UI entry, full E2E evidence, and release gate.

## Dependency order

Wave 0: `001`

Wave 1: `002` ← `001`; `003` ← `001`

Wave 2: `004` ← `001,003`; `006` ← `001,002`

Wave 3: `005` ← `001,002,004`

Wave 4: `007` ← `002,003,004,005,006`; `008` ← `005,006`

Wave 5: `009` ← `005,006,008`; `011` ← `002,004,009`

Wave 6: `010` ← `007,008,009`

Wave 7: `012` ← `010,011`

Key cross-epic references:

- `priority-upgrades/001` — quality flags in approval UI.
- `priority-upgrades/002` — BaseStore per-teacher/class memory substrate.
- `artifact-send-fanout/` and ADR-020 — reducer-backed fan-out patterns and concurrency discipline.
- `testing/001` and `testing/008` — real harness and canonical flow coverage.
