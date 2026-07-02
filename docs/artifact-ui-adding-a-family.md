# Adding a New Artifact UI Family

Step-by-step checklist for adding a 5th (or Nth) family to the Artifact UI renderer.
No changes outside `src/artifact-ui/` or `templates/artifact/` are required.

See ADR-024 §8 (Scalability) for the architectural rationale.

---

## Required artifacts (exactly 4)

| # | Artifact | Location |
|---|----------|----------|
| 1 | Token CSS | `src/artifact-ui/tokens/<family-id>.css` |
| 2 | Family CSS | `src/artifact-ui/families/<family-id>.css` |
| 3 | Eta template(s) | `templates/artifact/<family-id>/<kind>.html` |
| 4 | Contract adapter | `src/artifact-ui/adapters/<family-id>.ts` |
| 5 | Registry entry | `src/artifact-ui/registry.ts` (1-line addition) |

**Nothing else changes.** The loader, renderer, sanitizer, and existing families are untouched.

---

## Step-by-step checklist

### Step 1 — Choose a family ID

- Use `kebab-case` (e.g., `science-lab`)
- Must be unique — check `registry.ts` for conflicts
- Will appear in `data-artifact-theme="<family-id>"` on the `<html>` element

### Step 2 — Create the token CSS file

Create `src/artifact-ui/tokens/<family-id>.css`:

```css
/*
 * <Family Name> — design tokens
 * Namespace all custom properties with --art-* (e.g., --art-lab-border).
 * DO NOT use --art-* names already defined in tokens/contract.css.
 */

[data-artifact-theme="<family-id>"] {
  /* Extend or override contract tokens here */
  --art-accent: #2e7d5e;   /* example: a teal accent */
}
```

Avoid token namespace collisions — check `tokens/contract.css` for reserved names.

### Step 3 — Create the family CSS file

Create `src/artifact-ui/families/<family-id>.css`:

```css
/*
 * <Family Name> — component styles
 * Reference: docs/artifact-ui-adding-a-family.md · Issue NNN
 * Used by: <kind> kind(s) (Issue NNN)
 */

/* ---- Component-specific classes ---- */
.art-<family-specific-class> { ... }
```

**CSS class namespace rules:**
- Prefix all new classes with `.art-` (shared primitives) or `.art-<family>-` (family-specific)
- Never use generic class names like `.card`, `.section` without the `.art-` prefix
- The primitives (`src/artifact-ui/primitives.css`) provide `.art-projection-flag`, `.art-teacher-block`, `.art-callout`, etc. — reuse them instead of reinventing

**CSS loading order** (set by `loadArtifactCSS()`):
1. `tokens/contract.css` — global token definitions
2. `tokens/<family-id>.css` — family token overrides
3. `primitives.css` — shared components (teacher block, callout, shell, etc.)
4. `families/<family-id>.css` — family-specific components

> **Note:** `loadArtifactCSS()` is memoized at the module level — 4 unique CSS reads max per process lifetime, regardless of batch size (Issue 016).

### Step 4 — Add the registry entry

In `src/artifact-ui/registry.ts`, add one entry to the `FAMILIES` map:

```typescript
"science-lab": {
  id: "science-lab",
  tokenFile: "tokens/science-lab.css",
  familyFile: "families/science-lab.css",
  supportedKinds: ["experiment-log", "safety-quiz"],
},
```

`supportedKinds` is informational — it documents valid kinds but the renderer does not validate against it at runtime.

### Step 5 — Create Eta template(s)

Create one file per kind: `templates/artifact/<family-id>/<kind>.html`

```html
<%
/* <family-id>/<kind>.html
   it = <FamilyName>TemplateData (from adapter)
*/
const lang = it.lang || 'vi';
%>
<!DOCTYPE html>
<html lang="<%= lang %>" data-artifact-theme="<family-id>">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title><%= it.title %></title>
  <style><%~ it.artifactCss %></style>
  <%# If this kind needs interactivity.js, add it here in <head>: %>
  <%# <% if (it.interactivityJS) { %><script><%~ it.interactivityJS %></script><% } %> %>
</head>
<body>
<div class="art-root">
  <!-- your template content -->
  <footer class="art-footer">
    <span class="art-mono"><%= it.title %></span>
    <span class="art-mono" style="margin-left:auto;">oh-my-class</span>
  </footer>
</div>
</body>
</html>
```

**Template rules:**
- Always set `data-artifact-theme="<family-id>"` on `<html>`
- Always inline CSS: `<style><%~ it.artifactCss %></style>` — no `<link>` tags
- Never use `src=` on `<video>` or `<iframe>` — only metadata placeholders (INVARIANT-04)
- Teacher-only blocks: wrap in `<% if (it.isTeacher) { %> ... <% } %>` and gate them in the adapter too
- Use `<%~ ... %>` (unescaped) only for pre-trusted CSS/JS; use `<%= ... %>` (escaped) for all user data
- Eta **always** appends `.html` if the template name contains no dot. Use explicit `.html` suffix in `templatePath()` for families whose kind names contain dots (like `navy-ticket`'s `teaching.teacher`)

### Step 6 — Create the contract adapter

Create `src/artifact-ui/adapters/<family-id>.ts`:

```typescript
import type { MyFamilyInputData } from "../../contracts/my-family.js";

export interface MyFamilyTemplateData {
  artifactCss: string;
  lang: string;
  title: string;
  isTeacher: boolean;
  // ... other fields
}

export function adaptMyFamily(
  input: MyFamilyInputData,
  audience: "teacher" | "student",
  artifactCss: string,
): MyFamilyTemplateData {
  const isTeacher = audience === "teacher";
  return {
    artifactCss,
    lang: input.lang ?? "vi",
    title: input.title,
    isTeacher,
    // Strip teacher-only fields from student output here (ADR-022):
    teacherNotes: isTeacher ? input.teacherNotes : undefined,
    // ...
  };
}
```

**Projection safety (ADR-022):**
- Teacher-only data is stripped in the **adapter**, not hidden via CSS
- Student HTML must never contain teacher-only DOM elements
- Pass `isTeacher: false` for student audience → template skips teacher blocks

### Step 7 — Export from adapters barrel

In `src/artifact-ui/adapters/index.ts`, add:

```typescript
export { adaptMyFamily } from "./my-family.js";
```

### Step 8 — Wire the adapter in `renderer.ts`

In `src/artifact-ui/renderer.ts`, add:
1. Import: `import { adaptMyFamily } from "./adapters/index.js";`
2. Import your request type and add it to `ArtifactUiRenderRequest`
3. Add a case in `buildTemplateData()`:
   ```typescript
   case "science-lab":
     return adaptMyFamily(request.data, request.audience, css) as unknown as TemplateData;
   ```

### Step 9 — Write tests

Minimum test suite (`__tests__/artifact-ui/<family-id>-rendering.test.ts`):

- [ ] Renders valid standalone HTML with `data-artifact-theme="<family-id>"`
- [ ] Contains "oh-my-class" brand string
- [ ] Contains no external URLs (`not.toMatch(/https?:\/\//)`)
- [ ] Contains no `<link>` tags
- [ ] Teacher audience: `toContain('class="art-projection-flag"')`
- [ ] Student audience: `not.toContain('class="art-projection-flag"')`
- [ ] Student audience: `not.toContain('class="art-teacher-block"')`
- [ ] INVARIANT-04 (if applicable): no `<video>` or `<iframe>` src in output

> **Test assertion note:** `art-projection-flag` and `art-teacher-block` appear as CSS selectors
> in `primitives.css` (which is inlined). Use `class="art-projection-flag"` (the element attribute
> pattern) in assertions, NOT just the bare class name — otherwise the CSS comment matches.

### Step 10 — No sanitizer config needed

`sanitizeArtifactUi()` uses a single shared `ARTIFACT_UI_CONFIG` (`src/sanitizer/configs/artifact-ui.ts`).
Adding a new family requires **no changes to the sanitizer**.

---

## What NOT to modify

| File | Why it's untouched |
|------|--------------------|
| `src/artifact-ui/loader.ts` | Discovers CSS by family registry — no hard-coded list |
| `src/artifact-ui/primitives.css` | Shared component styles — add family-specific styles in `families/` instead |
| `src/sanitizer/configs/artifact-ui.ts` | Shared config for all families |
| `src/contracts/index.ts` | Only add contract type if it has non-UI uses; render contracts live in `src/contracts/` |
| Any existing family's CSS/templates/adapter | Each family is fully isolated |

---

## `ArtifactFamily` interface (registry)

```typescript
interface ArtifactFamily {
  id: string;           // kebab-case, matches data-artifact-theme
  tokenFile: string;    // relative to src/artifact-ui/
  familyFile: string;   // relative to src/artifact-ui/
  supportedKinds: string[];  // informational — used for docs/discovery
}
```

---

## Example: hypothetical "science-lab" family

**Kinds:** `experiment-log`, `safety-quiz`

```
src/artifact-ui/tokens/science-lab.css        ← Step 2
src/artifact-ui/families/science-lab.css       ← Step 3
templates/artifact/science-lab/experiment-log.html  ← Step 5a
templates/artifact/science-lab/safety-quiz.html     ← Step 5b
src/artifact-ui/adapters/science-lab.ts        ← Step 6
```

Registry entry (`registry.ts`):
```typescript
"science-lab": {
  id: "science-lab",
  tokenFile: "tokens/science-lab.css",
  familyFile: "families/science-lab.css",
  supportedKinds: ["experiment-log", "safety-quiz"],
},
```

No other files change. `renderArtifactUi({ family: "science-lab", kind: "experiment-log", ... })` resolves
and renders via the same pipeline as all other families.

---

## Common pitfalls

| Pitfall | Fix |
|---------|-----|
| CSS token namespace collision | Check `tokens/contract.css` for reserved `--art-*` names |
| Teacher content visible in student output | Strip in adapter (`isTeacher ? value : undefined`), not in CSS |
| Eta template not found (name with dot) | Use explicit `.html` suffix in `templatePath()` when kind names contain dots |
| `<video src>` in output | Use placeholder div + text note; never `<video src="...">` |
| `ArtifactDataMap` modified | Do NOT add family types here — they are render-layer only (ADR-024) |
| External assets in HTML | All CSS/JS inlined; no CDN, no `<link>` |

---

*Generated for ADR-024. See also: [DESIGN.md](.scratch/artifact-ui-integrations/resources/DESIGN.md)*
