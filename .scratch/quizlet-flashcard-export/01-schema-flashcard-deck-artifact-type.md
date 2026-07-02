---
title: "Add flashcard_deck to ArtifactContent artifact_type enum"
status: completed
labels: [schema, flashcard-export]
created: 2026-07-02
completed: 2026-07-02
adr: 024
---

## What to build

Add `flashcard_deck` as a valid value in the `ArtifactContent.artifact_type` Literal enum in `common/contracts/artifact.py`. This allows the Content Creator Agent to officially produce flashcard deck artifacts.

The existing `FlashcardDeckData` TypeScript contract (`packages/renderer/src/contracts/flashcard_deck.ts`) already defines the schema:
- `Flashcard {id, front, back, hint?}`
- `FlashcardDeckData {title, subject, gradeLevel, cards[], theme?, lang?}`

The Python Pydantic model in `common/contracts/artifact.py` needs a corresponding `FlashcardDeckData` model and `flashcard_deck` added to the `artifact_type` Literal.

## Acceptance criteria

- [x] `artifact_type` Literal in `common/contracts/artifact.py` includes `"flashcard_deck"`
- [x] Pydantic model `FlashcardDeckData` exists in `common/contracts/artifact.py` with fields: `title`, `subject`, `gradeLevel`, `cards` (list of `Flashcard`), optional `theme`, optional `lang`
- [x] Pydantic model `Flashcard` exists with fields: `id` (str), `front` (str), `back` (str), optional `hint` (str)
- [x] Auto-generated Zod schema at `common/schemas/src/generated/artifact.ts` includes the new types
- [x] Existing tests pass (no regressions)
- [x] `ArtifactContent` can be constructed with `artifact_type="flashcard_deck"` and validated by Pydantic

## Blocked by

None - can start immediately.
