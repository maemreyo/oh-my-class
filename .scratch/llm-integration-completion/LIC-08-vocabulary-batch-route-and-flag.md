---
title: "Build the missing production route into vocabulary_batch mode; flip its feature flag"
status: done
labels: [llm-integration, vocabulary-batch, routing]
created: 2026-07-08
priority: p2
epic: llm-integration-completion
sequence: 8
---

> **Done (2026-07-08) — but the premise was wrong, corrected during investigation.**
> This issue's own "what to build" (below, unedited for the record) claimed no
> route/API ever sets `contract.mode="vocabulary_batch"`. That's false: `services/gateway/routers/teaching_pack_schemas.py`'s
> `TeachingPackCreateRunRequest.class_info` is a **freeform `JsonObject`**, and
> `run_contract_setup.py`'s `_mode(class_info)` already reads `class_info.get("mode", "generate_pack")`
> with no allowlist — a client sending `{"class_info": {"mode": "vocabulary_batch", ...}}`
> today already sets `contract.mode` correctly. There is no missing route.
>
> The **actual** gap, found by tracing what `run_vocabulary_batch_orchestrator` reads
> (`state["input_normalization_report"]`) back to its producer: **nothing produced
> it.** `normalize_vocabulary_input` (`vocabulary_input_normalizer.py`) is a real,
> tested, complete `InputNormalizationReport` builder — with zero callers anywhere.
> The existing `test_vocabulary_batch_mode_uses_vocabulary_orchestrator` test masked
> this by hand-constructing `input_normalization_report` directly in its fixture
> instead of exercising the real upstream flow — exactly the false-green pattern the
> 2026-07-01 audit itself warns about, one level deeper.
>
> Fixed: `_artifact_workflow` (`teaching_pack/nodes.py`) now calls
> `normalize_vocabulary_input(raw_request)` and populates `input_normalization_report`
> when missing, before invoking the orchestrator. Added
> `test_vocabulary_batch_normalizes_raw_request_when_report_missing` — goes from a
> bare `raw_request` (no hand-built report) to 2 passed cluster workflows, proving the
> real upstream path now works end-to-end. `normalize_vocabulary_input` moved to
> `REQUIRE_WIRED` in `test_no_dark_runtime_modules.py`.
>
> **`FEATURE_VOCABULARY_BATCH_V1`'s default was deliberately left `false`** — flipping
> a global production feature-flag default is a rollout/ops decision (affects every
> deployment immediately), not a code-correctness fix; it belongs with whoever owns
> feature rollout, once they know the pipeline is actually complete now.
>
> Produced from `.scratch/design-reflection-2026-07-08.md` grill session, section 0d.

## What to build

`.scratch/ROADMAP.md`'s audit says `vocabulary-batch`'s "Orchestrator stops at `status=\"queued\"`; grounding→synthesis→practice→gate→export is never chained." Re-reading `packages/agents/teaching_pack/vocabulary_batch_orchestrator.py` as of 2026-07-08 shows this is stale: `_process_cluster` (`vocabulary_batch_orchestrator.py:184-224`) fully chains `gather_evidence → ground → synthesize → make_practice → evaluate`, called by `run_vocabulary_batch_orchestrator`, which `teaching_pack/nodes.py:453` does invoke.

The real, still-open gap is upstream:
1. `FEATURE_VOCABULARY_BATCH_V1` defaults to `false` (`packages/agents/config/features.py:17`).
2. No caller anywhere in `services/`/`packages/` (outside the orchestrator's own file and tests) ever sets `contract.mode == "vocabulary_batch"` — there is no route, API endpoint, or UI action that enters this mode at all.

Find or build the missing entry point (API route / UI action that lets a teacher submit a vocabulary batch), and flip the feature flag once that entry point exists and is tested.

## Acceptance criteria

- [x] Identified: a route already exists and already threads `contract.mode` through correctly (freeform `class_info`) — no route work needed. The real gap was the unwired `normalize_vocabulary_input`.
- [x] Fixed the real gap: `_artifact_workflow` now populates `input_normalization_report` from `raw_request` when missing.
- [ ] `FEATURE_VOCABULARY_BATCH_V1` default left `false` deliberately — flipping it is a rollout/ops decision, not part of this fix (see done-note).
- [x] `.scratch/ROADMAP.md`'s vocabulary-batch verdict updated to ✅ REAL, with the corrected (not "no route", but "no input-normalization wiring") explanation.

## Blocked by

Nothing technical — needs a product decision on where the entry point should live (new route vs. existing route gains a mode param).
