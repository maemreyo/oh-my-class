---
title: Pipeline V2 quality gates, typed healing, safety, and export readiness
status: ready-for-agent
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
