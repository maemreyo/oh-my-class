---
title: Build PR-reviewed YAML knowledge DB and generated SQLite index
status: ready-for-agent
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

- [ ] YAML schema exists for component knowledge, learning moves, strategy families, scoring profiles, evidence sources, contraindications, fallback components, and rationale templates.
- [ ] YAML entries validate that every referenced component type exists in `ContentComponent` and is renderable through dispatcher/plugin support.
- [ ] Knowledge manifest includes global `knowledge_db_version`, checksum, compatible strategy schema/selector versions, generated SQLite checksum, and supported locales.
- [ ] Entries include stable ID, per-entry semantic version, lifecycle status, production-selectability metadata, and complete supported-locale labels/templates for production entries.
- [ ] SQLite index generation is deterministic from YAML/manifests; generated index is reproducible in tests and loaded read-only at runtime.
- [ ] Query interface supports filtering by artifact type, subject tags, grade band, Bloom/MOET level, Gagne event, UDL tags, duration bounds, compliance risk, and strategy family.
- [ ] CI/test command fails on unknown component IDs, unknown evidence IDs, circular fallback paths, missing citations, non-renderable components, stale generated SQLite, missing production locale copy, conflicting rules without explicit priority/override, and insufficient component coverage for a supported strategy family.
- [ ] Production-selectable bindings declare fallback policy and production learning moves declare at least declarative fill-validation policy.
- [ ] Draft entries are excluded from production generation; deprecated entries are replay-resolvable by exact ID/version but not selectable for new runs/revisions.
- [ ] Tests include fixture queries for vocabulary, exam-prep, and concept/math-science contexts.

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
