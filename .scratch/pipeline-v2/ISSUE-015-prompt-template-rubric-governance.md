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
- Prompt compiler now rejects contradictory structured-output contracts. `packages/agents/prompts/compiler.py` raises `StructuredOutputContradictionError` when the final compiled body asks for both a JSON object and JSON array, including overlay-introduced contradictions.
- Focused prompt-governance verification: red regression first failed on missing `StructuredOutputContradictionError`; after implementation, `uv run pytest packages/agents/prompts/tests/test_compiler_output_contracts.py packages/agents/prompts/tests/test_compiler.py packages/agents/prompts/tests/test_prompt_eval.py -q` → `83 passed`; `uv run basedpyright packages/agents/prompts/compiler.py packages/agents/prompts/tests/test_compiler_output_contracts.py packages/agents/prompts/tests/test_compiler.py` → `0 errors`; `uv run python -m py_compile packages/agents/prompts/compiler.py packages/agents/prompts/tests/test_compiler_output_contracts.py packages/agents/prompts/tests/test_compiler.py` → success; manual compiler driver verified object+array overlay rejection and object-only acceptance.
- Prompt compiler now has deterministic safe compaction for oversized compiled bodies. `PromptCompiler.compile(..., max_chars=N)` drops droppable example sections before core sections, records `PromptMetadata.compacted` and `dropped_sections`, and raises `PromptCompactionError` when core prompt content still exceeds the budget.
- Focused safe-compaction verification: red regression first failed because `PromptCompactionError` and `max_chars` compilation were absent; after implementation, `uv run pytest packages/agents/prompts/tests/test_compiler_compaction.py packages/agents/prompts/tests/test_compiler.py packages/agents/tests/llm/test_compiled_chat.py packages/agents/tests/llm/test_compiled_chat_enrichment.py -q` → `65 passed`; `uv run basedpyright packages/agents/prompts/compaction.py packages/agents/prompts/compiler.py packages/agents/llm/prompt_metadata.py packages/agents/prompts/tests/test_compiler_compaction.py packages/agents/prompts/tests/test_compiler.py packages/agents/tests/llm/test_compiled_chat.py packages/agents/tests/llm/test_compiled_chat_enrichment.py` → `0 errors`; `uv run python -m py_compile packages/agents/prompts/compaction.py packages/agents/prompts/compiler.py packages/agents/llm/prompt_metadata.py packages/agents/prompts/tests/test_compiler_compaction.py packages/agents/prompts/tests/test_compiler.py packages/agents/tests/llm/test_compiled_chat.py packages/agents/tests/llm/test_compiled_chat_enrichment.py` → success; manual compiler driver verified examples are dropped while output-schema, safety, and teacher-must-have sections remain.
- Dedicated repair prompts now select by deterministic quality failure class. `packages/agents/prompts/repair_prompts.py` provides schema, answer-key, PII, and accessibility repair modules, falls back to generic `repair_v1` for non-local repair classes, and keeps every dedicated repair prompt in the aggregate registry drift guard.
- Focused repair-prompt verification: red regression first failed because `packages.agents.prompts.repair_prompts` was absent; after implementation, `uv run pytest packages/agents/prompts/tests/test_repair_prompts.py tests/test_registry_drift_guard.py -q` → `9 passed`; `uv run basedpyright packages/agents/prompts/repair_prompts.py packages/agents/prompts/tests/test_repair_prompts.py scripts/verify_registry_drift.py tests/test_registry_drift_guard.py` → `0 errors`; `uv run python -m py_compile packages/agents/prompts/repair_prompts.py packages/agents/prompts/tests/test_repair_prompts.py scripts/verify_registry_drift.py tests/test_registry_drift_guard.py` → success; manual selector driver verified `answer_key_leakage → repair_answer_key_v1`, `schema_invalid → repair_schema_v1`, and `export_not_ready → repair_v1`.
- Prompt observability metadata now carries overlay provenance. `PromptMetadata.overlay_ids` is populated by `PromptCompiler`, exported by `to_langfuse_metadata`, and emitted as an `overlay_ids:<ids>` provenance tag by compiled-chat when overlays are applied.
- Focused prompt-observability verification: red regressions first failed because overlay IDs were absent from `PromptMetadata`, Langfuse metadata, and compiled-chat tags; after implementation, `uv run pytest packages/agents/prompts/tests/test_registry.py packages/agents/prompts/tests/test_compiler.py packages/agents/tests/llm/test_compiled_chat.py packages/agents/tests/llm/test_compiled_chat_enrichment.py -q` → `121 passed`; `uv run basedpyright packages/agents/llm/prompt_metadata.py packages/agents/llm/compiled_chat.py packages/agents/prompts/compiler.py packages/agents/prompts/tests/test_registry.py packages/agents/prompts/tests/test_compiler.py packages/agents/tests/llm/test_compiled_chat.py packages/agents/tests/llm/test_compiled_chat_enrichment.py` → `0 errors`; `uv run python -m py_compile packages/agents/llm/prompt_metadata.py packages/agents/llm/compiled_chat.py packages/agents/prompts/compiler.py packages/agents/prompts/tests/test_registry.py packages/agents/prompts/tests/test_compiler.py packages/agents/tests/llm/test_compiled_chat.py` → success; manual compiler driver verified Langfuse `overlay_ids` and compiled-chat `overlay_ids:vi_vn,math` provenance tags.
- Structured-output strategy metadata now flows from `PromptModule` into prompt trace metadata and adaptive transport routing tags. Output-schema prompts default to `json_object`, explicit metadata can request `native_schema`, `json_object`, `prompt_json`, or `text_extract`, `to_langfuse_metadata` exports `structured_output_strategy`, and compiled-chat emits `json_strategy:<strategy>` provenance tags.
- Focused structured-output strategy verification: red regression first failed because `PromptMetadata.structured_output_strategy` and compiled-chat `json_strategy` tags were absent; after implementation, `uv run pytest packages/agents/prompts/tests/test_structured_output_strategy.py packages/agents/tests/llm/test_compiled_chat.py packages/agents/tests/llm/test_compiled_chat_enrichment.py packages/agents/tests/llm/test_json_strategy_policy.py -q` → `27 passed`; `uv run basedpyright packages/agents/llm/prompt_metadata.py packages/agents/llm/compiled_chat.py packages/agents/prompts/tests/test_structured_output_strategy.py` → `0 errors`; `uv run python -m py_compile packages/agents/llm/prompt_metadata.py packages/agents/llm/compiled_chat.py packages/agents/prompts/tests/test_structured_output_strategy.py` → success; manual compiler driver verified `native_schema` in `PromptMetadata`, Langfuse metadata, and `json_strategy:native_schema` compiled-chat provenance tags.
- Seeded prompt eval coverage now locks structured-output strategy readiness for planner, researcher, content creator, judge, and repair prompts. `packages/agents/prompts/tests/test_seeded_prompt_strategies.py` compiles every seeded prompt and asserts output-schema prompts default to `json_object` in both `PromptMetadata` and Langfuse metadata.
- Focused seeded strategy eval verification: `uv run pytest packages/agents/prompts/tests/test_seeded_prompt_strategies.py packages/agents/prompts/tests/test_structured_output_strategy.py packages/agents/tests/llm/test_compiled_chat.py packages/agents/tests/llm/test_compiled_chat_enrichment.py packages/agents/tests/llm/test_json_strategy_policy.py -q` → `29 passed`; `uv run basedpyright packages/agents/prompts/tests/test_seeded_prompt_strategies.py packages/agents/prompts/tests/test_structured_output_strategy.py packages/agents/llm/prompt_metadata.py packages/agents/llm/compiled_chat.py` → `0 errors`; `uv run python -m py_compile packages/agents/prompts/tests/test_seeded_prompt_strategies.py packages/agents/prompts/tests/test_structured_output_strategy.py packages/agents/llm/prompt_metadata.py packages/agents/llm/compiled_chat.py` → success.
- Targeted live 9Router prompt eval now covers every governed seeded prompt module through the compiled prompt/provenance path. The live probe compiled `planner_v1`, `researcher_v1`, `content_creator_mcq_v1`, `content_creator_lesson_v1`, `judge_v1`, and `repair_v1`, sent each to live `4omc` at `http://localhost:20228/v1`, and checked response parseability plus prompt id/version/content-hash/compiled-hash/JSON-strategy provenance.
- Live prompt eval evidence: `.scratch/pipeline-v2/artifacts/live-v2-prompt-eval-2026-06-29.json` records `LIVE_PROMPT_EVAL_STRICT_2026_06_29` with `all_calls_ok=true`, `all_valid_json_objects=true`, `all_strategy_tags_present=true`, and `all_provenance_tags_present=true`. The first low-token probe proved reachability and tags but truncated planner/MCQ JSON; the persisted artifact is the rerun with `max_tokens=4096` and all modules parseable.
- Rubric governance now has the same deterministic content-hash drift seam as prompts/templates/themes. `Rubric` computes a SHA-256 digest from its canonical rubric body, rejects mismatched explicit hashes, and `RubricRegistry.validate_hash(version_id)` detects in-memory rubric drift under the registered version.
- Focused rubric-drift verification: red regression first failed because `Rubric.content_hash` and `RubricRegistry.validate_hash` were absent; after implementation, `uv run pytest common/contracts/tests/test_rubric.py -q` → `32 passed`; `uv run basedpyright common/contracts/rubric.py common/contracts/tests/test_rubric.py` → `0 errors`; `uv run python -m py_compile common/contracts/rubric.py common/contracts/tests/test_rubric.py` → success; manual registry driver verified `validate_hash("manual-v1")` is true for the canonical rubric and false after direct criterion drift under the same version.
- CI/startup-style registry drift enforcement now has a single deterministic guard. `scripts/verify_registry_drift.py` builds a snapshot of seeded prompt modules, checked-in renderer templates, checked-in branding themes, and default judge rubrics, then fails if any registered hash no longer matches the registered content.
- Focused aggregate-drift verification: red regression first failed because `scripts.verify_registry_drift` was absent; after implementation, `uv run pytest tests/test_registry_drift_guard.py -q` → `4 passed`; `uv run basedpyright scripts/verify_registry_drift.py tests/test_registry_drift_guard.py` → `0 errors`; `uv run python -m py_compile scripts/verify_registry_drift.py tests/test_registry_drift_guard.py` → success; manual driver `uv run python scripts/verify_registry_drift.py` exits clean for current registries; `.github/workflows/ci.yml` now invokes `python scripts/verify_registry_drift.py` before Python tests.

Gaps:
- Live eval harness remains incomplete as a reusable CI/gated corpus runner. The compiler now covers deterministic contradiction rejection for object-vs-array output contracts and safe compaction of droppable example sections, the repair prompt suite now selects deterministic prompts by failure class, the rubric registry now covers deterministic content-hash drift detection, and targeted live 9Router prompt-eval evidence exists for planner/research/generation/healing/judge seeded prompts.
- Broader domain-quality live 9Router eval corpus coverage remains open for planner/research/generation/healing/judge prompt changes beyond the minimal parseability/provenance probe.
- Structured-output strategy metadata is now verified through prompt metadata, Langfuse metadata export, compiled-chat `json_strategy:<strategy>` tags, and existing adaptive transport policy tag parsing.
- Locale/subject/artifact overlay composition is still limited, but applied overlay IDs are now observable in prompt metadata and compiled-chat tags.
- Drift detection exists for prompt/template/theme/rubric registries and a combined CI/startup-style guard now verifies the checked-in registry hash set together. It is wired into the Python CI test job, but broader live 9Router eval gates remain separate release evidence.
