---
title: Collapse dead sub-agent StateGraph wrappers (behavior-preserving)
status: done
labels: []
created: 2026-06-30
---

## What to build

After legacy decommission (parity issue 004), the per-sub-agent `agent.py` (`make_*_agent()` StateGraph builders), `*_graph_node` wrappers, and `adapters.py` (`OhMyClassState`↔sub-agent-state bridges) have no live caller — the teaching-pack runtime calls the node functions (`planner_node`, `researcher_node`, `content_creator_node`) directly. Collapse the 5-file sub-agent pattern to the 3 files the stage runtime uses (`nodes.py`, `state.py`, `prompts/`) to remove dead weight and the `OhMyClassState` coupling.

**This is a strictly behavior-preserving refactor. It must NOT drop any feature — only make the structure more modern/leaner.** Nothing the wrappers did may become unreachable; if a capability is only reachable through a wrapper, it is migrated to the node path FIRST, not deleted.

- For each sub-agent (planner, researcher, content_creator, roadmap, diagnostician, reviewer): confirm the **only** caller of its StateGraph wrapper / `*_graph_node` / adapters is the (now-removed) legacy graph. Delete only then.
- **Reviewer caveat**: if the 6-layer judge (layer4, parity issue 001) uses `make_reviewer_agent()` / the reviewer StateGraph, **keep it** — it has a live caller.
- Produce a per-agent capability inventory (what the wrapper provided) and prove each item is still reachable via the retained node path before deletion.

## Acceptance criteria

- [x] A per-agent audit confirms wrapper/`*_graph_node`/adapter callers; only legacy-only ones are removed, live ones (e.g. reviewer used by layer4) are kept.
- [x] No feature is lost: a capability inventory maps every wrapper-provided behavior to its retained node-path equivalent; nothing becomes unreachable.
- [x] Deleted files leave no dangling imports; `import-linter` and `dependency-cruiser` pass.
- [x] The teaching-pack runtime produces identical artifacts/behavior before vs after (golden comparison).
- [x] Remaining `OhMyClassState` coupling is reduced to what parity issue 002 (healing adapter) still requires.

## Detailed test suite

(Real DB + real LLM via 9router port 20228, model `4omc`.)

- [x] `packages/agents/tests/test_subagent_capability_parity.py`: for each retained node (`planner_node`/`researcher_node`/`content_creator_node`), the same input produces the same output shape/behavior as before the collapse (golden snapshot).
- [x] `packages/agents/tests/test_no_dead_subagent_wrappers.py`: removed `make_*_agent`/`*_graph_node`/adapters have no remaining importers; kept ones (reviewer) still resolve their live caller.
- [x] Feature-inventory check: a documented list of each sub-agent's capabilities, each marked reachable via the node path post-collapse.
- [x] Regression: `make test` + `make check` pass; teaching-pack e2e output unchanged.
- [x] Run `uv run pytest packages/agents/tests/test_subagent_capability_parity.py packages/agents/tests/test_no_dead_subagent_wrappers.py -v`.

## Blocked by

- .scratch/runtime-parity/004-legacy-runtime-decommission.md
