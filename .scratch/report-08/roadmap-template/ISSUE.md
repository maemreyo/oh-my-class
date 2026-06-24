---
title: "Roadmap Template: 7 New Components + roadmap.eta Page"
status: ready
labels: [renderer, templates, roadmap]
created: 2026-06-24
priority: p1
report: "08"
---

## What to build

Implement the `roadmap` artifact type — 7 new component partials + `roadmap.eta` page. Matches `docs/templates/path-template.html` (846-line reference). Shares design system with answer_key.

**New components not in answer-key:** `stat_grid`, `pattern_grid`, `trait_grid`, `taxonomy_grid`, `phase_timeline`, `flow_step`, plus `roadmap.eta` page with unique sidebar (stats, nav, legend).

## File Structure

```
packages/renderer/templates/
├── pages/
│   └── roadmap.eta                   # Full roadmap page
└── components/
    ├── stat_grid.eta                 # 4-column stat cards (target/now/default variants)
    ├── pattern_grid.eta              # 2-column error pattern cards with ID badges
    ├── trait_grid.eta                # 2-column student personality trait cards
    ├── taxonomy_grid.eta             # 2-column reading comprehension taxonomy
    ├── phase_timeline.eta            # Vertical timeline with dot markers + phase cards
    └── flow_step.eta                 # Lesson flow with time badges
```

## Component Specs

### `phase_timeline.eta`
Most complex: vertical rail with colored dots, phase cards with `when` badge, `goal` text, `blocks` grid (label + items), `output` callout. Phase dot color = `var(--c-<%= phase.group %>)`.

### `stat_grid.eta`
Responsive grid (2-col mobile, 4-col desktop). Each card: label + value, variant styling (`target` → `--green`, `now` → `--gold`, `default` → `--ink`).

### `pattern_grid.eta`
2-column grid. Each card: colored ID badge (`g-<%= pattern.group %>`), title, description text.

### `pages/roadmap.eta`
Sidebar: stats cards (current score, target, duration), nav links to sections, legend. Hero: eyebrow, title, lede, stamp. Main content: sections loop → dispatcher per component.

## Fixture Data

Create `packages/renderer/fixtures/roadmap_sample.json` — fixture with hero, sidebar, 2 sections (one with phase_timeline, one with trait_grid).

## Tests

```
packages/renderer/src/__tests__/
├── roadmap.test.ts               # renderArtifact({artifact_type: "roadmap", ...})
└── components/
    ├── phase_timeline.test.ts    # phases render, group colors applied
    ├── stat_grid.test.ts         # variants, responsive classes
    └── pattern_grid.test.ts
```

## Acceptance Criteria

- [ ] `renderArtifact({artifact_type: "roadmap", ...})` produces valid standalone HTML
- [ ] `phase_timeline.eta` renders all 5 phase fields (title, when, goal, blocks, output)
- [ ] Group colors applied via CSS variables (no hardcoded hex)
- [ ] Fixture data renders without error
- [ ] Shared design system tokens match answer_key output (same `--paper`, `--ink`, etc.)

## Dependencies

- Blocked by: `template-engine`, `component-schema`, `answer-key-template` (shared sidebar/hero partials)
- Priority: p1
