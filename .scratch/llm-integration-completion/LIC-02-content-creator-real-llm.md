---
title: "Flip content_creator's generic artifact sections to real LLM content"
status: ready-for-agent
labels: [llm-integration, content-creator]
created: 2026-07-08
priority: p0
epic: llm-integration-completion
sequence: 2
---

> Produced from `.scratch/design-reflection-2026-07-08.md` grill session, section 0b (content_creator). See ADR-049 for the decision that `slide_deck` is explicitly excluded from this issue. Ship after `LIC-01` (reviewer quality gate) is live.

## What to build

`packages/agents/sub_agents/content_creator/hierarchical.py:123-163`'s `_fill_section` produces every section's content as `f"{outline.job}: {fact}"` for all artifact types except `slide_deck` (`lesson`, `worksheet`, `quiz`, `drill`, `recap`, `infographic`, `flashcard_deck`, `answer_key`, `roadmap`). Replace this with a real LLM call that writes the section's prose from the same structured inputs already available: `outline.title`, `outline.job`, `outline.objective`, `outline.gagne_event`, `fact` (from `_verified_fact(research_bundle)`), plus `strategy_fill`/`methodology_components` context.

Keep everything else in `_fill_section` unchanged: `strategy_fill`, `methodology_components`, the `answer_key`/`flashcard_deck` special-casing, and `_forced_failure`'s regen-placeholder path (used by tests/scoped-regeneration — do not remove).

## Acceptance criteria

- [ ] Section `content`/`components` paragraph text is LLM-generated per section (not per-artifact in bulk, unless batching a full artifact in one call is proven equivalent quality at acceptable cost — decide based on `MaxTokensConfig.content_creator` budget).
- [ ] LLM call goes through `LLMClient` (via `AgentRuntime`, consistent with `researcher`/`planner`), respects `MODELS.content_creator` tiering.
- [ ] `_forced_failure` / `regen_placeholder` path is preserved for scoped-regeneration tests.
- [ ] `validate_no_cdn`/`validate_no_pii` guards still run against LLM-generated content (they already do, since they operate on the assembled `artifacts` list — verify no regression).
- [ ] Cost/latency of generating a full pack (up to 9 artifact types × several sections) is measured and logged; if unacceptable, consider batching sections per artifact into one LLM call instead of one call per section.
- [ ] `LIC-01` (reviewer wired to AdaptiveJudge) is live before this ships to production, so LLM-generated content variance is caught by a real judge.

## Blocked by

`LIC-01` (reviewer quality gate) should land first — see that issue's rationale.
