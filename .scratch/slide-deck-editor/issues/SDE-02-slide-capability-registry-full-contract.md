---
title: Full 21-layout/block/interaction registry contract
status: ready-for-agent
labels: [ready-for-agent, slide-deck, editor, contracts]
created: 2026-07-07
---

## Parent

ADR-047: Slide Deck Editor and AI-Assisted Revision (decision 2); closes an ADR-041 implementation gap

## What to build

`SlideLayout` currently has 5 values (`title, content, question, activity, summary`); ADR-041 specifies 21. Declare the full 21-value layout registry (plus the block and 7-interaction registries ADR-041 names) as a typed contract now — Python `Literal`/enum plus generated TypeScript/Zod types — so the schema is honest immediately, even though renderer support ships incrementally.

## Acceptance criteria

- [ ] `SlideLayout` (and block/interaction registries) declare all values from ADR-041's target vocabulary (`cover, agenda, objective, hook, concept, definition, comparison, timeline, process, diagram, worked_example, guided_practice, independent_practice, discussion, poll, quiz_check, reflection, summary, exit_ticket, homework, appendix`).
- [ ] Generated TS/Zod schemas stay in parity with the Python contract via the existing schema-generation path.
- [ ] Renderer/template support ships incrementally, prioritized by ADR-044's 3 official scenarios first.
- [ ] Any layout without renderer support fails closed with an explicit "not yet supported" error at generation/render time — never a silent fallback to a different layout.
- [ ] Each newly-supported layout ships with its own renderer test before being considered "supported" (no batch-implementing all 21 renderers without tests).

## Blocked by

None — schema declaration can start immediately; renderer implementation is incremental follow-on work.
