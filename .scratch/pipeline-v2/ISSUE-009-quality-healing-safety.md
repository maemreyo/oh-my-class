---
title: Pipeline V2 quality gates, typed healing, safety, and export readiness
status: focused-slice-pass
labels: [pipeline-v2, quality, healing, safety]
created: 2026-06-27
order: 9
blocked_by: [ISSUE-005-research-engine, ISSUE-007-artifact-workflow, ISSUE-008-rendered-preview-approval]
adr_refs:
  - docs/adr/009-quality-healing-and-safety-gates.md
  - docs/adr/010-pipeline-v2-testing-and-observability.md
---

## Problem

V2 needs production-quality validation and healing that is artifact-scoped, privacy-aware, and aligned with rendered HTML approval. Final export cannot be the first time presentation and safety are checked.

## Scope

Implement V2 quality, healing, safety, and export readiness.

Agent-ready tasks:

1. Implement per-artifact deterministic gates: schema, placeholder, answer-key separation, language/age/readability, presentation contract, external assets, accessibility basics, unsupported components.
2. Implement adaptive artifact LLM judge based on risk/borderline/rigorous mode/artifact type.
3. Implement pack-level coherence review using artifact summaries and QA metrics.
4. Implement typed failure classifier.
5. Implement healing strategies for malformed JSON, schema invalid, answer-key leakage, factual uncertainty, pedagogical mismatch, timeout, and teacher-scoped rejection.
6. Implement pre-search, pre-LLM, and pre-publish safety gates.
7. Implement export readiness over approved rendered snapshots.
8. Ensure scoped teacher feedback can regenerate selected artifacts/sections only.

## Out Of Scope

- New non-HTML exporters.
- Full admin moderation UI.
- Rebuilding existing quality package if reusable parts can be adapted cleanly.

## Acceptance Criteria

- Required artifacts cannot reach content approval until minimum deterministic gates pass.
- Optional adaptive judge behavior follows RunContract quality policy.
- Pack-level coherence blocks inconsistent packs before approval/export.
- Safety gates prevent student PII search leakage and student-facing answer-key leakage.
- Healing attempts are bounded and persisted.
- Teacher rejection can target one artifact without regenerating the whole pack.

## Test Plan

- Unit tests for gate checks and failure classifier.
- Integration tests for artifact healing loops and escalation.
- Safety tests for PII, answer keys, and external assets.
- Live 9Router smoke for one healing path.
- Export readiness tests using persisted snapshots.

## Observability

- Emit compact events for gate pass/fail, healing started/completed/escalated, pack coherence result, and export readiness.
- Langfuse metadata includes failure class, healing strategy, judge score, issue counts, and artifact id.

## Required Edge Cases And Tests

- Every hard block fails deterministically: missing standalone HTML, external assets, answer-key leakage, unsupported components, PII leakage.
- Deterministic gates run before LLM judges and can block without spending LLM calls.
- Adaptive judge triggers only for configured risk/borderline/rigorous cases.
- Versioned rubric registry composes artifact, subject, locale, curriculum, and risk criteria correctly.
- Healing attempts are bounded per artifact and per run.
- Schema repair cannot change unrelated valid fields.
- Answer-key repair only moves/removes teacher-only data and reruns leakage detector.
- Factual uncertainty routes to research enrichment before regeneration.
- Pedagogical mismatch can route artifact-only or blueprint-level based on classifier.
- Teacher-scoped rejection regenerates only selected artifact/section unless feedback changes contract.
- Safety gates run before search, before LLM, and before publish.
- Tests include adversarial hidden answer keys, prompt injection in teacher request, student PII in evidence, unsafe HTML, and unsupported export.
- Pack coherence catches quiz not matching lesson objectives and inconsistent vocabulary across artifacts.

## Rollback

Quality/safety gates are release blockers. If a gate is noisy, tune thresholds/config rather than disabling core safety invariants.

## Ultrawork Review — 2026-06-27

Status: PARTIAL. Deterministic gates and export readiness exist, but adaptive judge, full healing loops, and pack coherence are not fully proven.

Evidence:
- Quality contracts are in `common/contracts/quality.py`.
- Deterministic artifact, snapshot publish, pre-search safety, healing classification, and export readiness checks are implemented in `services/gateway/quality_gates.py` and `services/gateway/quality_workflow.py`.
- Tests cover placeholder/answer-key/accessibility blocking, valid teacher-only answers, external asset and student key leakage, pre-search PII blocking, healing classifier mapping, and export readiness in `services/gateway/tests/test_quality_gates.py` and `test_quality_workflow.py`.
- Artifact generation calls `validate_artifact_content` in `services/gateway/artifact_workflow.py` before marking artifacts passed.
- Active Teaching Pack render-quality now includes a deterministic pack-level coherence gate in `packages/agents/teaching_pack/quality.py`, wired before content approval by `packages/agents/teaching_pack/nodes.py::_render_quality`.
- Regression coverage in `packages/agents/tests/teaching_pack/test_nodes.py` blocks a quiz that does not share lesson terms before snapshots/content approval are created.
- Pack-level coherence was deepened on 2026-06-29: `packages/agents/teaching_pack/quality.py` now blocks objective drift, lesson key-vocabulary drift for quiz/worksheet artifacts, and Vietnamese quiz difficulty distribution mismatch when the pack provides the relevant metadata signals.
- Focused coherence regressions now cover `quiz_not_aligned_with_lesson`, `worksheet_not_aligned_with_objectives`, `quiz_missing_lesson_vocabulary`, and `quiz_invalid_vietnamese_difficulty_distribution`.
- Manual quality-gate driver exercised `_render_quality` through the active graph node surface: a good normalized lesson+quiz pack returned `quality_scores.passed=True`; a bad worksheet/objective-drift pack returned `quality_scores.passed=False` with `quality_recovery_route=planning_blueprint`; a lesson-vocabulary drift pack returned `quality_recovery_route=artifact_workflow`.
- `packages/agents/teaching_pack/nodes.py` was split so active node orchestration stays below the 250 pure-LOC ceiling; quality checks live in `quality.py` and scoped regeneration helpers in `scoped_regeneration.py`.
- Render-quality recovery routing was split into `packages/agents/teaching_pack/quality_routing.py`; `packages/agents/teaching_pack/graph.py` now routes failed pack-coherence states to `planning_blueprint`, `post_blueprint_research`, or `artifact_workflow` before `teacher_approval` can run.
- Typed healing routing was made explicit for the previously missing ISSUE-009 classes: `common/contracts/quality.py` adds `FACTUAL_UNCERTAINTY`, `PEDAGOGICAL_MISMATCH`, `RESEARCH_ENRICHMENT`, and `REPLAN_BLUEPRINT`; `services/gateway/quality_gates.py` maps factual uncertainty to research enrichment and pedagogical mismatch to blueprint replan; `services/gateway/healing_executors.py` correctly treats those as non-local artifact repairs.
- Focused verification after the coherence/healing-routing updates: `uv run pytest services/gateway/tests/test_quality_gates.py services/gateway/tests/test_healing_executors.py common/contracts/tests/test_quality.py -q` → `15 passed`; `uv run pytest packages/agents/tests/teaching_pack/test_nodes.py packages/agents/tests/sub_agents/test_content_creator_per_artifact.py services/gateway/tests/test_teaching_pack_executor.py services/gateway/tests/test_teaching_pack_worker.py services/gateway/tests/test_teaching_pack_runs_router.py services/gateway/tests/test_teaching_pack_contract_resume.py services/gateway/tests/test_teaching_pack_gate_registry.py services/gateway/tests/test_teaching_pack_job_store_leases.py services/gateway/tests/test_teaching_pack_stream_router.py services/gateway/tests/test_run_creation_security.py services/gateway/tests/test_teaching_pack_auth.py -q` → `105 passed`; focused graph/node/quality smoke after test split → `44 passed`; broader focused suite including quality/healing/security paths → `132 passed`; py_compile succeeded on changed Python files.
- Oracle review of ISSUE-009 focused closure returned PASS before the graph-routing follow-up. The noted residual was closed for the active graph seam: pack-coherence failures no longer enter teacher approval and now route to research, blueprint, or artifact-workflow recovery. Persisted end-to-end orchestration of those recovery cycles remains broader Pipeline V2 work.

Focused-slice residuals:
- Adaptive LLM judge/rubric governance is still broader Pipeline V2 work and is not part of the focused `/teaching-packs/*` closure.
- Pack-coherence failures are deterministic blocks before approval/export and now route through the active graph recovery seam. Persisted cross-run repair orchestration and full live 9Router evidence for every recovery branch remain broader Pipeline V2 work.
- Persisted repair loops for every listed failure class remain broader Pipeline V2 work. The focused slice now has deterministic hard blocks, explicit typed routes for factual uncertainty/pedagogical mismatch, scoped teacher regeneration proof, and fail-closed timeout/malformed JSON evidence.
