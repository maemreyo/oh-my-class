---
title: Remove/park dead Lead Agent + clean dangling prod-compose dependency
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

The Lead Agent is dead code: `lead_agent_node` bridges `OhMyClassState` (the legacy state, used only by the removed 18-node graph), nothing in the teaching-pack runtime or gateway invokes it, and `make_lead_agent`'s `create_react_agent` is passed no middleware. Keeping a ReAct orchestrator contradicts the deterministic stage-graph (ADR-002) and INVARIANT-01.

- **Remove the ReAct orchestrator + bridge**: `lead_agent/agent.py` (`make_lead_agent`), `lead_agent/node.py` (`lead_agent_node`), and the `OhMyClassState` bridge. **Keep** the middleware *definitions* (reused by technical-debt/002) and the sub-agent *tools* if still useful.
- If a future conversational/tool-using surface is wanted, it is re-introduced deliberately then — not kept as dormant dead code now.
- **Clean infra**: remove the dangling `litellm.depends_on: 9router: service_healthy` in `docker-compose.prod.yml` (9Router runs on host by design); document the host-9Router topology.
- Confirm `packages/agents/state.py::OhMyClassState` has no remaining live consumers after this; remove or clearly mark legacy.

## Acceptance criteria

- [ ] `make_lead_agent`/`lead_agent_node` and the `OhMyClassState` bridge are removed; middleware definitions are retained for reuse.
- [ ] No live importer references the removed Lead Agent symbols; `import-linter` passes.
- [ ] `OhMyClassState` has no live consumers (removed or marked legacy with a note).
- [ ] The dangling `9router` `depends_on` is removed from the prod overlay; host-9Router topology documented.

## Detailed test suite

- [ ] `tests/test_no_lead_agent.py`: no live import of `make_lead_agent`/`lead_agent_node`; `OhMyClassState` unused by the runtime.
- [ ] Compose lint/test: prod overlay has no undefined-service `depends_on`.
- [ ] Regression: `make test` + `make check` pass; teaching-pack flow unchanged.
- [ ] Run `uv run pytest tests/test_no_lead_agent.py -v` and a compose validation.

## Blocked by

- .scratch/technical-debt/002-middleware-wiring-and-runner.md  (retain middleware defs before removing their old host)
