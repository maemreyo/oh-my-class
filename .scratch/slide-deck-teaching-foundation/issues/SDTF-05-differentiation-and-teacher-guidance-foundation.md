---
title: Differentiation and teacher guidance foundation for slide decks
status: ready-for-agent
labels: [ready-for-agent, slide-deck]
created: 2026-07-07
---

## Parent

ADR-045: Slide Deck as Teaching Session Foundation

## What to build

Add or formalize teacher-only differentiation guidance in slide decks so teachers can adapt for mixed-ability classrooms without exposing ability labels or answer guidance to students. The initial foundation is teacher-only scaffold/stretch suggestions, not student-path variants.

Future sessions may support group-specific companion prompts, but this slice should keep v1 student output clean and projection-safe.

## Acceptance criteria

- [ ] Teacher-only notes can represent scaffold and stretch suggestions separately from answer keys.
- [ ] Student/presentation exports never expose differentiation notes, ability labels, teacher hints, or answer guidance.
- [ ] Teacher preview can show differentiation guidance in a planning panel or notes area.
- [ ] Quality checks treat differentiation guidance as teacher-only and verify no student leakage.
- [ ] The model leaves room for future group/level variants without implementing them in this slice.
- [ ] Real-LLM evidence includes at least one deck with useful teacher-only scaffold/stretch guidance and no student leakage.

## Blocked by

- SDTF-01-session-ready-ids-and-interaction-contract.md
- SDH-02-safe-projections-and-chrome-policy.md
