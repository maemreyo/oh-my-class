---
title: Slide deck production hardening runbook and release evidence
status: ready-for-agent
labels: [ready-for-agent, slide-deck]
created: 2026-07-07
---

## Parent

ADR-043: Slide Deck Display Preferences and Projection Boundaries
ADR-044: Slide Deck Real-LLM Acceptance Harness

## What to build

Document the production-hardening workflow so future agents and developers know which decisions govern slide-deck display preferences, projections, print behavior, student chrome, and real-LLM acceptance. Update the testbook/runbook with commands, environment requirements, evidence bundle locations, and interpretation rules.

This slice should make the release evidence unambiguous: deterministic guard tests may be useful, but the feature is not done unless the real-LLM acceptance harness passes and the final report names the real run IDs, snapshot IDs, export paths, and evidence bundle path.

## Acceptance criteria

- [ ] The testbook/runbook documents the official real-LLM slide-deck acceptance command and required environment variables.
- [ ] The runbook explains the three acceptance scenarios and the expected evidence bundle contents.
- [ ] The runbook states that fixture/mock/deterministic tests are technical guards only and cannot prove this feature done.
- [ ] The release checklist includes student-safe projection, chrome policy, print layout, border fidelity, accessibility, and real browser QA checks.
- [ ] The docs link ADR-043, ADR-044, and the SDH issue set.
- [ ] The final release-evidence format requires run ID, snapshot ID, export path, quality pass result, and evidence bundle path for each real scenario.
- [ ] The documentation avoids secrets, local-only absolute paths as normative commands, and any claim that native PDF/PPTX or teacher-notes print is in v1.

## Blocked by

- SDH-07-real-llm-acceptance-harness.md
