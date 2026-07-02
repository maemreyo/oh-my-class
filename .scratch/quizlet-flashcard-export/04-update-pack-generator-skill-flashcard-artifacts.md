---
title: "Update pack-generator skill to produce flashcard_deck artifacts"
status: completed
labels: [agent-prompt, flashcard-export]
created: 2026-07-02
completed: 2026-07-02
adr: 024
---

## What to build

Update the `pack-generator` skill (`skills/pack-generator/SKILL.md`) to instruct the Content Creator Agent to generate `flashcard_deck` artifacts when the lesson topic involves vocabulary, terminology, definitions, or memorization-heavy content.

Currently, the Content Creator Agent produces artifacts of types: `lesson`, `worksheet`, `quiz`, `drill`, `recap`, `infographic`. It does not produce `flashcard_deck` artifacts because the prompt does not mention this capability.

The skill should:
1. Add `flashcard_deck` to the list of artifact types the agent can produce
2. Define when to generate flashcards (vocabulary topics, key term definitions, memorization-heavy content)
3. Specify the output contract: `FlashcardDeckData {title, subject, gradeLevel, cards[{id, front, back, hint?}]}`
4. Instruct the agent to produce 10-30 cards per deck, covering key terms from the lesson
5. Ensure cards are age-appropriate (reading level, complexity) for the target grade

Key file: `skills/pack-generator/SKILL.md`

## Acceptance criteria

- [x] `pack-generator` skill lists `flashcard_deck` as a supported artifact type
- [x] Skill includes guidance on when to generate flashcards (vocabulary/terminology topics)
- [x] Skill specifies the `FlashcardDeckData` output contract
- [x] Skill specifies card count guidance (10-30 per deck)
- [x] Content Creator Agent can produce `flashcard_deck` artifacts when instructed
- [x] Generated flashcard decks pass Pydantic validation against the `FlashcardDeckData` model
- [x] Existing artifact type generation (lesson, quiz, etc.) is unchanged

## Blocked by

- Issue #01 (flashcard_deck must be a valid artifact_type first)
