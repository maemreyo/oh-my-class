---
title: Diagnostician — wire into diagnose_then_generate, shared knowledge-state, upgrade
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

The diagnostician is dormant (not a stage; single-pass, no retry, static). Position and upgrade it as the **pre-instruction** half of the student-knowledge picture (Phase 3 — personalization).

- **Wire:** a conditional **diagnostic stage** in `mode="diagnose_then_generate"` (runs only when `student_evidence` is present), **before planning**; its `DiagnosticReport` feeds the planner's 3-source input.
- **Shared knowledge-state store with KT:** diagnostician = cold/pre-instruction diagnosis (placement quiz / prior work); KT engine = ongoing post-delivery mastery. Both write to **one per-student knowledge-state store** (two writers, one source of truth); the planner reads the unified store.
- **Divide-and-conquer (no mega-prompt):** analyze per-dimension — per BloomGap / per MisconceptionPattern / per KnowledgeGap as focused sub-steps → synthesize the `DiagnosticReport`.
- **Error-tolerance:** use the StructuredOutput/retry middleware (no single-pass crash).
- **Misconception grounding:** validate misconceptions against a misconception taxonomy (not pure LLM guess); distinguish systematic vs contextual.
- **Smart mechanism:** emit confidence per gap; **re-diagnose as new evidence arrives** (KT updates) — refine over time, not one-shot.

## Acceptance criteria

- [ ] Diagnostician runs as a conditional pre-planning stage in `diagnose_then_generate` (only with `student_evidence`); output feeds the planner's 3-source input.
- [ ] Diagnostician and KT write to one shared per-student knowledge-state store (no duplicate sources of truth).
- [ ] Per-dimension divide-and-conquer + StructuredOutput retry (no single-pass crash).
- [ ] Misconceptions are grounded against a taxonomy; systematic vs contextual distinguished; per-gap confidence emitted.
- [ ] Re-diagnosis refines the report as new KT evidence arrives.

## Detailed test suite

(Real DB + real LLM via 9router `:20228`/`4omc`.)

- [ ] `packages/agents/tests/test_diagnostician_stage.py`: with student_evidence the diagnostic stage runs pre-planning and feeds the planner; without it, skipped.
- [ ] `test_diagnostician_shared_store.py`: diagnostician + KT updates land in the same knowledge-state store; planner reads unified.
- [ ] `test_diagnostician_dc_retry.py`: per-dimension analysis; a malformed sub-step is repaired (no crash).
- [ ] Run `uv run pytest -m real_llm packages/agents/tests/test_diagnostician_*.py -v`.

## Blocked by

- .scratch/effectiveness-loop/004-bkt-knowledge-tracing-engine.md
- .scratch/agent-upgrades/002-planner-intelligent-staged.md
