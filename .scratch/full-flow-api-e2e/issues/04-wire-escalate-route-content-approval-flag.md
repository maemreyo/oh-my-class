# [FFA-04] Wire escalate route → `content_approval` with `escalated` flag

Status: DONE
Labels: full-flow-api, healing, gateway
ADR: 029
Depends on: FFA-03

## Context

Even when escalate is chosen, `_route_for_healing` returns `"teacher_approval"`
(`teaching_pack/healing_runtime.py`) but that target is NOT in `route_after_render_quality`
nor the `render_quality` conditional-edge map (`quality_routing.py`, `graph.py:107-116`) —
it falls through to `artifact_workflow`, so escalate never opens a teacher gate. This is a
dead safety valve for a K-12 product.

## Scope

- [x] Add `teacher_approval` as a valid target of `route_after_render_quality`
      (`quality_routing.py`) AND to the `render_quality` conditional-edge map in `graph.py`.
- [x] On escalate, open the existing `content_approval` gate flagged
      `escalated=true`, `needs_review=true`, with `escalate_reason` + `healing_history`
      in the gate payload (reuse the #29 explainable-gate surface; teacher UI shows a
      "Needs your review" badge + single CTA).
- [x] Ensure an escalated gate is NEVER fast-lane auto-approved (ADR-026): assert
      `escalated → approval_mode == manual_required`.

## Acceptance

- Graph test: an escalate decision routes to `content_approval` and the gate payload has
  `escalated=true` + reason + healing_history.
- Test: fast-lane cannot auto-approve an escalated gate.
- UI reflects the escalated badge (component test).

## References

- ADR-029, ADR-026 (fast-lane). `quality_routing.py`, `graph.py:107-116`,
  `healing_runtime.py`, `teaching_pack/nodes.py` (_teacher_approval), teacher gate UI (#29).
