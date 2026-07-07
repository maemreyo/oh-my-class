---
title: Slide pedagogical roles and planned pacing foundation
status: ready-for-agent
labels: [ready-for-agent, slide-deck]
created: 2026-07-07
---

## Parent

ADR-045: Slide Deck as Teaching Session Foundation

## What to build

Add a small typed pedagogical-role and planned-pacing foundation so slide decks can support teacher planning, density checks, quality review, and future session analytics. Visual layout should remain separate from pedagogical purpose.

The initial role taxonomy should be small and extensible: hook, objective, explain, model, guided practice, check understanding, independent practice, recap, and exit ticket. Planned pacing should support per-slide or per-activity estimated minutes so the app can reason about lesson duration without tracking live session time yet.

## Acceptance criteria

- [ ] Slide or block metadata can represent typed pedagogical role separately from visual layout.
- [ ] The engine can assign roles for the required deck spine and optional extensions.
- [ ] Planned duration metadata can represent estimated time per slide/activity and total deck pacing.
- [ ] Density/quality checks can use role-specific expectations rather than only layout or character count.
- [ ] Teacher preview can expose lesson flow/pacing information without leaking teacher-only data to student surfaces.
- [ ] Real-LLM evidence includes role/pacing sanity checks for at least the ESL and math/science scenarios.

## Blocked by

- SDTF-01-session-ready-ids-and-interaction-contract.md
