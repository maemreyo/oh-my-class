---
title: Typed seam-contract layer (producer ⊆ consumer, fail-closed)
status: done
labels: [done]
created: 2026-06-30
---

## What to build

Enforced **typed contracts at each agent→agent stage seam** — using LangGraph state + Pydantic, **not** a separate "RunContext blackboard" of new channels.

As-built clarification (corrects the original framing): the handoff is **not** lossy — `TeachingPackState` already carries the **full** `lesson_plan` and `research_bundle` across stages. The loss is **prompt-side**, inside `content_creator` (`summarizers.py` truncates to top-3 findings / top-5 sources / 6 objectives when building the prompt). A new channel layer would not fix that. So:

- Each seam (`planning_blueprint → post_blueprint_research → artifact_workflow → render_quality`) gets a **Pydantic contract** validating producer-output as consumer-input, **fail-closed** (raise on missing/malformed required fields — never silent degrade). Composes with content_creator's coverage contract and `testing/008` seam tests.
- Contracts live in `common/contracts/` (single source of truth) and are imported by **both** the producing and consuming stage.
- **Do NOT** introduce parallel `RunContext` state channels — type and contract the existing `TeachingPackState` at the seams instead.
- The "stop truncating" concern is **out of scope here** — it dissolves with per-section grounding (`agent-upgrades/003`) + semantic retrieval (`002b`), where context is scoped narrowly enough that truncation no longer harms. `summarizers.py` may be reduced to display-only.
- Deterministic; no Lead-Agent/ReAct.

## Acceptance criteria

- [ ] Each stage seam has a Pydantic contract (`producer ⊆ consumer`); a malformed or missing-required-field handoff is caught **fail-closed**.
- [ ] Seam contracts live in `common/contracts/` and are reused by both adjacent stages.
- [ ] No new parallel "RunContext" channel layer is added (existing `TeachingPackState` is typed/contracted in place).
- [ ] `summarizers.py` truncation is left to `agent-upgrades/003` or reduced to display-only here (no behavior regression).
- [ ] No regression in the deterministic stage flow.

## Detailed test suite

- [ ] `tests/integration/test_seam_contracts.py`: each seam validates producer→consumer; a deliberately malformed handoff fails closed (not a silent summary).
- [ ] `common/contracts/tests/test_seam_contract_models.py`: contract models reject missing required fields (deterministic).
- [ ] Run `uv run pytest tests/integration/test_seam_contracts.py common/contracts/tests/test_seam_contract_models.py -v`.

## Blocked by

None — can start immediately.
