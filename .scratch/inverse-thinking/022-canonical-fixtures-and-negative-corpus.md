---
title: Canonical inverse-thinking fixtures and negative regression corpus
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Create a shared canonical fixture corpus for inverse thinking so contracts, methodology projections, quality gates, renderer, teacher UI, and E2E tests all exercise the same data. Current issues mention English/math/science fixtures in multiple places, but no single corpus issue owns versioning, negative cases, hash drift, or fixture reuse.

## Acceptance criteria

- [ ] A fixture corpus exists under a documented test fixtures directory with English grammar, math misconception, science false-model, and Vietnamese bilingual examples.
- [ ] Negative fixtures cover missing disaster, missing clue, missing safe-zone boundary, rule-first ordering, generic/boring disaster, answer leakage, residual PII, and unknown component type.
- [ ] Each fixture has metadata: case ID, subject, grade band, locale, expected gate outcome, expected projection outputs, and sha256 hash.
- [ ] All inverse-thinking test suites import fixtures from this corpus rather than duplicating inline data.
- [ ] Corpus drift is detected by a manifest/hash check.
- [ ] Fixtures are safe to commit: no real student PII and no external asset URLs.

## Detailed test suite

- [ ] `tests/fixtures/test_inverse_thinking_corpus.py`: Given the corpus manifest, when loaded, then every referenced fixture exists and every file is referenced exactly once.
- [ ] Contract test: Every positive fixture validates against `InverseThinkingPack`.
- [ ] Gate test: Every negative fixture fails with the expected error code/severity.
- [ ] Renderer test: Every positive fixture can project and render lesson/worksheet/quiz/drill without external assets or answer leakage.
- [ ] Hash drift test: Modifying a fixture without updating the manifest fails the test with old/new hash output.
- [ ] PII safety test: Running the PII scrubber over the fixture directory reports zero residual PII.
- [ ] Documentation test: Fixture README lists how to add a new fixture and how to update the manifest.

## Blocked by

- .scratch/inverse-thinking/001-contracts-and-canonical-pack.md
- .scratch/inverse-thinking/004-quality-gates-and-repair.md
