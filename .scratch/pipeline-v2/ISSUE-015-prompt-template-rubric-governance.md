---
title: Pipeline V2 prompt, template, theme, and rubric governance
status: review-partial
labels: [pipeline-v2, prompts, templates, rubrics, evals]
created: 2026-06-27
order: 15
blocked_by: [ISSUE-001-foundation-architecture, ISSUE-005-research-engine, ISSUE-006-adaptive-llm-transport, ISSUE-008-rendered-preview-approval, ISSUE-009-quality-healing-safety]
adr_refs:
  - docs/adr/013-prompt-template-rubric-governance.md
  - docs/adr/007-adaptive-llm-transport.md
  - docs/adr/010-pipeline-v2-testing-and-observability.md
---

## Problem

Prompts, templates, themes, and rubrics are production logic. If they change without versioning, tests, evals, or trace metadata, V2 output quality and reproducibility will drift silently.

## Scope

Implement governance registries and eval harnesses.

Agent-ready tasks:

1. Implement typed PromptModule registry with Markdown bodies and code metadata/renderers.
2. Implement prompt section compiler with safe compaction and hard core-overflow fail.
3. Implement structured-output strategy metadata per prompt/task.
4. Implement prompt eval harness with static compile tests, schema eval, domain rubric eval, regression corpus, and targeted live 9Router eval.
5. Implement base prompt + locale/subject/artifact overlays with fixtures.
6. Implement dedicated repair prompts by failure type.
7. Implement prompt observability metadata in Postgres events and Langfuse traces.
8. Implement TemplateModule/Theme registry with version/hash validation and render fixtures.
9. Implement versioned Rubric registry with deterministic and LLM criteria.
10. Enforce manual version bump for body/template/rubric changes with content hash validation.

## Out Of Scope

- Prompt editing admin UI.
- Full prompt A/B experimentation platform.
- Non-core artifact templates.

## Acceptance Criteria

- Every V2 LLM call references prompt id, version, hash, compiled hash, sections, overlays, output contract, structured output mode, transport, model, and attempt.
- Prompt body changes fail tests unless version is bumped and eval evidence is updated.
- Template/theme body changes fail tests unless version is bumped and render validation passes.
- Rubric changes fail tests unless version is bumped and fixtures pass.
- Content Creator remains not tool-enabled and consumes explicit research inputs only.
- Prompt eval includes live 9Router for generation/research/planner/healing/judge body changes.

## Required Edge Cases And Tests

- Prompt compiler detects contradictory instructions such as object vs array output.
- Prompt compiler refuses to drop output schema, safety rules, answer-key rules, artifact type, language, grade, subject, or teacher must-haves.
- Auto-compaction drops examples before core context and records compacted/dropped sections.
- LLM compaction preserves source ids, constraints, and teacher must-haves or is rejected.
- Native schema unsupported path falls back safely by task policy.
- Repair prompt cannot modify unrelated fields/sections by default.
- Locale overlay for `vi-VN` and English ESL overlay both pass combined evals.
- Template tests catch hidden answer keys, external assets, print CSS breakage, and accessibility regressions.
- Rubric compiler composes base + artifact + subject + locale + curriculum criteria without duplicates/conflicts.
- Langfuse full IO remains disabled in production config.
- Startup/test detects prompt/template/rubric version/hash drift.

## Test Plan

- Static registry tests for prompt/template/rubric metadata.
- Prompt compile fixture tests for every core prompt module and overlay.
- Targeted live 9Router eval for Planner, Research Engine synthesis, each core artifact generator, repair prompt, and judge prompt.
- Renderer fixture tests for every core artifact template.
- Rubric fixture tests for Math, English ESL, Science citations, and answer-key separation.

## Observability

- Persist compact prompt/template/rubric metadata in run events.
- Langfuse receives richer prompt trace metadata but no full IO by default.
- Release evidence records prompt/template/rubric versions used for each live scenario.

## Rollback

Prompt/template/rubric governance is required before V2 release. If registry implementation is incomplete, do not allow uncontrolled prompt/template changes in production.

## Ultrawork Review — 2026-06-27

Status: PARTIAL. Prompt/template/theme registries and drift detection exist, but full compiler/eval/rubric governance is incomplete.

Evidence:
- Prompt registry, drift detection, and seed data are implemented in `packages/agents/prompts/registry.py`, `drift.py`, and `seed.py`.
- Template registry exists in `packages/renderer/templates/registry.py`; branding registry exists in `common/branding/registry.py`.
- Tests cover prompt/template/theme registration, semver/hash validation, duplicate detection, drift detection, and seed data in `packages/agents/prompts/tests/test_registry.py`.
- Prompt metadata hooks exist in `packages/agents/llm/prompt_metadata.py` and transport/prompt gate modules from Issue 006.

Gaps:
- I did not find a full prompt section compiler with safe compaction, live eval harness, repair prompt suite, or rubric registry implementation.
- Live 9Router eval evidence for planner/research/generation/healing/judge prompt changes was not found.
- Structured-output strategy metadata exists only partially through prompt metadata/schema fields; per-task strategy routing was not verified.
- Locale/subject/artifact overlay composition was not found beyond seeded prompt metadata.
- Drift detection exists, but CI/startup enforcement that fails uncontrolled body/template/rubric changes was not verified.
