---
title: "Theme System v2: Group Colors + Dark Mode + Print CSS"
status: ready
labels: [branding, css, theme]
created: 2026-06-24
priority: p2
report: "08"
---

## What to build

Extend `common/branding/` with group color tokens (a-e), tint utilities, `.g-*` CSS classes. Add dark mode and print media queries. Update `generate_theme.py` to output the full design token set. Update renderer `loadThemeCss()` to consume generated files.

**Design decision:** Group colors live in `theme.json` as `groups.a` through `groups.e`. `generate_theme.py` emits both `--c-a` variables AND `.g-a { border-left-color: var(--c-a) }` utility classes.

## File Structure

```
common/branding/
├── theme.json               # EXTEND: add "groups" and "typography" sections
├── generate_theme.py        # EXTEND: emit group tokens, tints, utility classes, dark/print
└── generated/
    ├── theme_default.css    # generated output (gitignored or committed)
    └── theme_*.css          # other themes
```

## Implementation Spec

### `theme.json` additions
```json
{
  "colors": {
    "paper": "#FBF4F0", "card": "#FFFFFF", "ink": "#22273A",
    "ink-soft": "#5C6275", "ink-faint": "#8B8FA0",
    "line": "#E8D8CD", "shadow": "rgba(34,39,58,0.06)",
    "red": "#B23A2E", "gold": "#A8782E", "green": "#2E6F4E"
  },
  "groups": {
    "a": { "color": "#33508F", "label": "Ngữ pháp – Từ vựng" },
    "b": { "color": "#B9762A", "label": "Hội thoại" },
    "c": { "color": "#3C7A4E", "label": "Viết lại / Kết hợp câu" },
    "d": { "color": "#1F7A8C", "label": "Điền từ & Đọc hiểu" },
    "e": { "color": "#8A4F7E", "label": "Tư duy logic" }
  },
  "typography": {
    "font-heading": "Georgia, 'Times New Roman', serif",
    "font-body": "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif",
    "font-mono": "'SF Mono', 'Fira Code', 'Cascadia Code', monospace"
  },
  "spacing": {
    "radius": "12px",
    "shadow": "0 1px 2px rgba(34,39,58,0.06), 0 2px 8px rgba(34,39,58,0.04)"
  }
}
```

### `generate_theme.py` — EXTEND
Outputs:
```css
:root {
  /* Core tokens */
  --paper: #FBF4F0; --card: #FFFFFF; --ink: #22273A; ...

  /* Group colors + tints */
  --c-a: #33508F; --c-a-tint: rgba(51,80,143,0.08);
  --c-b: #B9762A; --c-b-tint: rgba(185,118,42,0.09);
  ...

  /* Typography */
  --font-heading: Georgia, 'Times New Roman', serif;
  --font-body: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;

  /* Spacing */
  --radius: 12px;
  --shadow: 0 1px 2px rgba(34,39,58,0.06), ...;
}

/* Group utility classes */
.g-a { border-left-color: var(--c-a); }
.g-a .qnum, .g-a .pc-id { background: var(--c-a); color: #fff; }
.g-a-tint { background: var(--c-a-tint); }
...

/* Dark mode */
@media (prefers-color-scheme: dark) {
  :root { --paper: #1a1a2e; --card: #252540; --ink: #e8e8f0; ... }
}

/* Print */
@media print {
  .sidebar, .no-print { display: none; }
  .shell { display: block; }
  .page-break { page-break-before: always; }
  body { background: white; color: black; }
}
```

### `generate_theme.py` structure (modular)
Split into functions, not one big script:
- `load_theme_json(path) -> dict`
- `generate_core_tokens(colors: dict) -> str`
- `generate_group_tokens(groups: dict) -> str`
- `generate_typography_tokens(typography: dict) -> str`
- `generate_utility_classes(groups: dict) -> str`
- `generate_dark_mode(colors: dict) -> str`
- `generate_print_styles() -> str`
- `main()` — assembles all sections, writes to `generated/`

## Tests

```
common/branding/tests/test_generate_theme.py
```

Test: `generate_core_tokens` outputs all color variables; `generate_group_tokens` outputs `--c-a` through `--c-e`; `generate_utility_classes` outputs `.g-a` through `.g-e`; no Google Fonts in output; dark mode block present; print block present.

## Acceptance Criteria

- [ ] `theme.json` has `groups`, `typography`, `spacing` sections
- [ ] `generate_theme.py` is modular (7 pure functions + `main()`)
- [ ] Generated CSS has `--c-a` through `--c-e` + tint variants
- [ ] `.g-a` through `.g-e` utility classes generated
- [ ] Dark mode `@media (prefers-color-scheme: dark)` block present
- [ ] Print `@media print` block with `.sidebar { display:none }` present
- [ ] No Google Fonts or external font imports in generated CSS
- [ ] `loadThemeCss()` in renderer updated to consume generated files
- [ ] `generate_theme.py` tested with 100% function coverage

## Dependencies

- Blocked by: nothing (standalone)
- Blocks: `answer-key-template`, `roadmap-template` (need group colors at runtime)
- Priority: p2

## Research Findings

**Source**: Report 08 Section 13 — Template Engine & Component Dispatch

### Standalone HTML Requirements (All Systems)
- All CSS inlined within components
- No external CDN references (INVARIANT-04)
- System font stacks only (no custom web fonts)
- Media queries for responsive + print + dark mode

### Dark Mode Pattern
@media (prefers-color-scheme: dark) { :root { --paper: #1a1a2e; ... } }
All color tokens must have dark variants
Group colors need tint adjustments for dark backgrounds

### Print Styles (Moodle Pattern)
@media print { .sidebar, .no-print { display: none; } .shell { display: block; } }
body { background: white; color: black; }

### Quality Gate Integration
Layer 3 HTML validator checks: DOCTYPE, no CDN, brand strings, responsive
Hard blocks: missing_doctype, external_assets, answer_key_leakage, native_radio_inputs

### Key References
- Moodle Output API: https://docs.moodle.org/dev/Output_API
- WCAG 2.1 contrast requirements: https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum
