# ADR-049: Slide Deck Artifact Generation Remains Deterministic-by-Design (Other Artifact Types Flip to Real LLM)

## Status

**Accepted** (2026-07-08) — produced from the `.scratch/design-reflection-2026-07-08.md` grill session.

## Context

`packages/agents/sub_agents/content_creator/hierarchical.py` dispatches every artifact type (`lesson`, `worksheet`, `quiz`, `drill`, `recap`, `infographic`, `flashcard_deck`, `answer_key`, `roadmap`, `slide_deck`) through `build_hierarchical_artifacts`. For every type except `slide_deck`, section content is produced by `_fill_section` (`hierarchical.py:123-163`) as `f"{outline.job}: {fact}"` — literal string concatenation of a static job description and a research-bundle fact, e.g. `"teach verified content: <fact>"`. This is the actual text a teacher would receive; it is not usable classroom material as-is.

`slide_deck` is dispatched separately, to `build_slide_deck_artifact` → `SlideDeckEngine` (`packages/agents/slide_deck_engine.py`), which self-labels its output `"generation_mode": "slide_deck_engine_deterministic"` and produces a `scorecard`/`trace` alongside the deck. This is a purpose-built, actively-developed subsystem (ADR-040 through ADR-047 already cover its phased architecture, layout/block registry, offline presentation, and bilingual translation), engineered independently of the generic hierarchical dispatcher.

Per ADR-047 (`Consequences`, and Decision #1), `SlideDeckEngine`'s `ContentMaterializer` phase is already the agreed seam for adding a real, schema-bound LLM call to slide content specifically — that decision was made and scoped in ADR-047 and is not reopened here.

## Decision

1. **Every non-`slide_deck` artifact type's section content moves to a real LLM call.** `_fill_section`'s string-concat placeholder is replaced with an LLM-generated paragraph, grounded in the same `outline.job`, `fact`, `objective`, and `gagne_event` inputs it already receives — the structural scaffolding (`strategy_fill`, `methodology_components`, per-type section outlines) is unchanged; only the prose-generation step changes. See `.scratch/llm-integration-completion/LIC-02-content-creator-real-llm.md`.
2. **`slide_deck` is explicitly out of scope for this decision.** It continues to route through `SlideDeckEngine` unchanged by this ADR; its path to real content generation is ADR-047's `ContentMaterializer` LLM step, tracked under its own issue set (`.scratch/slide-deck-editor/issues/`), not under `content_creator`'s generic flip.
3. **The two paths are allowed to diverge permanently.** `slide_deck`'s `"generation_mode": "slide_deck_engine_deterministic"` label should not be read as an unfinished placeholder matching the other nine artifact types — it names a different, independently-designed subsystem.

## Consequences

- A future reader auditing "which artifact types call an LLM" gets a clean, self-consistent answer per type instead of one undifferentiated verdict for `content_creator`.
- `slide_deck`'s roadmap (real content via ADR-047) proceeds independently of this ADR's rollout — the two should not be sequenced against each other.
- If `slide_deck` is ever folded back into the generic hierarchical dispatcher (removing `SlideDeckEngine` as a separate subsystem), that reversal should itself be a new ADR, not a quiet merge.
