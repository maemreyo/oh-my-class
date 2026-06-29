---
title: Central methodology tag registry and CI drift guard
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Create one canonical methodology registry used by planner contracts, quality gates, teacher UI, and renderer projections. Today tags are split between `common/contracts/lesson_plan.py`, `packages/quality/layer2_content/methodology.py`, renderer component contracts, and issue descriptions. This creates drift risk: a tag can be accepted by the planner but not known to the gate or UI.

The registry should define each supported tag, display labels, teacher-facing descriptions, required component types, compatibility/conflict metadata, supported artifact types, and export-format support.

## Acceptance criteria

- [ ] A canonical registry exists in the contract/domain layer and is importable by quality gates and UI schema generation without violating import boundaries.
- [ ] `common/contracts/lesson_plan.py` derives or validates tags from the registry.
- [ ] `packages/quality/layer2_content/methodology.py` derives required component checks from the registry rather than duplicating string lists.
- [ ] UI mode picker consumes generated registry metadata for labels/descriptions instead of hardcoded tag strings.
- [ ] Adding a new tag requires updating exactly one canonical registry plus tests.
- [ ] CI fails if a known methodology tag literal is introduced outside approved registry/test fixture locations.

## Detailed test suite

- [ ] `common/contracts/tests/test_methodology_registry.py`: Given the registry, when iterated, then every supported tag has non-empty ID, English/Vietnamese labels, required component metadata, and supported artifact list.
- [ ] `packages/quality/tests/test_methodology_gate_registry.py`: Given each registered tag, when the quality gate runs with missing requirements, then it reports the registry-defined requirements.
- [ ] UI schema test: Given generated frontend metadata, when the mode picker renders, then every registry tag appears exactly once.
- [ ] CI guard test: Given a fixture file with a hardcoded known tag outside approved paths, when the drift guard runs, then it fails with file and line number.
- [ ] Compatibility test: Given all pairwise tag combinations, when checking compatibility, then every pair resolves to compatible, conflict, or neutral; no pair is undefined.
- [ ] Run `lint-imports`, schema generation/parity checks, and frontend typecheck.

## Blocked by

- .scratch/inverse-thinking/019-methodology-schema-parity-and-migration.md
