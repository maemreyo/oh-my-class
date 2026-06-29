---
title: Ship Inverse Thinking staged rollout and observability
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Add the release gate, E2E scenario, observability, and regression fixtures needed to ship inverse thinking safely in production. This slice turns the implemented capability into a monitored beta-ready feature.

## Acceptance criteria

- [ ] `features.inverse_thinking_v1` can be enabled in dev/staging and disabled without breaking standard generation.
- [ ] E2E scenario covers: teacher requests English grammar lesson, selects or receives Inverse Thinking, generated pack passes gates, teacher approves, exported HTML is standalone and contains case flow, summary table, student challenge, and separated teacher-only key.
- [ ] Observability records methodology, creative frame, projection, feature flag, quality gate, repair attempt, warning category, teacher action, export pass/fail, and approval/reject rate where available.
- [ ] Golden fixtures exist for at least one English case-file output and one non-English/non-detective subject-agnostic output.
- [ ] Regression tests catch model drift toward generic disaster text or rule-first content.
- [ ] Rollout checklist documents dev/staging validation, beta teacher enablement, fallback/escalation behavior, and metrics to monitor.
- [ ] No silent downgrade path exists from failed inverse-thinking generation to standard lesson generation.

## Detailed test suite

- [ ] `tests/e2e/test_inverse_thinking_release_flow.py`: Given mocked LLM responses and the feature flag enabled, when a teacher requests an English grammar lesson, then the flow generates, previews, approves, and exports standalone inverse-thinking HTML.
- [ ] Feature-flag tests: Given the flag disabled, when inverse-thinking controls or payloads are requested, then UI hides controls and backend rejects/blocks the path predictably.
- [ ] Observability tests: Given a completed run, when run events are inspected, then methodology, creative frame, projection, feature flag, quality gate, repair attempt, warning category, teacher action, and export pass/fail metadata are recorded where applicable.
- [ ] Golden fixture regression: Given the English case-file fixture and one non-detective subject fixture, when rendered after changes, then semantic structure remains disaster-first and no generic/rule-first drift appears.
- [ ] Rollout checklist test/docs check: Verify dev/staging validation, beta teacher enablement, fallback/escalation behavior, and metric dashboard links are documented.
- [ ] Run `make test`, `make check`, and targeted browser/visual QA before enabling the flag beyond staging.

## Blocked by

- .scratch/inverse-thinking/001-contracts-and-canonical-pack.md
- .scratch/inverse-thinking/002-methodology-package-and-projections.md
- .scratch/inverse-thinking/003-pipeline-wiring.md
- .scratch/inverse-thinking/004-quality-gates-and-repair.md
- .scratch/inverse-thinking/005-renderer-standalone-html.md
- .scratch/inverse-thinking/006-teacher-ui-structured-editor.md
