# Inverse Thinking Support Report — Present Tenses

## Question
Can the current oh-my-class Teaching Pack system support a lesson plan built around inverse thinking for `Present Tenses`?

## Short answer
Yes, for lesson planning. The existing `LessonPlan` contract supports this method through:

- `learning_objectives`: can target understanding, application, analysis, and creation.
- `learning_plan`: flexible `dict[str, Any]`, so each Gagné phase can carry inverse-thinking scenarios, wrong-answer consequences, roleplay scripts, student note systems, and homework video protocols.
- `assessment_checkpoints`: can encode oral reasoning, contrastive quizzes, exit tickets, and video homework.
- `methodology`: explicitly supports methodology metadata.

## Supported methodology tags used
The contract currently allows these tags:

- `concept_map`
- `contrastive_pairs`
- `film_based`
- `shy_student_1on1`
- `active_recall`
- `why_wrong_reasoning`
- `timed_quiz`
- `roleplay_script`

For this lesson plan, inverse thinking maps cleanly to:

- `contrastive_pairs`: compare correct tense against rival tense.
- `why_wrong_reasoning`: explain what meaning breaks if students choose the wrong tense.
- `active_recall`: students rebuild tense forms and rules from memory.
- `roleplay_script`: teacher uses conflict/drama scenarios to expose context and emotion.

## What works well
The system can represent the teacher's desired pedagogy without code changes:

1. Start from the wrong tense and ask what goes wrong.
2. Use absurd consequences to reveal the tense's communicative purpose.
3. Use context and immediate emotion as the core of Present Continuous.
4. Use bridge/result/process metaphors for Perfect Simple vs Perfect Continuous.
5. Use a four-column student note table instead of textbook-style paragraphs.
6. Assign video explanations for the hardest item in each exercise group.

## Current limitation
The `methodology.tags` literal does not contain an explicit `inverse_thinking` tag. That is not a blocker because the method is expressible via existing tags, especially `why_wrong_reasoning` and `contrastive_pairs`.

If this pedagogy becomes a first-class product mode, add a new allowed methodology tag:

```python
"inverse_thinking"
```

That would make filtering, analytics, prompt selection, and UI labeling cleaner.

## Generated artifact
Lesson plan JSON:

- `.scratch/teaching-pack-present-tenses/present-tenses-inverse-thinking.lesson-plan.json`

## Recommendation
Use the generated lesson plan as the planner artifact for this topic. If generating a full teaching pack later, ask the content creator to preserve these required elements:

- inverse-thinking trap scenarios,
- wrong-answer consequence explanation,
- four-column thinking table,
- one-minute video explanation homework,
- contrastive pairs for every tense and stative-verb trap.
