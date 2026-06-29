# ADR-014: Inverse Thinking Methodology Architecture

## Status

**Decided** (2026-06-30) — `inverse_thinking` is a production teaching methodology, not a one-off HTML template or visual style.

## Context

The project needs to support an inverse-thinking / disaster-first teaching approach inspired by the provided present-tense case-file templates, including `docs/templates/inverse-thinking-template.html`. The examples show a strong instructional pattern: students first see a plausible wrong idea and its concrete consequence, then infer the clue, boundary, and rule from the failure.

Existing oh-my-class concepts already overlap with this approach: `contrastive_pairs`, `why_wrong_reasoning`, concept maps, diagnostic misconceptions, and answer-key separation. However, inverse thinking needs its own contract so the system can validate that the method is actually used instead of merely styling a standard lesson as a case file.

## Decision

`inverse_thinking` is a global methodology with English grammar/vocabulary as the first production preset.

Every inverse-thinking output must satisfy a semantic four-step contract:

1. **Disaster / scene first** — present a plausible wrong choice, foil, or misconception before the rule.
2. **Key clues** — identify the observable evidence that makes the correct choice necessary.
3. **Safe zone / boundary** — show when the foil or rival idea becomes valid, so students learn the boundary instead of memorizing a slogan.
4. **Filing note / synthesis** — compress the lesson into a memorable class-owned conclusion or summary row.

The labels and creative metaphor may vary by subject and age. English may use "scene", "clue", "safe zone", and "case file" language. Math may use "dangerous shortcut", "decisive data", "valid range", and "conclusion". Science may use "false model", "observed evidence", "boundary condition", and "lab note".

The first production preset is English grammar/vocabulary because the available template references are concrete and high-quality. The underlying schemas, validators, projection layer, and tests must remain subject-agnostic.

## Consequences

- The method is selected during Blueprint / LessonPlan, not only during rendering.
- Planner, Researcher, Content Creator, Quality Gates, Renderer, and Teacher UI all receive explicit inverse-thinking data.
- A case-file visual treatment is allowed, but the semantic method is not coupled to detective styling.
- Quality gates can fail outputs that are rule-first, lack a concrete disaster, omit clues, or omit a boundary contrast.
- English-specific conveniences live in presets/adapters, not in the top-level contract.

## Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| Patch the existing HTML template directly | Fast demo | Not scalable, not testable, bypasses contracts and gates |
| Treat inverse thinking as only a renderer theme | Easy to style | Does not guarantee disaster-first pedagogy |
| Make it English-only | Simple initial scope | Locks the architecture away from math/science/history use cases |
| Global methodology with English first preset | Production-ready, reusable, testable | Requires contracts, projections, gates, and UI integration |
