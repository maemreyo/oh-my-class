---
title: Remove/park dead Lead Agent + clean dangling prod-compose dependency
status: done
labels: []
created: 2026-06-30
---

## What to build

The Lead Agent is dead code: `lead_agent_node` bridges `OhMyClassState` (the legacy state, used only by the removed 18-node graph), nothing in the teaching-pack runtime or gateway invokes it, and `make_lead_agent`'s `create_react_agent` is passed no middleware. Keeping a ReAct orchestrator contradicts the deterministic stage-graph (ADR-002) and INVARIANT-01.

- **Remove the ReAct orchestrator + bridge**: `lead_agent/agent.py` (`make_lead_agent`), `lead_agent/node.py` (`lead_agent_node`), and the `OhMyClassState` bridge. **Keep** the middleware *definitions* (reused by technical-debt/002) and the sub-agent *tools* if still useful.
- If a future conversational/tool-using surface is wanted, it is re-introduced deliberately then — not kept as dormant dead code now.
- **Clean infra**: remove the dangling `litellm.depends_on: 9router: service_healthy` in `docker-compose.prod.yml` (9Router runs on host by design); document the host-9Router topology.
- Confirm `packages/agents/state.py::OhMyClassState` has no remaining live consumers after this; remove or clearly mark legacy.

## Acceptance criteria

- [x] `make_lead_agent`/`lead_agent_node` are removed; middleware definitions are retained for reuse.
- [x] No live importer references the removed Lead Agent symbols; guarded by `tests/test_no_lead_agent.py`.
- [x] `OhMyClassState` is marked legacy; retained consumers are legacy graph nodes, healing adapters, and middleware definitions.
- [x] The prod overlay has no dangling `9router`/`router` dependency; host-9Router topology is documented in `docs/system/ARCHITECTURE.md`.

## Detailed test suite

- [x] `tests/test_no_lead_agent.py`: no live import of `make_lead_agent`/`lead_agent_node`; removed bridge modules stay gone.
- [x] Compose guard: prod overlay has no undefined host-9Router service dependency.
- [x] Regression: focused teaching-pack and middleware suite unchanged.
- [x] Run `uv run pytest tests/test_no_lead_agent.py -v` and focused regression.

## Blocked by

- .scratch/technical-debt/002-middleware-wiring-and-runner.md  (retain middleware defs before removing their old host)
