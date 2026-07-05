---
title: Add teacher-facing strategy preview to blueprint approval
status: ready-for-agent
labels: [component-strategist, frontend, ui-ux]
created: 2026-07-05
---

## Parent

ADR-035.

## What to build

Add a compact Teaching Strategy panel to the existing blueprint approval experience after final strategy planning. The panel must help teachers trust the recommended strategy without turning the product into a component editor.

The panel shows the finalized recommended strategy, why it was chosen, key learning moves, selected component types/families, optional alternatives, tradeoffs, export/fallback warnings if any, and lightweight feedback actions. Teacher feedback must be sent as typed events, not free-form prompt blobs.

## Acceptance criteria

- [ ] Blueprint approval UI displays strategy summary when `component_strategy_plan` exists and gracefully hides it for old/flag-off runs.
- [ ] UI shows recommended strategy, selected learning moves, component types, teacher-facing rationale, and up to two meaningful variants.
- [ ] UI uses progressive disclosure: compact rationale by default; details panel can show ordered moves, artifact projections, tradeoffs, fallback/export warnings, and teacher-only/student-facing split.
- [ ] Teacher can approve, switch strategy variant, request more/less of a style, or reject with bounded reason values.
- [ ] Teacher can edit objective priority/assessability, delivery context when ambiguous/material, and bounded strategy intent/style controls; the UI does not expose arbitrary exact component placement in v1.
- [ ] Feedback actions map to typed teacher feedback contracts from CS-01.
- [ ] Explicit teacher feedback conflicts render engine-authored typed options and explain what constraint prevented full application.
- [ ] Fallback-only profiles appear as notes when active, not normal selectable variants.
- [ ] Numeric strategy quality scores stay debug-only; teacher UI shows actionable qualitative states such as strong fit, good fit with tradeoff, fallback used, or needs teacher choice.
- [ ] UI remains compact; no full component-by-component editor in v1.
- [ ] UI never asks teacher to approve provisional strategy; approval is for finalized strategy only.
- [ ] Accessibility and responsive behavior are verified for the new panel.
- [ ] Tests cover rendering with strategy, rendering without strategy, variant switch, bounded feedback submission, and CJK/Vietnamese text clipping/responsiveness where relevant.

## Blocked by

- CS-01 contracts and immutable strategy snapshot.
- CS-04 LangGraph stage and blueprint payload.

## References

- `docs/adr/035-component-strategist-stage.md`
- `apps/web/src/app`
- `apps/web/src/components`
- `services/gateway/routers/teaching_packs.py`
- `packages/agents/teaching_pack/gates.py`
- `packages/agents/teaching_pack/teacher_memory.py`

## Implementation notes

- This is frontend/UI work: use the frontend and visual QA skills when implementing.
- Keep the design user-centric: the teacher should understand “why this strategy” in seconds.
- Do not expose developer score ledger in normal UI.
- Material strategy revisions after feedback show a concise diff/summary and require reapproval only when teacher-visible pedagogy changes.
- Free-text feedback can be collected as a supplemental note, but it is not direct selector input and must not be stored in immutable strategy snapshot as raw text.
