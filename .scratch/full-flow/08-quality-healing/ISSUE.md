---
title: "Full flow 08 - Quality gates and healing loop"
status: ready-for-agent
labels: [ready-for-agent, full-flow, incomplete, quality]
created: 2026-06-25
reviewed: 2026-06-25
---

## Review status

**Not complete.** This is the biggest correctness blocker. The current Layer 1 gate validates a fake `{type, content}` shape instead of the canonical `ArtifactContent` contract. The LLM judge path is effectively a hardcoded pass for non-empty content. Current tests mostly prove simple routing and strategy selection, not a real quality/healing loop.

Known current implementation:

- `packages/agents/gates/schema_validator.py` uses `REQUIRED_ARTIFACT_KEYS = {"type", "content"}`.
- `common/contracts/artifact.py::ArtifactContent` uses `artifact_type`, `theme`, `title`, `sections`, `metadata`, and `accessibility`.
- A valid `ArtifactContent` currently fails `step_09_schema_validate()` because it lacks `type` and `content`.
- `packages/agents/gates/llm_judge.py` returns a deterministic high score for non-empty content instead of a real or injectable judge path.
- Healing strategy selection exists, but no end-to-end fail -> heal -> regenerate -> revalidate loop is covered.

## Remaining work

- [ ] Replace Layer 1 schema validation with validation against `ArtifactContent`/`TeachingPack`, or a clearly documented canonical artifact DTO shared by generator, gates, API, renderer, and frontend.
- [ ] Make content/presentation gates inspect `ArtifactContent.sections` and rendered/preview HTML, not only a flat `content` string.
- [ ] Replace hardcoded judge pass with an injectable deterministic judge for tests and the real configured judge path for runtime.
- [ ] Ensure answer-key leakage, external assets, missing brand string, native radio inputs, and unmanaged JS fail closed before content approval/export.
- [ ] Make healing loop actually re-enter generation and then re-run gates, with state evidence of each attempt.
- [ ] Expose quality summary/issues in the run read model without leaking unsafe internal state.

## Acceptance criteria

- [ ] Layer 1 schema validation runs against generated canonical artifacts and blocks invalid content.
- [ ] A valid `ArtifactContent` from the content creator passes Layer 1 schema validation.
- [ ] Layer 2/3 content and presentation checks run and write actionable issues to state.
- [ ] Layer 4 judge uses the real quality judge path or an injectable deterministic judge in tests; no unconditional hardcoded pass.
- [ ] Healing strategy increments fail counts, records strategy, and either regenerates or escalates.
- [ ] Passing artifacts advance to content approval waiting state.
- [ ] Failing artifacts do not silently advance to content approval.
- [ ] Web run detail shows quality status/issues for the run.
- [ ] `make check` passes.

## Test suite upgrades

- [ ] Unit: schema gate fails malformed artifact and passes valid `ArtifactContent`.
- [ ] Unit: schema gate rejects legacy `{type, content}` if that is not the canonical contract, or converts it explicitly before validation.
- [ ] Unit: content/presentation gates detect answer-key leakage, external assets, missing brand requirements, native radio inputs, and unmanaged JS.
- [ ] Unit: judge result below threshold routes to healing; above threshold routes to content approval using an injected judge, not a hardcoded score.
- [ ] Unit: healing strategy selection respects fail count and failure type.
- [ ] Integration: generated valid artifact reaches content approval through the real graph gate chain.
- [ ] Integration: generated invalid artifact enters healing and records issues.
- [ ] Integration: healing re-runs generation and validation before success or escalation.
- [ ] Integration: repeated failures escalate after configured limit.
- [ ] Real surface: run with mocked bad artifact shows quality failure/healing state via `GET /run/{id}`.

## Blocked by

- Full flow 07 - Artifact retrieval and web preview
