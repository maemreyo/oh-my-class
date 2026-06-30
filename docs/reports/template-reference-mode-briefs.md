# Template reference mode design briefs

These briefs adapt the raw `docs/templates/` references into offline-safe, tokenized mode contracts. They are design contracts, not copied HTML. Every mode uses system fonts through theme tokens, inline CSS, no remote assets, no external scripts, no CDN dependencies, and standalone print styles.

## Key Reference

- Source template: `docs/templates/key-template.html`
- Reusable primitives: answer-key shell, grouped question card, wrong-reason feedback panel, sidebar range navigation, score/category badges.
- Teacher controls: answer visibility scope, grouped range labels, misconception emphasis, print density.
- Renderer surfaces: `answer_key` page, `question_card`, `wrong_reason_feedback`, grouped sidebar navigation.
- Quality expectations: answer keys stay teacher-only, every student-facing artifact excludes scrapeable answers, grouped explanations include question anchors.
- Offline adaptation: replace remote font assumptions with `--font-heading`, `--font-body`, `--font-mono`; replace logo dots with CSS token shapes; keep all styles inline.
- Follow-up: implementation-ready through existing answer-key renderer; no new methodology issue needed.

## Path Reference

- Source template: `docs/templates/path-template.html`
- Reusable primitives: learning roadmap shell, phase timeline, goal/stat cards, stage navigation, checkpoint checklist.
- Teacher controls: target score/level, phase count, checkpoint cadence, remediation emphasis.
- Renderer surfaces: `roadmap` page, phase timeline component, stat grid, progress checklist.
- Quality expectations: each phase has a goal, activity, checkpoint, and export-safe print state; no external tracking widgets.
- Offline adaptation: replace paper texture and imported fonts with theme background tokens and CSS-only patterns; keep progress indicators text-readable.
- Follow-up: implementation-ready through roadmap renderer polish; no new methodology issue needed.

## Learning Vocab Reference

- Source template: `docs/templates/learning-vocab-template.html`
- Reusable primitives: vocab cluster card, film hunt sheet, concept map triads, quick-pair contrast table, homework list.
- Teacher controls: vocabulary set, contrast pair emphasis, film/video optionality, homework density.
- Renderer surfaces: `lesson` page, `vocab_cluster`, `contrastive_pairs`, `film_clip_activity`, `hw_list`.
- Quality expectations: vocab items include definitions or examples, media references remain text-only, contrast pairs avoid teacher rationale leakage.
- Offline adaptation: replace decorative icons with CSS/text labels; replace imported font stack with theme tokens; avoid remote thumbnails or embeds.
- Follow-up: implementation-ready through existing methodology component polish; no new methodology issue needed.

## Learning via Video Reference

- Source template: `docs/templates/learning-via-video-template.html`
- Reusable primitives: ticket header, station timeline, before/during/after viewing cards, transcript clue chips, self-check station.
- Teacher controls: clip context, station sequence, viewing pass count, transcript clue list, reflection prompt.
- Renderer surfaces: `film_clip_activity`, station timeline, reflection note, text-only video reference.
- Quality expectations: no iframe/video embed in standalone output, every video task has before/during/after prompts, transcript clues are text-readable.
- Offline adaptation: replace external fonts and video links with theme tokens and teacher-provided text references; all station colors map to semantic/category tokens.
- Follow-up: implementation-ready through film-based renderer polish; no new methodology issue needed.
