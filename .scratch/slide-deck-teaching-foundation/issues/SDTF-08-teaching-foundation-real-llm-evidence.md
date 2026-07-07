---
title: Real-LLM evidence for slide-deck teaching foundation
status: ready-for-agent
labels: [ready-for-agent, slide-deck]
created: 2026-07-07
---

## Parent

ADR-044: Slide Deck Real-LLM Acceptance Harness
ADR-045: Slide Deck as Teaching Session Foundation

## What to build

Extend the real-LLM acceptance harness or evidence checklist so foundation-level slide-deck claims are proven with real generated decks, not just contracts or fixtures. The evidence should show that decks are teaching-session-ready in structure even though v1 remains standalone/local-only.

The harness should verify stable IDs, interaction readiness, pedagogical roles, planned pacing, related-artifact references where applicable, teacher-only differentiation guidance, localization behavior, inline/offline-safe visual support where appropriate, and no student-response persistence.

## Acceptance criteria

- [ ] Real-LLM evidence includes stable deck/slide/block/interaction IDs suitable for future session binding.
- [ ] Real-LLM evidence checks typed pedagogical roles and planned pacing for the required deck spine.
- [ ] Real-LLM evidence confirms interactions are local-only in v1: no response persistence endpoints or stored student answers.
- [ ] Real-LLM evidence includes teacher-only guidance/differentiation where expected and verifies no student leakage.
- [ ] Real-LLM evidence checks primary locale/chrome behavior for Vietnamese or bilingual scenarios.
- [ ] Real-LLM evidence checks inline/offline-safe diagrams or visual blocks for math/science when appropriate, including alt/fallback text.
- [ ] The evidence bundle records these foundation checks alongside run ID, snapshot ID, export path, quality result, and browser QA.
- [ ] The harness exits non-zero if foundation claims are missing for scenarios where they are required.

## Blocked by

- SDH-07-real-llm-acceptance-harness.md
- SDTF-01-session-ready-ids-and-interaction-contract.md
- SDTF-02-pedagogical-roles-and-planned-pacing.md
- SDTF-05-differentiation-and-teacher-guidance-foundation.md
