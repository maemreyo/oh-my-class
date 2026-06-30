---
title: Staged rollout, feature flag, and end-to-end unit flow
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Turn the implemented capability into a monitored, beta-ready feature behind `features.topic_decomposition_v1`, with a full end-to-end scenario and a rollout checklist (ADR-017 §Phasing). This is the release gate for Phase 1 (sequential happy-path); Phase 2/3 features (parallel intra-layer, soft-block override polish, decomposition memory, knowledge graph, coherence lint, personalization) ship behind the same flag incrementally.

- A single feature flag `features.topic_decomposition_v1` gates triage suggestion, the `plan_unit` path, the unit gate, fan-out, and the unit workspace. With it off, the system behaves exactly as today.
- Rollout checklist at `docs/reports/topic-decomposition-rollout-checklist.md`: dev/staging validation, beta-teacher enablement, fallback/escalation behavior, metrics to monitor, and a kill switch.
- No silent downgrade: a failed unit plan/fan-out must fail closed or escalate to the teacher — never silently fall back to a single lesson.

## Acceptance criteria

- [ ] `features.topic_decomposition_v1` toggles the entire feature in dev/staging; disabling it restores baseline behavior with no broken UI/endpoints.
- [ ] E2E covers: teacher submits a multi-tiết topic → triage suggests a unit → teacher confirms → reviews/edits the sequence at `UNIT_APPROVAL` → approves → children fan out (sequential, topo order) → teacher reviews sessions in the dashboard → approves all → exports a unit bundle.
- [ ] Failure path E2E: a child session fails → unit stays alive → teacher retries that session → unit completes.
- [ ] Observability dashboard links and the metrics from issue 018 are documented in the checklist.
- [ ] No silent downgrade path from a failed unit to a single lesson exists.
- [ ] All prior issues' suites pass; the standard single-lesson E2E is unchanged.

## Detailed test suite

(Real DB + real LLM via 9router port 20228, model `4omc`; full stack.)

- [ ] `tests/e2e/test_unit_flow.py`: the happy-path scenario above runs end to end and exports a standalone unit HTML bundle containing all sessions, the sequence overview, and the locked theme.
- [ ] `tests/e2e/test_unit_failure_recovery.py`: a forced session failure keeps the unit alive; retry drives it to `complete`.
- [ ] Feature-flag tests: flag off → no triage suggestion, no `/units` route, `plan_unit` rejected predictably; flag on → full path.
- [ ] No-silent-downgrade test: a unit-plan failure surfaces an error/escalation, never a single-lesson substitute.
- [ ] Regression: `make test` and `make check` pass; the standard teaching-pack E2E is unchanged.
- [ ] Rollout checklist doc check: dev/staging validation, beta enablement, fallback, metrics, and kill switch are documented.
- [ ] Run `make check` and `uv run pytest tests/e2e/test_unit_flow.py tests/e2e/test_unit_failure_recovery.py -v`.

## Blocked by

- .scratch/topic-decomposition/012-frontend-unit-workspace.md
- .scratch/topic-decomposition/016-cross-session-coherence-lint.md
- .scratch/topic-decomposition/017-unit-packager-export.md
- .scratch/topic-decomposition/018-observability-and-eval-harness.md
