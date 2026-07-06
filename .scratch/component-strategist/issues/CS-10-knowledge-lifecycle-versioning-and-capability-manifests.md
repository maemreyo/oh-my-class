---
title: Add knowledge lifecycle, versioning, and capability-manifest governance
status: completed
labels: [component-strategist, knowledge-db, governance, testing]
created: 2026-07-05
---

## Parent

ADR-036 and ADR-038.

## What to build

Extend the component-strategy knowledge system with production/draft/deprecated lifecycle states, global manifest versioning, per-entry semantic versions, generated renderer/exporter capability manifests, build-order validation, and CI freshness checks for the generated SQLite index.

This issue makes strategy knowledge reproducible and production-safe: runtime loads generated data read-only, draft knowledge cannot leak into production, deprecated knowledge can replay old snapshots but cannot be selected for new decisions, and strategy validation depends on current renderer/exporter capabilities.

## Acceptance criteria

- [x] Knowledge manifest includes `knowledge_db_version`, manifest checksum, compatible strategy schema versions, compatible selector versions, generated SQLite checksum, and supported locale list.
- [x] Every knowledge entry has stable `id`, semantic `version`, lifecycle `status` (`production`, `draft`, `deprecated`), and production-selectability metadata.
- [x] Production-selectable entries require complete teacher-facing labels/descriptions/rationale templates for all supported locales.
- [x] Draft entries can load only in explicit non-production/dev mode and cannot pass production release gates.
- [x] Deprecated entries are excluded from new strategy planning and new revisions, but remain resolvable by exact id/version for old snapshot replay until retention/removal metadata allows removal.
- [x] Snapshots store global manifest/checksum plus exact selected knowledge refs with id/version/kind.
- [x] SQLite index is generated at build/CI time, packaged for runtime read-only loading, and never regenerated silently at runtime.
- [x] CI fails when generated SQLite is stale relative to YAML/capability manifests or when runtime manifest/checksum compatibility is invalid.
- [x] Renderer/exporter packages expose generated capability manifests; strategy validation consumes these manifests instead of reading templates/export implementation.
- [x] Capability manifests are hybrid: mechanical support facts generated from contracts/templates/export bindings, reviewed annotations for cognitive load, print risk, item limits, accessibility requirements, and known limitations.
- [x] Build order is enforced: contracts -> renderer/exporter capability manifests -> strategy YAML validation -> SQLite generation -> golden/render/export tests.
- [x] Knowledge validation fails on unknown references, production entries missing locale labels, stale manifests, conflicting rules without explicit priority/override, production-selectable entries without fallback policy, and production learning moves without validator policy.

## Blocked by

- CS-01 contracts and immutable strategy snapshot.
- CS-02 YAML knowledge DB and SQLite index.

## References

- `docs/adr/036-component-strategy-knowledge-and-governance.md`
- `docs/adr/038-component-strategy-validators-and-release-gates.md`
- `.scratch/component-strategist/issues/CS-02-yaml-knowledge-db-and-sqlite-index.md`
- `common/contracts/components/__init__.py`
- `packages/renderer/templates/components/dispatcher.html`
- `packages/renderer/src/contracts/components.ts`
- `packages/exporters/src`

## Implementation notes

- Runtime stale-index behavior is fail-closed. Developer regeneration must be explicit.
- Deprecated knowledge is replay compatibility, not new-selection compatibility.
- Do not add a runtime/admin YAML editing UI in v1.

## Completion notes

- Extended `common/contracts/component_strategy_knowledge_models.py` with pinned knowledge manifest checksums and renderer/exporter capability manifest contracts.
- Added generated capability manifests:
  - `common/component_strategy_knowledge/capabilities/renderer.json`
  - `common/component_strategy_knowledge/capabilities/exporter.json`
- Added capability governance helpers in `common/contracts/component_strategy_capabilities.py` and split SQLite query/persistence helpers into `common/contracts/component_strategy_knowledge_index.py` to keep modules under the size ceiling.
- Updated `common/contracts/component_strategy_knowledge.py` so validation consumes capability manifests, rejects stale capability checksums, rejects draft entries in production mode, excludes deprecated entries from new planning, and keeps exact id/version replay resolution via `resolve_knowledge_ref`.
- Added explicit capability generation/freshness tooling:
  - `scripts/generate_component_strategy_capabilities.py`
  - `scripts/verify_component_strategy_capabilities.py`
- Regenerated Zod schemas and rebuilt `common/component_strategy_knowledge/knowledge.sqlite` after pinning capability checksums.
- Verification evidence:
  - LSP diagnostics clean for changed Python files and generated `common/schemas/src/generated/component_strategy.ts`.
  - `uv run python scripts/verify_component_strategy_capabilities.py` → passed.
  - `uv run pytest common/contracts/tests/test_component_strategy_knowledge.py common/contracts/tests/test_component_strategy_selector.py common/contracts/tests/test_component_strategy_release_gate.py` → 29 passed.
  - `uv run python scripts/generate_zod_schemas.py` → success.
  - `uv run python scripts/build_component_strategy_index.py` → success with source checksum `942c8de23bfb8d47593f5106aa73fbc7697774a0dbf19c71e797b46391755b6a`.
  - `uv run python scripts/run_component_strategy_selector.py .scratch/component-strategist/fixtures/cs08_vocabulary_language_request.json --mode final` → planned vocabulary strategy with `contrastive_pairs`, `vocab_cluster`, score `1.0`.
- Post-write size audit passed: changed Python modules are all below 250 pure LOC after helper extraction.
