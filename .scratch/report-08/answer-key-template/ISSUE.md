---
title: "Answer Key Template: question_card + sidebar + hero + answer_key.eta"
status: ready
labels: [renderer, templates, answer-key]
created: 2026-06-24
priority: p0
report: "08"
---

## What to build

Implement the `answer_key` artifact type — the highest-value deliverable. Produces standalone HTML matching `docs/templates/key-template.html` (1067-line reference). Architecture: `answer_key.eta` page → `dispatcher.eta` → component partials.

**Key components:** `question_card.eta` (most complex), `question_list.eta`, `sidebar.eta`, `hero.eta`, shared utility components.

## File Structure

```
packages/renderer/templates/
├── pages/
│   └── answer_key.eta                # Full answer key page
└── components/
    ├── question_card.eta             # Core: options, explain, wrongReasons, essence, tip
    ├── question_list.eta             # Section wrapper iterating question_cards
    ├── sidebar.eta                   # Nav, jump grid, hide/reveal toggle, legend
    ├── hero.eta                      # Title, lede, stamp, stat grid
    ├── callout.eta                   # Note/warning/tip/alert variants
    ├── note_callout.eta              # Gold-bordered note boxes
    ├── alert.eta                     # Critical gap alerts
    ├── table.eta                     # Data tables (.dtable styling)
    ├── heading.eta                   # h1-h4 with optional id
    └── paragraph.eta                 # Simple paragraph
```

## CSS Design System (inline in answer_key.eta)

From `key-template.html` — reference implementation. Group colors `--c-a` through `--c-e`, card shadows, sidebar layout. MUST use system font stack (not Google Fonts):
- Heading: `Georgia, 'Times New Roman', serif`
- Body: `system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif`
- Mono: `'SF Mono', 'Fira Code', 'Cascadia Code', monospace`

## Component Specs

### `question_card.eta`
Renders one MCQ question with: number badge, question text, 4-option grid (correct highlighted), explain panel, wrongReasons breakdown (optional), essence ("Bản chất"), tip ("Mẹo làm bài").

Color group applied via `g-<%= it.group %>` CSS class.

### `sidebar.eta`
Sticky sidebar (268px): section navigation list, jump-to-question grid (5×N dots colored by group), hide/reveal toggle, legend (group color → label mapping).

### `hero.eta`
Title, subtitle lede, stamp badge ("Đáp án chi tiết"), optional stat grid (4 cards: total questions, sections, etc.).

### `pages/answer_key.eta`
Layout: `<div class="shell">` with sidebar + main. Main loops through sections → per-section header → `dispatcher.eta` for each component.

```eta
<%~ include("../base", {
  title: it.title,
  lang: it.accessibility?.language || 'vi',
  themeCss: it.themeCss,
  body: bodyContent
}) %>
```

## Fixture Data

Create `packages/renderer/fixtures/answer_key_sample.json` — minimal fixture with 3 questions across 2 sections, all fields populated (explain, wrongReasons, essence, tip). Used in tests.

## Tests

```
packages/renderer/src/__tests__/
├── answer_key.test.ts        # renderArtifact({artifact_type: "answer_key", ...}) → HTML
└── components/
    ├── question_card.test.ts  # all fields, missing optional fields, group colors
    ├── sidebar.test.ts
    └── hero.test.ts
```

Test: output contains question text, correct answer has `.correct` class, explain appears, essence/tip optional fields omitted when absent, HTML is valid (DOCTYPE present, no external assets), sanitizer passes.

## Acceptance Criteria

- [ ] `renderArtifact({artifact_type: "answer_key", ...})` produces valid standalone HTML
- [ ] `question_card.eta` renders all fields: explain, wrongReasons, essence, tip (optional fields omitted when null)
- [ ] `sidebar.eta` generates jump grid with correct group colors
- [ ] System font stack used everywhere (no Google Fonts)
- [ ] No external assets (`src=http://`, `href=http://`) in output
- [ ] `<!DOCTYPE html>` present in output
- [ ] Fixture data renders without error

## Dependencies

- Blocked by: `template-engine` (dispatcher.eta must exist), `component-schema` (QuestionCard model)
- Priority: p0

## Research Findings

**Source**: Report 08 Section 12 — Answer Key Wrong Reasoning

### DiVERT (arXiv 2406.19356)
Variational model: generates error description → generates distractor from that error
7B params outperforms GPT-4o on distractor generation quality
Human evaluation: error labels "comparable in quality to human-authored ones"

### Eedi Misconception Taxonomy
2587 misconception categories in K-12 math
1st place Kaggle solution: synthetic data (10.6k) + Claude reasoning traces + 3-model ensemble

### Distractor Assessment Framework (DAF)
3 automatic quality metrics: Incorrectness (binary MRC), Plausibility (system confidence), Diversity (BERT Equivalence Metric)

### Recommended LLM Prompt Pattern
Two-stage: First identify misconception → Then generate distractor that embodies it
Zero-shot CoT template for distractor + feedback generation
5 distractor strategies: Overcorrection, Outdated Practice, Wrong Context, Incomplete Solution, Reasonable Misunderstanding

### VN Platform Gap
Sitori: manual explanations, no per-distractor rationale
MegaEdu.AI: error patterns but no per-option breakdown
→ oh-my-class can differentiate with full wrongReasons + essence + tip

### Key References
- DiVERT: https://arxiv.org/html/2406.19356v1
- UMass ML4Ed: https://github.com/umass-ml4ed/prompt_distractor_generation_naacl
- Eedi: https://www.eedi.com/news/from-wrong-answers-to-real-insights
