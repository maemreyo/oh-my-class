---
title: Official REAL LLM slide-deck acceptance harness
status: ready-for-agent
labels: [ready-for-agent, slide-deck]
created: 2026-07-07
---

## Parent

ADR-044: Slide Deck Real-LLM Acceptance Harness

## What to build

Promote slide-deck acceptance from ad-hoc smoke scripts into an official, documented, CI-ready real-LLM harness. This harness is the acceptance gate for the slide-deck production-hardening work. It must use real gateway HTTP, model `4omc`, real classroom prompts, real quality gates, real exports, and browser QA on actual exported HTML.

The harness must run three core scenarios: Grade 5 ESL vocabulary, Grade 5 math or science concept with worked example/practice, and Vietnamese classroom deck. It should classify failures, exercise real structured recovery where the application supports it, and write an evidence bundle for each run.

## Acceptance criteria

- [ ] An official harness script exists outside `.scratch` and can be invoked with explicit gateway URL, model, auth/JWT, and evidence output directory configuration.
- [ ] The harness runs three natural classroom scenarios with no marker/test prompt strings.
- [ ] Each scenario drives the real gateway HTTP surface, uses model `4omc`, waits for final run status, obtains the slide-deck snapshot/export, and records run and snapshot identifiers.
- [ ] Each scenario asserts meaningful deck shape: minimum six slides, required pedagogical spine, density/purpose checks, and prompt-relevant content.
- [ ] Each scenario asserts quality pass, standalone HTML export, no external assets, no raw prompt/marker leakage, and no teacher-only/answer-key leakage in student/presentation HTML.
- [ ] Browser QA opens the actual exported HTML and verifies navigation, mobile readability, print media shows all slides, and selected print settings apply.
- [ ] Failures are classified as generation sparse, quality fail, leakage, export/render fail, browser navigation fail, print fail, or infrastructure fail.
- [ ] Where real recovery exists, the harness exercises structured recovery rather than blind retrying; success must be on the actual repaired export.
- [ ] The harness exits non-zero if any scenario fails and writes a timestamped evidence bundle with summary JSON, scenario inputs, endpoint/model metadata, IDs, quality scores, export paths, assertions, and browser evidence.

## Blocked by

- SDH-02-safe-projections-and-chrome-policy.md
- SDH-03-standalone-presentation-print-controls.md
- SDH-05-print-layout-and-border-fidelity.md
- SDH-06-adaptive-content-density-and-deck-shape.md
