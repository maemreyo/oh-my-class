---
title: Teacher-safe slide deck failure UX and recovery messages
status: ready-for-agent
labels: [ready-for-agent, slide-deck, frontend]
created: 2026-07-07
---

## Parent

ADR-043: Slide Deck Display Preferences and Projection Boundaries
ADR-044: Slide Deck Real-LLM Acceptance Harness

## What to build

Make slide-deck failures understandable and actionable for teachers without exposing raw technical details, model traces, stack traces, or hidden teacher-only data. When sparse generation, quality failure, export failure, print failure, or recovery exhaustion occurs, the app should explain what happened in teacher-safe language and offer the next best action.

This slice should connect failure classification from quality/recovery/harness behavior to user-centric copy and UI states. It should preserve fail-closed behavior while avoiding generic or frightening errors.

## Acceptance criteria

- [ ] Sparse deck, quality gate, leakage, export/render, print, and infrastructure failures map to teacher-safe messages.
- [ ] Failure messages explain the next action: regenerate, revise prompt, inspect teacher notes, retry export, or contact/admin escalation as appropriate.
- [ ] No user-facing failure state exposes raw stack traces, raw model responses, hidden teacher-only data, answer keys, JWTs, or internal debug markers.
- [ ] Recovery states distinguish “repairing this slide/deck” from “full regeneration required” when scoped recovery is available.
- [ ] Student-facing surfaces never show teacher recovery/debug messages.
- [ ] Technical guards or UI tests cover representative failure states.
- [ ] Real-LLM acceptance evidence from SDH-07/SDH-10 can classify failures consistently with the teacher-facing categories.

## Blocked by

- SDH-02-safe-projections-and-chrome-policy.md
- SDH-06-adaptive-content-density-and-deck-shape.md
