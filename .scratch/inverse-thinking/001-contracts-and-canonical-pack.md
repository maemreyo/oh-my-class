---
title: Inverse Thinking contracts and canonical pack
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Add the typed contract foundation for inverse thinking so the system can represent disaster-first pedagogy as structured data instead of parsing free-form prose or rendered HTML.

This slice should introduce the canonical pack and case contracts, preserve compatibility with existing methodology tags, and provide subject-agnostic fixtures. It should not implement renderer styling or pipeline generation yet; later slices will consume these contracts.

Decision-rich shape from the ADRs:

```python
InverseThinkingPack:
    methodology = "inverse_thinking"
    creative_frame
    cases
    summary_table
    student_challenges
    teacher_only
    projection_hints

InverseThinkingCase:
    id
    title
    alias
    target_concept
    foil
    disaster
    key_clues
    safe_zone
    filing_note
    student_task
    teacher_only
```

## Acceptance criteria

- [ ] Pydantic v2 contracts exist in the canonical contract layer for inverse-thinking pack, case, creative-frame selection, summary row, student challenge, and teacher-only rationale.
- [ ] `inverse_thinking` is represented as a supported methodology tag without breaking existing `methodology_tags` behavior.
- [ ] A structured methodology payload path exists for inverse-thinking data instead of overloading generic component fields.
- [ ] Generated TypeScript/Zod schema output includes inverse-thinking types for renderer and web usage.
- [ ] Fixtures cover at least one English grammar case, one math misconception case, and one science misconception case.
- [ ] Contract tests reject missing disaster, empty clues, missing safe zone, missing filing note, and answer-key data in student-facing fields.
- [ ] Contract tests verify valid fixtures parse cleanly and are serializable for downstream projection/rendering.

## Detailed test suite

- [ ] `common/contracts/tests/test_inverse_thinking_contracts.py`: Given valid English, math, and science fixtures, when parsed as `InverseThinkingPack`, then all fixtures validate and round-trip via `model_dump()`.
- [ ] `common/contracts/tests/test_inverse_thinking_contracts.py`: Given a case missing `disaster`, `key_clues`, `safe_zone`, or `filing_note`, when parsed, then Pydantic raises a field-specific `ValidationError`.
- [ ] `common/contracts/tests/test_inverse_thinking_contracts.py`: Given student-facing fields containing answer-key/rationale markers, when parsed, then validation rejects them and requires `teacher_only` separation.
- [ ] `common/contracts/tests/test_lesson_plan_methodology.py`: Given existing `methodology_tags`, when `inverse_thinking` is added, then existing tags still parse without migration breakage.
- [ ] `common/schemas` parity test: Given generated TypeScript/Zod schemas, when compared against Pydantic JSON schema, then inverse-thinking field names and required/optional status match.
- [ ] Run `make check-schemas` and `uv run pytest common/contracts/tests -v`.

## Blocked by

None - can start immediately
