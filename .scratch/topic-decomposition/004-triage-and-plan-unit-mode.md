---
title: Decomposition triage stage and plan_unit mode selection
status: done
labels: [done]
created: 2026-06-30
---

## What to build

Add the stage that decides whether a topic is a single lesson or a multi-session unit, and surfaces the suggestion at the existing `contract_confirmation` gate (ADR-017 §Trigger). The decision locks `mode` into the `RunContract`.

**Target the teaching-pack stage runtime** (`packages/agents/teaching_pack/`), not the legacy `packages/agents/graph.py`. Add a `TRIAGE` stage to `TeachingPackStage` (`stages.py`) that runs after `SETUP_CONTRACT`:

- **Heuristics first** (cheap, deterministic): `duration_minutes > 90`; regex over `raw_request` for "qua N tuần/buổi/tiết"; explicit teacher session count.
- **LLM fallback only when ambiguous**: estimate competencies / content strands (report §6.5) to recommend split vs single. Real LLM via 9router port 20228, model `4omc`.
- Writes `decomposition_intent { suggested_mode, target_sessions, session_length_minutes, source, rationale }` into the contract path so the existing `contract_confirmation` gate payload (`run_contract_setup.py`) shows the suggestion.

Gate behind `features.topic_decomposition_v1`. Flag off → `TRIAGE` is a pass-through no-op and the flow is the standard single-lesson stage path.

## Acceptance criteria

- [x] A `TRIAGE` stage exists in `TeachingPackStage` and runs after `SETUP_CONTRACT` in `build_teaching_pack_graph`.
- [x] Heuristic path runs with no LLM call for clear cases (duration > 90, explicit "N tiết/tuần", explicit count); `source` distinguishes `heuristic` vs `auto` (LLM).
- [x] The `contract_confirmation` gate payload includes the decomposition suggestion + rationale; teacher confirmation locks `RunContract.mode` to `plan_unit` or `generate_pack`.
- [x] With the flag disabled, `TRIAGE` is a no-op and existing contract-confirmation behavior is byte-for-byte unchanged.
- [x] Triage never decomposes silently — it only suggests; the teacher confirms.

## Detailed test suite

(Real DB + real LLM via 9router port 20228, model `4omc`; deterministic for heuristics.)

- [x] `packages/agents/tests/test_triage_stage_heuristics.py`: "dạy thì hiện tại trong 3 tuần" → `suggested_mode=plan_unit`, `source=heuristic`, no LLM call.
- [x] same file: a short single-concept request < 90 min → `suggested_mode=generate_pack` via heuristics, no LLM call.
- [x] `packages/agents/tests/test_triage_stage_llm.py`: an ambiguous broad topic invokes the LLM fallback seam and returns a bounded `target_sessions` with rationale.
- [x] `services/gateway/tests/test_contract_confirmation_decomposition.py`: after triage, the `contract_confirmation` gate payload contains the suggestion; confirming `plan_unit` persists `RunContract.mode="plan_unit"`.
- [x] Feature-flag test: flag disabled → `TRIAGE` no-op, contract confirmation identical to baseline.
- [x] Run `uv run pytest packages/agents/tests/test_triage_stage_*.py services/gateway/tests/test_contract_confirmation_decomposition.py -v`.

## Verification

```
uv run pytest packages/agents/tests/test_triage_stage_heuristics.py tests/trajectory/test_stage_order.py -q
12 passed in 0.30s

uv run pytest packages/agents/tests/test_triage_stage_heuristics.py \
  packages/agents/tests/test_triage_stage_llm.py \
  services/gateway/tests/test_contract_confirmation_decomposition.py -q
10 passed in 0.59s
```

- `test_triage_stage_heuristics.py`: 7 tests — duration heuristic, Vietnamese multi-session regex patterns, feature flag on/off
- `test_stage_order.py`: 5 tests — stage list order (now 9 stages with TRIAGE at index 1), no duplicates, event name consistency

## Blocked by

- .scratch/topic-decomposition/001-contracts-and-codegen.md
