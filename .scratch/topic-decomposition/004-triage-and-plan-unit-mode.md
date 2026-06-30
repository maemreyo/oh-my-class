---
title: Decomposition triage node and plan_unit mode selection
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Add the step that decides whether a topic is a single lesson or a multi-session unit, and surfaces the suggestion to the teacher at the existing `contract_confirmation` gate (ADR-017 §Trigger). The decision locks `mode` into the `RunContract`.

`packages/agents/nodes/triage.py` (`step_02b_triage`), run after quickstart and before contract confirmation:

- **Heuristics first** (cheap, deterministic): `duration_minutes > 90`; regex over `raw_request` for "qua N tuần/buổi/tiết"; explicit teacher session count.
- **LLM fallback only when ambiguous**: estimate competencies / content strands (report §6.5) to recommend split vs single.
- Writes a suggestion onto the contract path: `decomposition_intent { suggested_mode, target_sessions, session_length_minutes, source, rationale }` for the `contract_confirmation` gate payload.

Gate this behind `features.topic_decomposition_v1`. When the flag is off, triage is a no-op and the flow is the standard single-lesson path.

## Acceptance criteria

- [ ] `step_02b_triage` exists as a standalone node, testable without the full graph.
- [ ] Heuristic path runs with no LLM call for clear cases (duration > 90, explicit "N tiết/tuần", explicit session count).
- [ ] LLM fallback runs only when heuristics are inconclusive and records `source="auto"` vs `source="heuristic"`.
- [ ] The `contract_confirmation` gate payload includes the decomposition suggestion and rationale; teacher confirmation locks `RunContract.mode` to `plan_unit` or `generate_pack`.
- [ ] With `features.topic_decomposition_v1` disabled, triage is a no-op and existing contract-confirmation behavior is unchanged.
- [ ] Triage never silently decomposes — it only suggests; the teacher confirms.

## Detailed test suite

(Real LLM via 9router port 20228, model `4omc`, for the fallback path; deterministic for heuristics.)

- [ ] `packages/agents/tests/test_triage_heuristics.py`: "dạy thì hiện tại trong 3 tuần" → `suggested_mode=plan_unit`, `source=heuristic`, no LLM call made.
- [ ] same file: a short single-concept request under 90 min → `suggested_mode=generate_pack` via heuristics, no LLM call.
- [ ] `packages/agents/tests/test_triage_llm_fallback.py`: an ambiguous broad topic with no explicit signals invokes the real LLM and returns a bounded `target_sessions` with rationale.
- [ ] `packages/agents/tests/test_triage_gate_payload.py`: after triage, the contract-confirmation gate payload contains the suggestion; confirming `plan_unit` sets `RunContract.mode="plan_unit"`.
- [ ] Feature-flag test: flag disabled → triage no-op, contract confirmation identical to baseline.
- [ ] Run `uv run pytest packages/agents/tests/test_triage_*.py -v`.

## Blocked by

- .scratch/topic-decomposition/001-contracts-and-codegen.md
