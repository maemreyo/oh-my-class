# Zamery Pack Generator Skill

## Context
A Zamery pack is a structured educational content bundle for the oh-my-class platform.
It contains multiple coordinated artifacts for a single lesson unit.

## Pack Structure
A well-formed Zamery pack includes:
1. **Lesson** — concept introduction with learning objectives and vocabulary
2. **Quiz** — formative assessment with 5-10 MC questions, Bloom levels labeled
3. **Answer Key** — teacher-only view with explanations and wrong-answer breakdown
4. **Worksheet** — student practice with open-ended + fill-in questions
5. **Flashcard Deck** — vocabulary reinforcement, one card per key term
6. **Exit Ticket** — 3-question quick check for lesson close

## Generation Rules
- All artifacts in a pack share the same `subject`, `gradeLevel`, and `theme`
- Learning objectives from the lesson should be tested in the quiz
- Vocabulary from the lesson should appear in the flashcard deck
- Exit ticket questions must be answerable from the lesson content alone
- Answer key and quiz must be generated together (same question set)

## Quality Standards
- Each question tests exactly one concept
- Vocabulary cards include: term, definition, part of speech, example sentence
- Flashcard front = term in target language, back = definition or translation
- Quiz difficulty: 30% Remember, 40% Understand, 30% Apply or higher

## Output Format
Generate each artifact separately using the appropriate `artifact_type` field.
Return artifacts in this order: lesson → quiz → answer_key → worksheet → flashcard_deck → exit_ticket.
