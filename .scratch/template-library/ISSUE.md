---
title: "Template Library: S1 — All 10 Pages + 20 Components, Fully Implemented"
status: ready
labels: [renderer, templates, ui]
created: 2026-06-24
priority: p0
report: "03"
---

## What to build

Implement all page templates and components in `packages/renderer/templates/`. Every template is a real Eta file (not a stub). All templates use `it.` variable access, WCAG 2.1 AA, keyboard navigable, touch-friendly, print-ready, standalone (no CDN).

**Design decision (S1):** No MVP shortcuts — every template fully implemented with proper semantics, accessibility attributes, and the design language from `template.html` (CSS custom properties, system font stack, inline SVG icons).

## File Structure

```
packages/renderer/templates/
├── base.html                        # shell: DOCTYPE, <head>, CSS injection, <slot>
├── pages/
│   ├── lesson.html                  # structured lesson with objectives + sections
│   ├── quiz.html                    # multiple-choice test, hide/reveal answers
│   ├── drill.html                   # practice exercises, progressive difficulty
│   ├── worksheet.html               # printable worksheet, fill-in + open response
│   ├── recap.html                   # summary card, key concepts + vocabulary
│   ├── infographic.html             # visual-first layout, timeline/chart/concept map
│   ├── answer_key.html              # teacher view: all answers + explanations visible
│   ├── flashcard_deck.html          # flip cards, vocabulary + concepts
│   ├── reading_passage.html         # long text + numbered paragraphs + questions
│   └── exit_ticket.html             # 3-question quick check, compact single-page
└── components/
    ├── question_mc.html             # multiple choice, custom radio, WCAG radiogroup
    ├── question_tf.html             # true/false pair
    ├── question_fill.html           # fill-in-the-blank with underline slots
    ├── question_match.html          # drag-or-select matching pairs
    ├── question_order.html          # reorder items
    ├── question_open.html           # open-ended response, lined area + word count
    ├── hint_box.html                # collapsible hint (hidden by default)
    ├── note_callout.html            # always-visible Note/Tip/Warning box
    ├── learning_objective.html      # SWBAT box: "By the end of this lesson..."
    ├── answer_reveal.html           # toggle: hide/show answer + explanation
    ├── vocabulary_card.html         # word + definition + pos + example sentence
    ├── image_figure.html            # figure + caption + attribution (SVG/base64 only)
    ├── math_block.html              # MathML or LaTeX-rendered formula
    ├── timeline.html                # horizontal/vertical timeline
    ├── concept_map.html             # SVG-based concept node graph
    ├── comparison_table.html        # side-by-side comparison grid
    ├── data_chart.html              # inline SVG bar/line chart
    ├── feedback.html                # score + encouragement + next-step message
    ├── progress_bar.html            # animated progress indicator
    └── header.html / footer.html    # branding header + legal footer
```

## Implementation Spec

### `base.html`

```html
<!DOCTYPE html>
<html lang="<%= it.lang ?? 'vi' %>">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title><%= it.title %></title>
  <style>
    /* Theme tokens — injected from ThemeCSSGenerator */
    :root {
      <%- it.themeCSS %>
    }

    /* System font stack — no CDN */
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue',
                   Arial, 'Noto Sans', sans-serif;
      margin: 0;
      background: var(--color-bg, #fafafa);
      color: var(--color-text, #1a1a2e);
      line-height: 1.65;
    }

    /* Print styles */
    @media print {
      .no-print { display: none !important; }
      body { background: white; }
    }
  </style>
</head>
<body class="artifact artifact--<%= it.type ?? 'unknown' %>">
  <%~ await include('../components/header', it) %>
  <main id="main-content">
    <%- it.body %>
  </main>
  <%~ await include('../components/footer', it) %>
</body>
</html>
```

### `pages/quiz.html`

```html
<%
  /* Quiz page: multiple-choice test with answer reveal toggle */
  const isAnswerKey = it.showAnswers ?? false
%>
<%~ await include('../base.html', {
  ...it,
  type: 'quiz',
  body: await eta.renderAsync('_partials/quiz_body', { ...it, isAnswerKey })
}) %>
```

### `pages/answer_key.html`

```html
<%
  /* Teacher view: all answers + explanations always visible.
     Rendered separately from quiz.html — never sent to students. */
%>
<%~ await include('../base.html', {
  ...it,
  type: 'answer_key',
  body: await eta.renderAsync('_partials/quiz_body', { ...it, isAnswerKey: true })
}) %>
```

### `pages/flashcard_deck.html`

```html
<%~ await include('../base.html', {
  ...it,
  type: 'flashcard_deck',
  body: `
    <section class="flashcard-deck" aria-label="Flashcard deck: ${it.title}">
      <div class="deck-progress">
        <span aria-live="polite" id="card-counter">1 / ${it.cards.length}</span>
      </div>
      <div class="deck-container" role="list">
        ${it.cards.map((card, i) => `
          <article class="flashcard ${i === 0 ? 'flashcard--active' : ''}"
                   role="listitem"
                   aria-label="Card ${i + 1}: ${card.term}">
            <button class="flashcard__inner" aria-pressed="false"
                    aria-label="Flip card to see definition">
              <div class="flashcard__front">
                <span class="flashcard__term">${it.eta.escapeXML(card.term)}</span>
                <span class="flashcard__pos">${it.eta.escapeXML(card.partOfSpeech ?? '')}</span>
              </div>
              <div class="flashcard__back" aria-hidden="true">
                <span class="flashcard__definition">${it.eta.escapeXML(card.definition)}</span>
                <span class="flashcard__example">${it.eta.escapeXML(card.example ?? '')}</span>
              </div>
            </button>
          </article>
        `).join('')}
      </div>
      <nav class="deck-nav no-print" aria-label="Card navigation">
        <button id="btn-prev" aria-label="Previous card">←</button>
        <button id="btn-next" aria-label="Next card">→</button>
      </nav>
    </section>
    <script>/* inline JS: flip + prev/next, no framework */</script>
  `
}) %>
```

### `components/question_mc.html`

```html
<%
  /* Multiple choice question. it = MCQuestion + { index, showAnswer } */
  const { id, prompt, options, answer, explain, index, showAnswer } = it
%>
<article class="component-question-mc" id="q-<%= id %>">
  <p class="question-prompt" id="prompt-<%= id %>">
    <span class="question-number" aria-hidden="true"><%= index %>.</span>
    <%- prompt %>
  </p>

  <div class="options-grid" role="radiogroup" aria-labelledby="prompt-<%= id %>">
    <% for (const opt of options) { %>
      <label class="option <%= showAnswer && opt.label === answer ? 'option--correct' : '' %>
                          <%= showAnswer && opt.label !== answer ? 'option--neutral' : '' %>"
             aria-checked="<%= showAnswer && opt.label === answer %>">
        <input type="radio"
               name="q-<%= id %>"
               value="<%= opt.label %>"
               <%= showAnswer ? 'disabled' : '' %>>
        <span class="option-label" aria-hidden="true"><%= opt.label %></span>
        <span class="option-text"><%= opt.text %></span>
        <% if (showAnswer && opt.label === answer) { %>
          <span class="option-check" aria-label="Correct answer">✓</span>
        <% } %>
      </label>
    <% } %>
  </div>

  <% if (showAnswer && explain) { %>
    <div class="question-explanation" role="note">
      <span class="explanation-label">Giải thích:</span>
      <%- explain %>
    </div>
  <% } %>
</article>
```

### `components/learning_objective.html`

```html
<%
  /* SWBAT box: "By the end of this lesson, students will be able to..."
     it = { objectives: string[], gradeLevel?: string } */
%>
<aside class="component-learning-objective" role="note" aria-label="Learning objectives">
  <h2 class="objective-heading">
    <span class="objective-icon" aria-hidden="true">🎯</span>
    Mục tiêu bài học
  </h2>
  <p class="objective-lead">Sau bài học này, học sinh có thể:</p>
  <ul class="objective-list">
    <% for (const obj of it.objectives) { %>
      <li class="objective-item"><%= obj %></li>
    <% } %>
  </ul>
  <% if (it.gradeLevel) { %>
    <p class="objective-grade">Lớp: <strong><%= it.gradeLevel %></strong></p>
  <% } %>
</aside>
```

### `components/answer_reveal.html`

```html
<%
  /* Toggleable answer reveal — teacher or self-study mode.
     it = { answer: string, explain?: string, id: string } */
%>
<div class="component-answer-reveal" data-reveal-id="<%= it.id %>">
  <button class="reveal-btn"
          aria-expanded="false"
          aria-controls="reveal-content-<%= it.id %>"
          onclick="this.setAttribute('aria-expanded',
            this.getAttribute('aria-expanded') === 'true' ? 'false' : 'true');
            document.getElementById('reveal-content-<%= it.id %>').hidden =
              this.getAttribute('aria-expanded') === 'false'">
    Xem đáp án
  </button>
  <div id="reveal-content-<%= it.id %>"
       class="reveal-content"
       hidden
       role="region"
       aria-label="Answer for question <%= it.id %>">
    <span class="reveal-answer"><strong>Đáp án:</strong> <%= it.answer %></span>
    <% if (it.explain) { %>
      <p class="reveal-explain"><%- it.explain %></p>
    <% } %>
  </div>
</div>
```

### `components/note_callout.html`

```html
<%
  /* Always-visible callout box. Different from hint_box (hidden by default).
     it = { type: 'note' | 'tip' | 'warning', title?: string, body: string } */
  const icons = { note: 'ℹ️', tip: '💡', warning: '⚠️' }
  const labels = { note: 'Lưu ý', tip: 'Mẹo', warning: 'Cảnh báo' }
%>
<aside class="component-note-callout component-note-callout--<%= it.type %>"
       role="note"
       aria-label="<%= labels[it.type] %>">
  <span class="callout-icon" aria-hidden="true"><%= icons[it.type] %></span>
  <div class="callout-body">
    <% if (it.title) { %>
      <strong class="callout-title"><%= it.title %></strong>
    <% } else { %>
      <strong class="callout-title"><%= labels[it.type] %></strong>
    <% } %>
    <p class="callout-text"><%- it.body %></p>
  </div>
</aside>
```

### `components/vocabulary_card.html`

```html
<%
  /* Single vocabulary entry. Used in lesson body and flashcard_deck.
     it = { term, definition, partOfSpeech?, example?, id } */
%>
<article class="component-vocabulary-card" id="vocab-<%= it.id %>">
  <header class="vocab-header">
    <span class="vocab-term" lang="<%= it.termLang ?? 'en' %>"><%= it.term %></span>
    <% if (it.partOfSpeech) { %>
      <span class="vocab-pos" aria-label="Part of speech"><%= it.partOfSpeech %></span>
    <% } %>
  </header>
  <p class="vocab-definition"><%= it.definition %></p>
  <% if (it.example) { %>
    <p class="vocab-example">
      <span class="vocab-example-label" aria-hidden="true">Ví dụ:</span>
      <em><%= it.example %></em>
    </p>
  <% } %>
</article>
```

### `components/image_figure.html`

```html
<%
  /* Figure with caption. src must be SVG string or base64 data URI — no CDN.
     it = { src, alt, caption?, attribution? } */
%>
<figure class="component-image-figure">
  <% if (it.src.startsWith('<svg')) { %>
    <%- it.src %>
  <% } else { %>
    <img src="<%= it.src %>"
         alt="<%= it.alt %>"
         loading="lazy"
         decoding="async">
  <% } %>
  <% if (it.caption) { %>
    <figcaption class="figure-caption">
      <%= it.caption %>
      <% if (it.attribution) { %>
        <span class="figure-attribution">— <%= it.attribution %></span>
      <% } %>
    </figcaption>
  <% } %>
</figure>
```

### `pages/exit_ticket.html`

```html
<%
  /* Exit ticket: compact 3-question quick check.
     it = ExitTicketData { title, subject, gradeLevel, questions: (max 3), theme } */
%>
<%~ await include('../base.html', {
  ...it,
  type: 'exit_ticket',
  body: `
    <section class="exit-ticket">
      <header class="exit-ticket-header">
        <h1>${it.title}</h1>
        <div class="exit-ticket-meta">
          <span>${it.gradeLevel}</span> · <span>${it.subject}</span>
        </div>
      </header>
      <ol class="exit-ticket-questions">
        ${it.questions.slice(0, 3).map((q, i) =>
          /* render each question component inline */
          `<li class="exit-ticket-question">${q.prompt}
             <div class="answer-line"></div>
           </li>`
        ).join('')}
      </ol>
      <footer class="exit-ticket-footer no-print">
        <span>Hoàn thành trước khi ra về</span>
      </footer>
    </section>
  `
}) %>
```

## Accessibility Requirements (all templates)

- Every interactive element has `aria-label` or `aria-labelledby`
- Color is never the sole differentiator (icons + text labels used together)
- Keyboard navigable: all buttons/inputs reachable via Tab, activated via Enter/Space
- Minimum touch target 44×44px (WCAG 2.5.5)
- `role="radiogroup"` on question option groups
- `aria-live="polite"` on dynamic counters (flashcard progress, score)
- `hidden` attribute (not `display:none`) used for initially hidden content

## Print Requirements (worksheets, answer_key)

- `@media print` removes `.no-print` elements
- Answer lines use `border-bottom` not `text-decoration`
- Page breaks: `page-break-inside: avoid` on question cards
- Font size minimum 11pt in print mode

## Acceptance Criteria

- [ ] All 10 page templates render valid HTML5 (html-validate passes)
- [ ] All 20 component templates render in isolation with minimal data
- [ ] `base.html` injects `it.themeCSS` into `:root {}`
- [ ] No external URLs in any template (no CDN, no Google Fonts)
- [ ] All interactive components keyboard-navigable
- [ ] `answer_key.html` always shows answers — no hide/reveal toggle
- [ ] `quiz.html` hides answers by default — `answer_reveal` component handles toggle
- [ ] `flashcard_deck.html` flip animation via CSS + minimal inline JS
- [ ] `exit_ticket.html` max 3 questions, compact layout, print-ready
- [ ] All templates pass TypeScript contract types from `contracts/` (T3)

## Dependencies

- Blocked by: `html-template-system` (eta-engine, contracts)
- Blocks: nothing (leaf — renderer uses templates, not the other way)
- Priority: p0
