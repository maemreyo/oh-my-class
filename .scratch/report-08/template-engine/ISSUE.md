---
title: "Template Engine: Eta Dispatcher Pattern — renderArtifact() Rewrite"
status: ready
labels: [renderer, typescript, templates]
created: 2026-06-24
priority: p0
report: "08"
---

## What to build

Rewrite `packages/renderer/src/renderer.ts` to use Eta's layout+block system with a `dispatcher.eta` central router. Replace manual `buildContentHtml()` with typed component dispatch. All templates converted from `.html` → `.eta`.

**Design decision:** Dispatcher pattern (Khan Perseus / json-render). LLM generates typed ContentComponent JSON → Zod validates → Eta dispatcher routes each component to its partial → sanitizer cleans.

## File Structure

```
packages/renderer/
├── src/
│   ├── renderer.ts          # REWRITE: renderArtifact() uses Eta dispatch
│   ├── sanitizer.ts         # KEEP AS-IS
│   ├── inline-assets.ts     # KEEP AS-IS
│   └── theme.ts             # NEW: loadThemeCss() reads generated theme_*.css
├── templates/
│   ├── base.eta             # REWRITE from base.html: layout + block system
│   ├── pages/
│   │   ├── lesson.eta       # Convert from lesson.html
│   │   ├── worksheet.eta    # Convert from worksheet.html
│   │   ├── quiz.eta
│   │   ├── drill.eta
│   │   ├── recap.eta
│   │   ├── infographic.eta
│   │   ├── answer_key.eta   # NEW (implemented in answer-key-template issue)
│   │   └── roadmap.eta      # NEW (implemented in roadmap-template issue)
│   └── components/
│       ├── dispatcher.eta   # THE ROUTER: switch on component.type
│       ├── heading.eta      # NEW
│       ├── paragraph.eta    # NEW
│       ├── callout.eta      # NEW
│       ├── table.eta        # NEW
│       └── [other components added by answer-key-template and roadmap-template]
```

## Implementation Spec

### `src/theme.ts` — NEW
```typescript
import { readFileSync, existsSync } from "node:fs";
import path from "node:path";

const THEME_DIR = path.join(import.meta.dirname, "../../common/branding/generated");
const themeCache = new Map<string, string>();

const FALLBACK_CSS = `
:root {
  --paper: #FBF4F0; --card: #FFFFFF; --ink: #22273A;
  --ink-soft: #5C6275; --ink-faint: #8B8FA0;
  --line: #E8D8CD; --red: #B23A2E; --gold: #A8782E; --green: #2E6F4E;
  --c-a: #33508F; --c-b: #B9762A; --c-c: #3C7A4E; --c-d: #1F7A8C; --c-e: #8A4F7E;
  --font-heading: Georgia, 'Times New Roman', serif;
  --font-body: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
  --font-mono: 'SF Mono', 'Fira Code', monospace;
  --radius: 12px;
}`;

export function loadThemeCss(theme: string): string {
  if (themeCache.has(theme)) return themeCache.get(theme)!;
  const filePath = path.join(THEME_DIR, `theme_${theme}.css`);
  const css = existsSync(filePath) ? readFileSync(filePath, "utf-8") : FALLBACK_CSS;
  themeCache.set(theme, css);
  return css;
}
```

### `src/renderer.ts` — REWRITE
```typescript
import { Eta } from "eta";
import path from "node:path";
import { sanitizeHtml } from "./sanitizer.js";
import { loadThemeCss } from "./theme.js";

const eta = new Eta({
  views: path.join(import.meta.dirname, "../templates"),
  cache: process.env.NODE_ENV === "production",
});

const SUPPORTED_ARTIFACT_TYPES = new Set([
  "lesson", "worksheet", "quiz", "drill", "recap", "infographic",
  "answer_key", "roadmap",
]);

export function renderArtifact(data: Record<string, unknown>): string {
  const artifactType = data["artifact_type"] as string;
  if (!SUPPORTED_ARTIFACT_TYPES.has(artifactType)) {
    throw new Error(`Unknown artifact type: ${artifactType}`);
  }

  const theme = (data["theme"] as string) ?? "default";
  const themeCss = loadThemeCss(theme);

  const html = eta.render(`./pages/${artifactType}`, {
    ...data,
    themeCss,
  });

  if (!html) throw new Error(`Template render failed for: ${artifactType}`);
  return sanitizeHtml(html);
}

export function renderTemplate(
  templateStr: string,
  data: Record<string, unknown>,
): string {
  if (!templateStr) return "";
  return eta.renderString(templateStr, data) ?? "";
}
```

### `templates/base.eta` — REWRITE
```eta
<!DOCTYPE html>
<html lang="<%= it.lang ?? 'vi' %>">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title><%= it.title %> — oh-my-class</title>
  <style>
    <%= it.themeCss %>
    *, *::before, *::after { box-sizing: border-box; }
    body { margin: 0; font-family: var(--font-body); background: var(--paper, #fff); color: var(--ink, #222); }
  </style>
</head>
<body>
  <%~ it.body %>
</body>
</html>
```

### `templates/components/dispatcher.eta` — NEW (architectural keystone)
```eta
<%
const type = it.component?.type;
if (type === "heading") { %>
  <%~ include("./heading", it.component) %>
<% } else if (type === "paragraph") { %>
  <%~ include("./paragraph", it.component) %>
<% } else if (type === "callout") { %>
  <%~ include("./callout", it.component) %>
<% } else if (type === "table") { %>
  <%~ include("./table", it.component) %>
<% } else if (type === "stat_grid") { %>
  <%~ include("./stat_grid", it.component) %>
<% } else if (type === "pattern_grid") { %>
  <%~ include("./pattern_grid", it.component) %>
<% } else if (type === "trait_grid") { %>
  <%~ include("./trait_grid", it.component) %>
<% } else if (type === "taxonomy_grid") { %>
  <%~ include("./taxonomy_grid", it.component) %>
<% } else if (type === "phase_timeline") { %>
  <%~ include("./phase_timeline", it.component) %>
<% } else if (type === "flow_step") { %>
  <%~ include("./flow_step", it.component) %>
<% } else if (type === "question_card") { %>
  <%~ include("./question_card", it.component) %>
<% } else if (type === "question_list") { %>
  <%~ include("./question_list", it.component) %>
<% } else if (type === "alert") { %>
  <%~ include("./alert", it.component) %>
<% } else { %>
  <!-- unknown component type: <%= type %> -->
<% } %>
```

### Existing page stubs — CONVERT to `.eta`
Each existing `.html` page stub becomes `.eta`, calls `base.eta`, renders sections via dispatcher:

```eta
<%~ include("../base", { title: it.title, lang: it.accessibility?.language || 'vi', themeCss: it.themeCss, body: "" }) %>
```

(Full page templates for answer_key and roadmap implemented in their own issues.)

## Tests

```
packages/renderer/src/__tests__/
├── renderer.test.ts          # renderArtifact() with all artifact types
├── theme.test.ts             # loadThemeCss() fallback + cache
└── dispatcher.test.ts        # each component type dispatches correctly
```

Test: all 8 artifact types render without throwing; unknown type throws; sanitizer called; themeCss injected.

## Acceptance Criteria

- [ ] `renderArtifact()` uses Eta dispatch — zero manual HTML string building
- [ ] `dispatcher.eta` routes all 14 component types
- [ ] `theme.ts` extracted — `loadThemeCss()` with fallback + cache
- [ ] All 6 existing page stubs converted to `.eta`
- [ ] `base.eta` uses layout pattern (not manual DOCTYPE string)
- [ ] `buildContentHtml()` removed
- [ ] All tests pass

## Dependencies

- Blocked by: `component-schema` (needs artifact types enum)
- Blocks: `answer-key-template`, `roadmap-template`
- Priority: p0

## Research Findings

**Source**: Report 08 Section 13 — Template Engine & Component Dispatch

### Khan Academy Perseus Pattern
registerWidget() → WidgetExports<T> → getWidget() rendering
Editor registration with bidirectional data binding
Error Boundary: widget failures silently disappear (don't crash)

### Vercel json-render Pattern
defineCatalog() + defineRegistry() with Zod-backed schemas
ActionProvider for event handling
Sub-200ms hydration via fine-grained component hydration

### Eta.js Production Patterns
layout() + block() system for page composition
include() / includeAsync() for partials
Whitespace control via ~> and ~ delimiters
Custom tags for component-like elements

### LLM→JSON→Template Pipeline
autoFixSpec() distinguishes lossy vs lossless fixes
retry_prompt informed by validation errors
3 retries before full pipeline restart

### Performance Benchmarks
Perseus: LCP sub-500ms
json-render: sub-200ms hydration
Moodle: JS bundle <50KB
End-to-end (LLM→HTML): 2100-5200ms

### Key References
- Perseus: https://github.com/Khan/perseus
- json-render: https://github.com/vercel-labs/json-render
- Eta.js: https://eta.js.org/
