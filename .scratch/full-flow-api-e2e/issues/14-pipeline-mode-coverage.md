# [FFA-14] Pipeline-mode coverage — diagnose / plan_unit / vocabulary_batch

Status: DONE
Labels: full-flow-api, e2e
ADR: 031
Depends on: FFA-02, FFA-10

## Context

`PipelineMode` has four modes (`common/contracts/run_contract.py:10`) that produce different
outputs and gates:
- `generate_pack` — default full pack (covered by FFA-10 core scenarios).
- `diagnose_then_generate` — requires `class_info.student_evidence`; runs a diagnostic then an
  adapted pack.
- `plan_unit` — a unit of lessons; opens the `unit_approval` gate; produces a roadmap.
- `vocabulary_batch` — vocabulary clusters with its own export path (html/gift/h5p + manifest,
  `packages/exporters/src/vocabulary-batch/index.ts`).

A "full test" must exercise each mode at least once, not just `generate_pack`.

## Scope

- [x] Driver adds one scenario per non-default mode:
      - `diagnose_then_generate` with a sample `student_evidence`.
      - `plan_unit` with a `decomposition_intent`; drive the `unit_approval` gate (approve),
        then continue; capture the roadmap + unit lessons.
      - `vocabulary_batch`; capture the cluster manifest + per-cluster html/gift/h5p.
- [x] Handle each mode's distinct gate sequence (e.g. `unit_approval` before content).
- [x] Emit each mode's outputs into its own `.scratch/teacher-scenarios/<mode>/` folder + index.
- [x] Record mode coverage in `summary.json`.

## Acceptance

- Each of the four modes runs to completion (or its expected gate) and produces its expected
  outputs, captured in the e2e output tree.
- `unit_approval` gate is driven for `plan_unit` (uses REST gate discovery, FFA-02).

## References

- ADR-031 (matrix E). `common/contracts/run_contract.py:10`,
  `packages/agents/teaching_pack/nodes.py` (`_unit_approval`),
  `packages/exporters/src/vocabulary-batch/index.ts`.
