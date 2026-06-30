---
title: UnitPackager — per-session export and lazy unit bundle
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Let a teacher export a whole unit as one coherent deliverable, while each session also exports independently (ADR-017 §Export). Packaging is an orthogonal layer over existing formats — it must not add values to the `ExportFormat` enum.

`packages/exporters/unit_packager.py`:

- Per-session export reuses each child's existing export path (already available — children are real runs).
- A `UnitPackager` composes the **approved** session packs + sequence metadata into a unit deliverable, generated **lazily/on demand** (`POST /units/{id}/export`, issue 011):
  - HTML → one unit document: cover + sequence/prerequisite overview + table of contents + linked sessions, using the locked unit theme.
  - Assessment formats (gift/qti/h5p/google_forms) → a zip bundle of per-session files + a unit manifest (no semantic cross-session merge).
- Partial units: package only the approved sessions; skip the rest.

## Acceptance criteria

- [ ] Per-session export is unchanged (reuses the child run export path).
- [ ] `UnitPackager` composes approved sessions into a unit bundle on demand; nothing is generated until requested.
- [ ] HTML bundles use the locked unit theme and include cover + TOC + sequence overview + linked sessions.
- [ ] Assessment-format bundles produce a zip of per-session files plus a manifest; no malformed cross-session merge.
- [ ] A `partially_complete` unit packages only its approved sessions; the manifest **encodes the omitted sessions** (id + status) and the bundle/UI surfaces a teacher-visible "N/M approved sessions included" warning.
- [ ] No new `ExportFormat` enum values are introduced.

## Detailed test suite

(Real artifacts from real child runs where feasible; deterministic packaging logic.)

- [ ] `packages/exporters/tests/test_unit_packager_html.py`: a 3-session unit produces one HTML doc with cover, TOC, all three sessions, and the locked theme tokens.
- [ ] `packages/exporters/tests/test_unit_packager_assessment.py`: a quiz-format unit produces a zip of 3 per-session files + a manifest; each file is independently valid.
- [ ] `packages/exporters/tests/test_unit_packager_partial.py`: with 2 of 3 sessions approved, the bundle contains exactly 2 sessions.
- [ ] `packages/exporters/tests/test_unit_packager_lazy.py`: no bundle artifact exists until `export` is invoked.
- [ ] Enum guard: a test asserts `ExportFormat` is unchanged.
- [ ] Run `uv run pytest packages/exporters/tests/test_unit_packager_*.py -v`.

## Blocked by

- .scratch/topic-decomposition/010-unit-orchestrator.md
- .scratch/topic-decomposition/011-unit-read-api-and-streaming.md
