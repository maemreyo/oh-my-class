---
title: "Full flow 08 - Quality gates and healing loop"
status: ready-for-agent
labels: [ready-for-agent, full-flow]
created: 2026-06-25
---

## What to build

Make generated draft artifacts pass through the real quality gate chain and healing loop. Passing artifacts should proceed to content approval. Failing artifacts should be repaired, rerouted, replanned, or escalated according to the existing healing strategy rules.

This slice is complete when run state visibly records quality outcomes and the system does not silently pass broken artifacts.

## Acceptance criteria

- [ ] Layer 1 schema validation runs against generated artifacts and blocks invalid content.
- [ ] Layer 2/3 content and presentation checks run and write actionable issues to state.
- [ ] Layer 4 judge uses the real quality judge path or an injectable deterministic judge in tests; no unconditional hardcoded pass.
- [ ] Healing strategy increments fail counts, records strategy, and either regenerates or escalates.
- [ ] Passing artifacts advance to content approval waiting state.
- [ ] Web run detail shows quality status/issues for the run.
- [ ] `make check` passes.

## Test suite

- [ ] Unit: schema gate fails malformed artifact and passes valid artifact.
- [ ] Unit: content/presentation gates detect answer-key leakage, external assets, and missing brand requirements.
- [ ] Unit: judge result below threshold routes to healing; above threshold routes to content approval.
- [ ] Unit: healing strategy selection respects fail count and failure type.
- [ ] Integration: generated valid artifact reaches content approval.
- [ ] Integration: generated invalid artifact enters healing and records issues.
- [ ] Integration: repeated failures escalate after configured limit.
- [ ] Real surface: run with mocked bad artifact shows quality failure/healing state via `GET /run/{id}`.

## Blocked by

- Full flow 07 - Artifact retrieval and web preview
