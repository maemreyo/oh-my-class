# oh-my-class Context

## Glossary

### slide_deck

A core teaching-pack artifact representing a classroom presentation deck. A `slide_deck` is generated, reviewed, quality-gated, regenerated, and exported through the same artifact lifecycle as lessons, worksheets, quizzes, drills, recaps, flashcards, roadmaps, and answer keys.

### SlideDeckData

The canonical typed domain model for a slide deck. It describes deck metadata, slides, blocks, interactions, teacher-only facilitation data, source references, accessibility metadata, media policy metadata, and surface/export readiness. It is the source shape used by generation, rendering, quality gates, and export adapters.

### SlideDeckEngine

The deterministic orchestration module that produces `SlideDeckData` behind the Content Creator seam. It may call LLM providers through schema-bound ports, but layout selection, interaction selection, density policy, accessibility validation, healing, source references, and teacher-only safety are enforced by typed engine phases and registries.

### Slide surface

A projection of one `SlideDeckData` for a specific audience or use mode. The approved surfaces are student presentation HTML, teacher guide/preview HTML, and print HTML.

### Slide registry

A typed extension seam for slide layouts, slide blocks, or slide interactions. Registry entries declare their schema, supported surfaces, density budget, accessibility requirements, print behavior, teacher-only behavior, and fallback behavior.

### Teacher-only slide data

Facilitation content intended for teachers only: speaker notes, pacing cues, misconceptions, explanations, answer guidance, and rubrics. Teacher-only slide data must not appear in student-facing DOM, hidden JSON, data attributes, or export surfaces.

### DeckSourceContext

The normalized source context used to generate a slide deck. It is assembled from lesson blueprint, research brief, teacher constraints, and approved dependency artifacts. Deck pages and blocks may reference this context through source references.
