---
title: Bounded upstream revision protocol (state-flag + conditional-edge router)
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Let a downstream stage signal an upstream one (content_creator → planner "objective X has no teachable content"; researcher → planner "the plan asserts a false claim"; reviewer → scoped replan) — **deterministically and bounded**, reusing the existing routing idiom.

As-built note: `render_quality` **already** reroutes upstream (`route_after_render_quality` → `planning_blueprint`/`post_blueprint_research`/`artifact_workflow`) via the `quality_recovery_route` state flag. That is the **reactive, post-hoc** upstream signal. This issue adds the **proactive, agent-asserted precondition failure** — complementary, not redundant.

- **Mechanism: state-flag + conditional-edge router, NOT `Command(goto)` emitted from inside agent nodes.** The agent writes a structured `revision_request` to state and returns normally; a dedicated **conditional-edge router** at the seam reads it and decides `goto` (the exact pattern `route_after_render_quality` already uses). This keeps routing centralized in one testable place per seam, deterministic, and avoids network-style control flow (no Lead-Agent/ReAct).
- **`RevisionRequest` schema** in `common/contracts/`: `{target_stage, reason, scope (artifact/section/objective), evidence}`.
- **One shared `upstream_cycle_count`** (global, monotonic) bounds **both** agent-revision **and** the existing quality-reroute — a single termination guarantee, so the two mechanisms cannot ping-pong past the budget. Optional **per-seam soft cap** for early escalation / observability only (the global counter is the hard bound).
- **Exhaustion → escalate** by routing to `teacher_approval` with a `revision_exhausted` payload, **reusing the existing `interrupt()` HITL gate** — no new escalation path.
- Composes with the scoped repair loop (`agent-upgrades/007`). Every revision is traced (`004a`).

## Acceptance criteria

- [ ] A `RevisionRequest` schema exists; a downstream stage writes `revision_request` to state and a **conditional-edge router** routes upstream (no `Command(goto)` from inside agent nodes).
- [ ] A **single shared** `upstream_cycle_count` bounds quality-reroute + agent-revision together; the flow provably terminates (bound test).
- [ ] Exceeding the budget escalates via the existing teacher `interrupt()` gate (`revision_exhausted`).
- [ ] Routing decisions are deterministic and pure-testable from synthetic state; every revision is traced.

## Detailed test suite

- [ ] `packages/agents/tests/test_revision_protocol.py`: content_creator writes a RevisionRequest → router routes to `planning_blueprint` with the request in state; planner revises scoped; flow resumes.
- [ ] `packages/agents/tests/test_revision_bound.py`: repeated agent-revisions **and** quality reroutes share one budget; hitting the cap escalates to the teacher (no infinite loop).
- [ ] `packages/agents/tests/test_revision_router_pure.py`: router returns correct target from synthetic state (deterministic, no LLM).
- [ ] Run `uv run pytest packages/agents/tests/test_revision_*.py -v`.

## Blocked by

- .scratch/agent-interaction/001-seam-contract-layer.md
