---
title: Extend ADR-044 real-LLM harness with edit/rewrite scenarios
status: ready-for-agent
labels: [ready-for-agent, slide-deck, editor, testing]
created: 2026-07-07
---

## Parent

ADR-047: Slide Deck Editor and AI-Assisted Revision (decision 12)

## What to build

Extend the existing ADR-044 official real-LLM acceptance harness (model `4omc`, real gateway HTTP, evidence bundles) with new scenarios covering this editor's LLM-touching paths, rather than building separate harness infrastructure. Passing these scenarios is a completion gate for ADR-047's scope, the same way the existing 3 scenarios gate generation.

## Acceptance criteria

- [ ] A new scenario exercises edit-then-reexport staleness: generate a deck, edit a block, verify a new version/snapshot is created and the export-staleness indicator (SDE-06) fires correctly.
- [ ] A new scenario exercises AI-rewrite end-to-end: trigger a preset rewrite via real gateway HTTP against `4omc`, verify the output passes registry/density validation (SDE-01/02), and verify the confirmation-modal-gated apply path (SDE-08) produces a correctly-tagged version.
- [ ] Both scenarios produce the same timestamped evidence bundle format (run IDs, snapshot IDs, export paths) as the existing 3 ADR-044 scenarios — no new evidence format is invented.
- [ ] These scenarios are added to the same official (non-`.scratch`), CI-ready harness location as the existing ones — not a parallel test suite.
- [ ] SDE-01 through SDE-08 are not considered complete until these scenarios pass — this is the ADR-047 completion gate.

## Blocked by

- SDE-01-content-materialization-llm-integration.md
- SDE-08-ai-assisted-block-rewrite.md
- SDH-07-real-llm-acceptance-harness.md
