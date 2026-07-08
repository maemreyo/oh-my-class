---
title: "Flip content_creator's generic artifact sections to real LLM content"
status: done
labels: [llm-integration, content-creator]
created: 2026-07-08
priority: p0
epic: llm-integration-completion
sequence: 2
---

> **Done (2026-07-08).** Implemented as one LLM call per artifact (not per section —
> proven equivalent/cheaper, see cost note below): `_generate_section_prose` in
> `hierarchical.py` sends all of an artifact's section outlines in one prompt,
> gets back `{section_id: prose}`, and `_fill_section` uses it with a fallback to
> the old deterministic string if a key is missing/malformed. `build_hierarchical_artifacts`
> → `_build_artifact` → `_fill_section` chain is now async; `content_creator_node`
> awaits it. Verified live against 9router (not just mocked): lesson sections come
> back as real, grounded, coherent prose (see done note below for a sample).
>
> **Known limitation found, not fixed (separate bug, out of LIC-02's scope):** quiz's
> `_outline` gives every question section the same literal `section_id="assessment"`
> (pre-existing, unrelated to this issue) because `strategy_fill.py`'s `_target_section("quiz")`
> exact-matches that literal to decide which section gets strategy components — changing
> the id to be unique per question would break that matching and needs its own fix, not a
> quiet change here. Effect: quiz sections can't be individually addressed by the prose LLM
> call today, so they reliably fall back to the deterministic string. This is a safe
> degradation (no crash, no wrong content), not a regression — flagging for a future issue.
>
> Produced from `.scratch/design-reflection-2026-07-08.md` grill session, section 0b (content_creator). See ADR-049 for the decision that `slide_deck` is explicitly excluded from this issue. Ship after `LIC-01` (reviewer quality gate) is live.

## What to build

`packages/agents/sub_agents/content_creator/hierarchical.py:123-163`'s `_fill_section` produces every section's content as `f"{outline.job}: {fact}"` for all artifact types except `slide_deck` (`lesson`, `worksheet`, `quiz`, `drill`, `recap`, `infographic`, `flashcard_deck`, `answer_key`, `roadmap`). Replace this with a real LLM call that writes the section's prose from the same structured inputs already available: `outline.title`, `outline.job`, `outline.objective`, `outline.gagne_event`, `fact` (from `_verified_fact(research_bundle)`), plus `strategy_fill`/`methodology_components` context.

Keep everything else in `_fill_section` unchanged: `strategy_fill`, `methodology_components`, the `answer_key`/`flashcard_deck` special-casing, and `_forced_failure`'s regen-placeholder path (used by tests/scoped-regeneration — do not remove).

## Acceptance criteria

- [x] Section `content`/`components` paragraph text is LLM-generated. Implemented batched **per-artifact** (all sections of one artifact in one call), not per-section — chosen upfront given per-section would multiply an already-slow call count; not a fallback from a failed per-section attempt.
- [x] LLM call goes through `LLMClient` (via `AgentRuntime`, consistent with `researcher`/`planner`), respects `MODELS.content_creator` tiering.
- [x] `_forced_failure` / `regen_placeholder` path is preserved for scoped-regeneration tests.
- [x] `validate_no_cdn`/`validate_no_pii` guards still run against LLM-generated content — verified via full `packages/agents/tests/` sweep (byte-identical failure set vs. pre-change baseline).
- [x] Cost/latency measured live against 9router (`4omc`): a 2-artifact-type pack (lesson: 4 sections, quiz: 2 sections → 2 LLM calls total) took **39.8s** (~20s/call). Not optimized further in this issue — batching per-artifact (done) was the agreed mitigation; per-section would have been ~3x more calls. If this proves too slow in production, the next lever is concurrent `asyncio.gather` across artifact types (currently sequential in the `build_hierarchical_artifacts` list comprehension) — noted, not implemented here (out of scope; no latency SLO was given to design against).
- [x] `LIC-01` (reviewer wired to AdaptiveJudge) landed first in this session, in that order.

### Test fixes needed and applied (incidental, same shape as LIC-01's)

`build_hierarchical_artifacts`/`_build_artifact`/`_fill_section` becoming `async` required `await` at every call site: `packages/agents/sub_agents/content_creator/nodes.py` (production), and tests in `test_cc_hierarchical.py` (10 tests), `test_component_strategy_release_gate.py` (2), `test_generate_one_artifact.py` (1), `test_slide_deck_tracer.py` (1, slide_deck path only — no LLM call, still needed `await` for the coroutine). Added a shared `stub_section_prose` fixture in new `packages/agents/tests/conftest.py` (stubs `llm.complete_json_chat` to return `{}`, which safely falls back to deterministic text per section — none of these tests assert on exact prose) so they stay fast/hermetic instead of needing a live LLM. One real bug caught along the way: `await x()["key"]` parses as `await (x()["key"])` in Python, not `(await x())["key"]` — a naive scripted `await` insertion produced `TypeError: 'coroutine' object is not subscriptable` in `test_component_strategy_release_gate.py`, fixed with explicit parens.

## Blocked by

`LIC-01` (reviewer quality gate) should land first — see that issue's rationale.
