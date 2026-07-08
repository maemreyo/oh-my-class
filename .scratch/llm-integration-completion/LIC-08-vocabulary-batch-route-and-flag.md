---
title: "Build the missing production route into vocabulary_batch mode; flip its feature flag"
status: ready
labels: [llm-integration, vocabulary-batch, routing]
created: 2026-07-08
priority: p2
epic: llm-integration-completion
sequence: 8
---

> Produced from `.scratch/design-reflection-2026-07-08.md` grill session, section 0d — **corrects** `.scratch/ROADMAP.md`'s 2026-07-01 audit verdict on this epic (see `LGH` epic's ROADMAP update). The internal orchestration is NOT broken; the gap is upstream of it.

## What to build

`.scratch/ROADMAP.md`'s audit says `vocabulary-batch`'s "Orchestrator stops at `status=\"queued\"`; grounding→synthesis→practice→gate→export is never chained." Re-reading `packages/agents/teaching_pack/vocabulary_batch_orchestrator.py` as of 2026-07-08 shows this is stale: `_process_cluster` (`vocabulary_batch_orchestrator.py:184-224`) fully chains `gather_evidence → ground → synthesize → make_practice → evaluate`, called by `run_vocabulary_batch_orchestrator`, which `teaching_pack/nodes.py:453` does invoke.

The real, still-open gap is upstream:
1. `FEATURE_VOCABULARY_BATCH_V1` defaults to `false` (`packages/agents/config/features.py:17`).
2. No caller anywhere in `services/`/`packages/` (outside the orchestrator's own file and tests) ever sets `contract.mode == "vocabulary_batch"` — there is no route, API endpoint, or UI action that enters this mode at all.

Find or build the missing entry point (API route / UI action that lets a teacher submit a vocabulary batch), and flip the feature flag once that entry point exists and is tested.

## Acceptance criteria

- [ ] Identify (via `services/gateway/routers/`) whether a route for vocabulary-batch submission exists but doesn't set `contract.mode`, or whether no route exists at all.
- [ ] Build/fix the route so a real request can reach `contract.mode == "vocabulary_batch"`.
- [ ] Flip `FEATURE_VOCABULARY_BATCH_V1` default once the route is live and tested end-to-end (real DB + real LLM per repo testing policy).
- [ ] Update `.scratch/ROADMAP.md`'s vocabulary-batch verdict to reflect that internal chaining works; the historical POTEMKIN verdict was about routing/flag, not the orchestrator logic (this issue's `LGH` epic sibling handles the ROADMAP text itself).

## Blocked by

Nothing technical — needs a product decision on where the entry point should live (new route vs. existing route gains a mode param).
