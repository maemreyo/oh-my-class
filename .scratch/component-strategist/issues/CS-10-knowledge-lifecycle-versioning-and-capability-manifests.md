---
title: Add knowledge lifecycle, versioning, and capability-manifest governance
status: ready-for-agent
labels: [component-strategist, knowledge-db, governance, testing]
created: 2026-07-05
---

## Parent

ADR-036 and ADR-038.

## What to build

Extend the component-strategy knowledge system with production/draft/deprecated lifecycle states, global manifest versioning, per-entry semantic versions, generated renderer/exporter capability manifests, build-order validation, and CI freshness checks for the generated SQLite index.

This issue makes strategy knowledge reproducible and production-safe: runtime loads generated data read-only, draft knowledge cannot leak into production, deprecated knowledge can replay old snapshots but cannot be selected for new decisions, and strategy validation depends on current renderer/exporter capabilities.

## Acceptance criteria

- [ ] Knowledge manifest includes `knowledge_db_version`, manifest checksum, compatible strategy schema versions, compatible selector versions, generated SQLite checksum, and supported locale list.
- [ ] Every knowledge entry has stable `id`, semantic `version`, lifecycle `status` (`production`, `draft`, `deprecated`), and production-selectability metadata.
- [ ] Production-selectable entries require complete teacher-facing labels/descriptions/rationale templates for all supported locales.
- [ ] Draft entries can load only in explicit non-production/dev mode and cannot pass production release gates.
- [ ] Deprecated entries are excluded from new strategy planning and new revisions, but remain resolvable by exact id/version for old snapshot replay until retention/removal metadata allows removal.
- [ ] Snapshots store global manifest/checksum plus exact selected knowledge refs with id/version/kind.
- [ ] SQLite index is generated at build/CI time, packaged for runtime read-only loading, and never regenerated silently at runtime.
- [ ] CI fails when generated SQLite is stale relative to YAML/capability manifests or when runtime manifest/checksum compatibility is invalid.
- [ ] Renderer/exporter packages expose generated capability manifests; strategy validation consumes these manifests instead of reading templates/export implementation.
- [ ] Capability manifests are hybrid: mechanical support facts generated from contracts/templates/export bindings, reviewed annotations for cognitive load, print risk, item limits, accessibility requirements, and known limitations.
- [ ] Build order is enforced: contracts -> renderer/exporter capability manifests -> strategy YAML validation -> SQLite generation -> golden/render/export tests.
- [ ] Knowledge validation fails on unknown references, production entries missing locale labels, stale manifests, conflicting rules without explicit priority/override, production-selectable entries without fallback policy, and production learning moves without validator policy.

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
