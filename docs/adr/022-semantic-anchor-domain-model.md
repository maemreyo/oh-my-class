# ADR-022: Semantic Anchor Domain Model and Projections

## Status

**Decided** (2026-07-01) — The Neo Tư Duy / Semantic Anchoring method will be represented as typed domain contracts and RCM components with separate teacher/student projections, not as raw HTML templates or unstructured prompt output.

## Context

The target pedagogy teaches confusing vocabulary through a memorable semantic anchor rather than flat translation. A cluster such as `travel / journey / trip / voyage / excursion` should become a coherent contrastive map:

```text
Voyage → Hoành tráng / dài ngày → Explore → tàu thủy lớn / phi thuyền
Journey → Gian khổ / đường dài → Path → nhiều stop points
Trip → Nhanh gọn / ngắn ngày → Purpose → return
```

The provided HTML template (`docs/templates/neo-tu-duy-template.html`) shows the desired visual direction: ticket-style cards, impression badges, teaching scripts, semantic chains, and a compact summary table. However, production support cannot be a pasted HTML template. The system must validate the pedagogy, produce student-safe and teacher-rich projections, generate practice, support review/editing, and export standalone files.

The template is a **design reference only**, not a shippable artifact: it loads webfonts via external `<link>` tags. Generated projections must instead satisfy the standalone-HTML invariant (INVARIANT-04, no external URLs) by inlining or self-hosting fonts — implementers must not copy the template's `<link rel="stylesheet" href="https://fonts.googleapis.com/...">` into produced output.

Existing components partially overlap with the method: `vocab_cluster`, `contrastive_pairs`, `concept_map`, `active_recall`, and `inverse_thinking`. They do not fully capture impression keywords, bilingual anchor chains, source-informed distinction notes, teacher scripts, or per-cluster practice.

## Decision

### 1. Introduce `SemanticAnchorCluster` as the core RCM component

`SemanticAnchorCluster` is the typed representation of one confusing-word cluster. It is a Rapid Concept Mapping component that captures the relation between terms, not just a list of word cards.

The cluster includes:

- cluster id, title, title confidence, and raw input span;
- terms and normalized display labels;
- semantic anchor cards;
- contrast / boundary notes between terms;
- summary rows;
- review status and warnings;
- teacher-facing source and nuance notes.

The semantic anchor card uses bilingual structured fields rather than one free-form chain string:

```text
word
impression_vi
core_trigger_en
visual_cue_vi
semantic_chain[]
example_en
contrast_note_vi
student_explanation_vi
teacher_script_vi
edge_cases
source_notes
```

The “visual cue” is a mental image encoded as text and optional predefined icon/motif. The system does not generate or manage image assets for this feature.

### 2. Keep `PracticeSet` separate from teaching content

`PracticeSet` is a separate contract produced from a `SemanticAnchorCluster`. It is not nested inside the RCM component and is not an `ArtifactType`.

The first semantic-anchor practice profile includes four exercise intents:

1. core trigger recall;
2. context discrimination;
3. boundary explanation;
4. reverse retrieval from trigger/cue to word.

This separation preserves answer-key boundaries, allows practice regeneration without changing teaching content, and makes GIFT/H5P export a practice concern rather than a visual-template concern.

### 3. Render separate teacher and student projections

Every cluster can produce separate standalone files:

```text
teaching.teacher.html
teaching.student.html
practice.teacher.html
practice.student.html
```

Teacher teaching projection is a superset: it includes the student view plus teaching scripts, source notes, edge cases, review flags, and suggested delivery. Student teaching projection excludes teacher-only notes.

Teacher practice projection includes answers and rationales. Student practice projection excludes answer keys and teacher rationale.

Separate files are required because hidden teacher-only DOM inside a student file is still leakage.

### 4. Use structured field editing, not HTML editing

Teacher review edits the contract fields, not the rendered HTML. Editable fields include title, impression, core trigger, visual cue, semantic chain entries, examples, contrast notes, teaching script, source notes, and practice items.

After edits, the system validates the contract and re-renders projections. This keeps standalone HTML, leakage rules, and export behavior deterministic.

### 5. Store lexical truth and teaching style separately

The domain separates shared lexical knowledge from teacher delivery style:

| Scope | Owns |
|---|---|
| Shared/global | source-grounded distinctions, edge cases, uncertainty flags |
| Teacher/tenant | preferred tone, anchor intensity, example style, corrections |
| Class/run | grade, CEFR/exam target, topic context, current objective |

Teacher corrections are saved per teacher/tenant first. Shared lexical knowledge is updated only after review. This avoids turning one teacher’s style or correction into global truth.

### 6. Use source-informed, LLM-adapted examples

Dictionary and reference sources constrain usage. The LLM adapts examples for the audience and style profile. Quality gates check that examples remain natural, grade-appropriate, and faithful to the source-grounded distinction.

### 7. Quality returns `passed`, `needs_review`, or `failed`

Semantic anchoring quality is not binary. It evaluates:

- lexical correctness;
- semantic anchor quality;
- pedagogical usability;
- teacher/student projection safety;
- standalone HTML invariants.

`needs_review` is used when content is probably useful but source confidence, nuance, or teacher suitability requires review.

## Consequences

- The feature can render the provided ticket-card visual language while keeping the semantic method contract-first.
- Practice generation, answer keys, and LMS exports are decoupled from the teaching HTML.
- Teacher review can improve future outputs through structured corrections without corrupting rendered files.
- Student output remains safe because teacher-only content and answers are never present in student files.
- The model is reusable beyond travel/fare examples and can later support other language-learning contrastive clusters.

## Alternatives Considered

| Option | Pros | Cons |
|---|---|---|
| Store the semantic chain as one display string | Simple rendering | Hard to validate, edit, translate, or reuse |
| Extend `VocabItem` only | Minimal contract change | Does not model cluster-level contrasts, summary rows, or projections |
| Put practice inside `SemanticAnchorCluster` | One object per cluster | Blurs teaching and assessment; answer-key leakage risk |
| Render one combined teacher/student file | Convenient | Violates student-safe projection discipline |
| Allow freeform HTML edits | Flexible for power users | Breaks validation, re-rendering, standalone guarantees, and leakage checks |
| Make corrections global immediately | Fast collective learning | Conflates teacher style with lexical truth and risks spreading mistakes |
