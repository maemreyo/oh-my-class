---
title: Command-based upstream revision protocol (bounded)
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Let a downstream agent signal an upstream one (e.g. content_creator → planner "objective X has no teachable content"; researcher → planner "the plan asserts a false claim"; reviewer → scoped replan) — using LangGraph's native **`Command(goto=..., update=...)`**, deterministically and bounded (no free loops, no Lead-Agent).

- **`RevisionRequest` schema**: `{target_stage, reason, scope (artifact/section/objective), evidence}`.
- A node emits `Command(goto=<upstream_stage>, update={"revision_request": ..., "revision_count": n+1})` to route upstream + carry the request.
- **Bounded**: per-seam + global `revision_count` cap; exceeding → escalate to the teacher (don't ping-pong planner↔content_creator).
- Composes with the scoped repair loop (`agent-upgrades/007`): reviewer issues use the same Command-based scoped routing.
- Every revision is traced (RunEvent/Langfuse).

## Acceptance criteria

- [ ] A `RevisionRequest` schema exists; downstream agents emit `Command(goto=upstream, update=...)` to request scoped revision.
- [ ] Revisions are bounded (per-seam + global counter); exceeding escalates to the teacher.
- [ ] No infinite upstream loop is possible (proven by a bound test).
- [ ] Revision routing is deterministic and traced.

## Detailed test suite

- [ ] `packages/agents/tests/test_revision_protocol.py`: content_creator emitting a RevisionRequest routes to planner with the request in state; planner revises scoped; flow resumes.
- [ ] `test_revision_bound.py`: repeated revision requests hit the cap and escalate to the teacher (no infinite loop).
- [ ] Run `uv run pytest packages/agents/tests/test_revision_protocol.py packages/agents/tests/test_revision_bound.py -v`.

## Blocked by

- .scratch/agent-interaction/001-shared-context-and-seam-contracts.md
