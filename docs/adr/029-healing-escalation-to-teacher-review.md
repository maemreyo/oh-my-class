# ADR-029: Healing Escalation to Teacher Review

## Status

**Proposed** (2026-07-03) — The self-healing "escalate" outcome ("Needs your review") is currently **unreachable in production**: the healing ladder never advances past `rewrite`, and even when escalate is chosen the route is a dead end. This ADR fixes both layers, defines what the teacher sees on escalate, and adds a deterministic test seam so the escalate scenario can be exercised end-to-end. Extends the round-2/3 agents-hardening finding that escalation was orphaned (see [[project_agents_hardening]]); companion to ADR-028.

## Context

Verified against code (2026-07-03):

1. **Ladder frozen at `rewrite`.** `fail_count` exists on `TeachingPackState` (`teaching_pack/nodes.py:79`) but is **never incremented/persisted** across healing rounds. `heal_quality_failure` reads it fresh from state (`healing_runtime.py`), and `HealingOrchestrator.heal` computes `fail_count = state.get("fail_count",0)+1` (`orchestrator.py`). Because the incremented value is never written back into the graph state between rounds, every quality failure recomputes `fail_count = 1` → strategy `rewrite`. `reroute` (2), `replan` (3), and `escalate` (>3) are effectively dead.
2. **Escalate route is a dead end.** `_route_for_healing` returns the string `"teacher_approval"` on escalate (`healing_runtime.py`), but `route_after_render_quality` and the compiled `render_quality` conditional-edge map only wire `planning_blueprint | post_blueprint_research | artifact_workflow | compliance_gate` (`quality_routing.py`, `graph.py:107-116`). `"teacher_approval"` falls through to `artifact_workflow` — the escalate branch never opens a teacher gate.
3. **No trigger.** There is no env/flag/hook to force repeated quality failure, so the path cannot be exercised over HTTP even for testing.

Net: the only human-review stop that ever opens is `content_approval` on the success path. For a K-12 product, a healing ladder whose terminal safety valve (escalate → human) is dead is a real defect, not just missing UX.

## Decision

### 1. Persist the healing counter across rounds

Increment and **write back** the healing counter into the graph state each healing round so the ladder actually advances `retry/rewrite → reroute → replan → escalate`. Track it at the granularity the fan-out already supports — per `artifact_id`/`workflow_id` where a single artifact is failing (aligns with scoped-replan, agents-hardening #27), falling back to run-level for upstream (blueprint/research) failures. The counter must round-trip through the reducer, not live only in a transient local.

### 2. Wire the escalate route

Add `teacher_approval` as a valid target of `route_after_render_quality` **and** to the `render_quality` conditional-edge map in `graph.py`, so `_route_for_healing`'s escalate decision reaches the gate instead of silently regenerating.

### 3. Escalate surfaces via the existing `content_approval` gate, flagged

On escalate, open the existing `content_approval` gate (not a new gate type) with:

```json
{
  "gate_name": "content_approval",
  "escalated": true,
  "needs_review": true,
  "escalate_reason": "Quality checks did not pass after N attempts.",
  "healing_history": [ ... ],
  "actions": ["approve", "approve_selected", "reject", "reject_selected", "edit"]
}
```

The teacher UI reuses the #29 explainable-gate surface with a distinct "Needs your review" badge + single CTA + healing history. Rationale: least new surface, consistent with the explainable-gate work already shipped, and it keeps the teacher able to rescue the run in place rather than restarting.

### 4. Deterministic test seam

Add a **test-only** `TEACHING_PACK_FORCE_ESCALATE` env flag read in `heal_quality_failure` that short-circuits to the escalate outcome. It is off by default and must never alter production behaviour; it exists so the teacher-scenario e2e driver and CI can exercise the escalate path deterministically without depending on real LLM quality failures. A guard test asserts it is inert unless explicitly set.

## Consequences

- The healing ladder becomes real end-to-end: transient/validation → rewrite → reroute → replan → **escalate → teacher gate**. INVARIANT-06's "cannot be silently bypassed" now has a live escalate counterpart.
- Escalate is exercisable in e2e/CI via the force seam, closing the "escalate scenario not triggerable" gap.
- Reuses the explainable-gate UI; the only UI delta is the escalated badge/reason.
- Touches healing state shape → must ship with unit tests for the ladder progression (fail_count 1→>3) and a graph test that escalate opens `content_approval` with `escalated=true`.
- Interacts with fast-lane (ADR-026): an escalated gate must **never** be fast-lane auto-approved — assert `escalated → manual_required`.

## Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| **Reuse content_approval + `escalated` flag (chosen)** | Least new surface; reuses #29 UI; teacher rescues run in place | Slightly overloads one gate name |
| Distinct `escalation_review` gate type | Clear semantics | New gate_name + registry + payload + UI + route — more surface to build/secure/test |
| No gate — status `needs_attention` + notify | Least code | Loses in-place rescue; teacher must restart; weaker than an interrupt gate for a safety valve |
| Leave escalate dead, document as known gap | Zero work | Terminal safety valve stays broken in a K-12 product — rejected |
