---
title: Shared in-run context (blackboard) + typed handoff contracts per seam
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Replace lossy point-to-point handoff (the `summarizers.py` truncation between planner→content_creator) with a structured shared in-run context and enforced seam contracts — using LangGraph **state channels** (the native blackboard), not a custom layer.

- **`RunContext` blackboard**: a structured, versioned set of state channels every agent reads — persona (3-source view), grounding, researcher **verified-facts + provenance**, component-registry view, methodology, structured lesson_plan. Concurrent writes merged by **order-stable reducers** (`Annotated[..., reducer]`).
- **Typed handoff contract per seam**: each agent→agent boundary validates producer-output as consumer-input (Pydantic), enforced — no silent lossy summary. (Composes with content_creator's coverage contract and testing/008 seam tests.)
- Keep the runtime deterministic (no Lead-Agent/ReAct).

## Acceptance criteria

- [ ] `RunContext` is a typed set of state channels read by all agents (persona/grounding/verified-facts/components/methodology/plan); lossy `summarizers` truncation is removed or reduced to display-only.
- [ ] Each agent→agent seam has an enforced typed contract (producer ⊆ consumer); a corrupted handoff is caught.
- [ ] Concurrent state writes use order-stable reducers (deterministic merge).
- [ ] No regression in the deterministic stage flow.

## Detailed test suite

- [ ] `packages/agents/tests/test_run_context.py`: agents read the structured RunContext (not a truncated summary); a missing required channel is caught at the seam.
- [ ] `tests/integration/test_seam_contracts.py`: each seam validates producer→consumer; a deliberately malformed handoff fails.
- [ ] Reducer determinism test: out-of-order concurrent writes merge to the same result.
- [ ] Run `uv run pytest packages/agents/tests/test_run_context.py tests/integration/test_seam_contracts.py -v`.

## Blocked by

None - can start immediately
