---
title: Build PR-reviewed YAML knowledge DB and generated SQLite index
status: completed
labels: [component-strategist, knowledge-db, testing]
created: 2026-07-05
---

## Parent

ADR-036.

## What to build

Create the component-strategy knowledge base with repo YAML as the source of truth and a generated SQLite runtime index. The knowledge base maps learning moves, component affordances, evidence sources, constraints, strategy families, negative rules, fallback policies, validator policies, and rationale templates without making SQLite or runtime memory authoritative.

Initial production strategy families must cover:

- vocabulary / language lessons;
- exam / assessment-prep lessons;
- concept / math-science lessons.

Initial entries must reuse existing renderable components where possible: `vocab_cluster`, `contrastive_pairs`, `roleplay_script`, `active_recall_prompt`, `question_list`, `question_card`, `flow_step`, `concept_map`, `table`, `comparison_table` where supported, `phase_timeline`, and safe text-only media references.

## Acceptance criteria

- [x] YAML schema exists for component knowledge, learning moves, strategy families, scoring profiles, evidence sources, contraindications, fallback components, and rationale templates.
- [x] YAML entries validate that every referenced component type exists in `ContentComponent` and is renderable through dispatcher/plugin support.
- [x] Knowledge manifest includes global `knowledge_db_version`, checksum, compatible strategy schema/selector versions, generated SQLite checksum, and supported locales.
- [x] Entries include stable ID, per-entry semantic version, lifecycle status, production-selectability metadata, and complete supported-locale labels/templates for production entries.
- [x] SQLite index generation is deterministic from YAML/manifests; generated index is reproducible in tests and loaded read-only at runtime.
- [x] Query interface supports filtering by artifact type, subject tags, grade band, Bloom/MOET level, Gagne event, UDL tags, duration bounds, compliance risk, and strategy family.
- [x] CI/test command fails on unknown component IDs, unknown evidence IDs, circular fallback paths, missing citations, non-renderable components, stale generated SQLite, missing production locale copy, conflicting rules without explicit priority/override, and insufficient component coverage for a supported strategy family.
- [x] Production-selectable bindings declare fallback policy and production learning moves declare at least declarative fill-validation policy.
- [x] Draft entries are excluded from production generation; deprecated entries are replay-resolvable by exact ID/version but not selectable for new runs/revisions.
- [x] Tests include fixture queries for vocabulary, exam-prep, and concept/math-science contexts.

## Completion evidence

- Added source-of-truth YAML at `common/component_strategy_knowledge/knowledge.yaml`.
- Added frozen knowledge models in `common/contracts/component_strategy_knowledge_models.py`.
- Added validation, deterministic SQLite build, read-only runtime loading, stale-index checks, and query filters in `common/contracts/component_strategy_knowledge.py`.
- Added CLI wrapper `scripts/build_component_strategy_index.py` and generated `common/component_strategy_knowledge/knowledge.sqlite` from YAML.
- Verified with `uv run pytest common/contracts/tests/test_component_strategy_knowledge.py common/contracts/tests/test_component_strategy_contracts.py` and `uv run python scripts/build_component_strategy_index.py`.

## Blocked by

- CS-01 contracts and immutable strategy snapshot.

## References

- `docs/adr/036-component-strategy-knowledge-and-governance.md`
- `common/contracts/components/__init__.py`
- `common/contracts/components/registry.py`
- `packages/renderer/src/contracts/components.ts`
- `packages/renderer/templates/components/dispatcher.html`
- `packages/renderer/src/contracts/questions/registry.ts`
- `packages/renderer/src/contracts/questions/register.ts`
- `docs/reports/template-reference-mode-briefs.md`

## Implementation notes

- YAML is the only editable source of truth. SQLite is derived and must not be manually edited.
- Runtime must fail closed on stale/missing generated SQLite rather than regenerating silently.
- Prefer small, cited, composable entries over one giant strategy blob.
- If a useful component is defined but not renderable, do not include it as selectable until renderer support is added or a fallback is declared.
- CS-10 owns deeper lifecycle/version/capability-manifest governance; keep this issue aligned with those constraints.
