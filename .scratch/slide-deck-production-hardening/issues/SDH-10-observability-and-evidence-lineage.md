---
title: Slide deck observability and evidence lineage
status: ready-for-agent
labels: [ready-for-agent, slide-deck]
created: 2026-07-07
---

## Parent

ADR-044: Slide Deck Real-LLM Acceptance Harness

## What to build

Add enough slide-deck lineage to debug and audit real-LLM acceptance runs without reading raw logs manually. A production evidence bundle should tie together the teacher prompt, model/endpoint, run ID, snapshot ID, selected display preferences, projection surface, export path, quality result, recovery attempts, browser QA result, and failure classification.

This slice should align runtime observability and harness evidence. The goal is not noisy telemetry; it is a clear chain from real generation to rendered export so a failed acceptance run can be diagnosed and a passed run can be trusted.

## Acceptance criteria

- [ ] Real acceptance evidence records `run_id`, `snapshot_id`, model, endpoint, scenario, final status, quality result, export path, and effective display preferences.
- [ ] Evidence can distinguish generation/content failures from projection, export, browser navigation, print, leakage, and infrastructure failures.
- [ ] Structured recovery attempts, if exercised, are recorded with attempt number, failure type, recovery route, and resulting snapshot/export.
- [ ] Runtime or harness logs do not include secrets, raw credentials, JWTs, or student PII.
- [ ] Evidence lineage makes it clear which exported HTML file was used for browser/mobile/print QA.
- [ ] The final report format can cite evidence bundle paths and IDs without copying huge raw outputs into chat.
- [ ] SDH-07 uses this lineage in its summary JSON and exits non-zero if required lineage fields are missing.

## Blocked by

- SDH-07-real-llm-acceptance-harness.md
