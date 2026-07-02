# Pack Generator Skill

## Purpose
Generate structured JSON content for each artifact type, rendered via Eta templates into standalone HTML.

## Triggers
- "generate worksheet"
- "create quiz"
- "make a teaching pack"
- "generate HTML artifacts"

## Workflow
1. Receive ArtifactContent JSON from content creator agent
2. Select appropriate Eta template based on artifact_type
3. Inject theme CSS (from branding/theme_{name}.css)
4. Render via Eta template engine
5. Sanitize HTML (DOMPurify)
6. Validate no external assets (INVARIANT-04)
7. Output: standalone HTML file

## Supported artifact types

| artifact_type   | Template                       | When to generate |
|----------------|--------------------------------|-----------------|
| lesson         | pages/lesson.html              | Always |
| worksheet      | pages/worksheet.html           | Practice exercises |
| quiz           | pages/quiz.html                | Assessment items (MCQ/open) |
| drill          | pages/drill.html               | Repetition practice |
| recap          | pages/recap.html               | End-of-unit review |
| infographic    | pages/infographic.html         | Visual summary |
| flashcard_deck | pages/flashcard_deck.html      | **Vocabulary, terminology, key-term memorization** |

### flashcard_deck — when and how

Generate a `flashcard_deck` artifact when the topic involves vocabulary, terminology,
definitions, or memorization-heavy content (e.g. language learning, science glossaries,
historical events, math formulas).

Output contract (`FlashcardDeckData`):
```json
{
  "artifact_type": "flashcard_deck",
  "title": "Vocabulary: <topic>",
  "sections": [
    {
      "heading": "Core Vocabulary",
      "cards": [
        { "id": "1", "front": "<term>", "back": "<definition>", "hint": "<optional>" }
      ]
    }
  ],
  "metadata": { "subject": "<subject>", "gradeLevel": "<grade>" }
}
```

Card count guidance: **10–30 cards per deck**. Each card must have non-empty `front` and `back`.
Cards are stored in `sections[].cards` (not a top-level field) to stay valid against the
`ArtifactContent` Pydantic schema. The export pipeline reads cards from `sections[].cards`
automatically when building Quizlet TSV or Anki APKG files.

## Constraints
- All CSS inlined — no `<link rel="stylesheet">`
- System font stack only (zero weight)
- Images: inline SVG preferred; small bitmaps as base64 data URIs
- JS: minimal, inline, vanilla; no frameworks; no `eval()`
- Answer keys MUST be in `teacher_only` sections (INVARIANT-05)
- Brand string "oh-my-class" must appear in output (Layer 3 check)
- No CDN references anywhere in output
