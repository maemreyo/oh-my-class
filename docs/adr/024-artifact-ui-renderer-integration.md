# ADR-024: Artifact UI Renderer Integration

## Status

**Decided** (2026-07-02) — The Artifact UI CSS design system from `.scratch/artifact-ui-integrations/resources/` integrates into `packages/renderer/` via a family-registry pattern with dedicated templates, contract adapters, and a public `renderArtifactUi()` API.

## Context

ADR-023 decided that generated teaching artifacts use a dedicated Artifact UI layer separate from the product dashboard. The implementation in `.scratch/artifact-ui-integrations/resources/artifact-ui/` delivered:

- 10 CSS files (contract + 4 family tokens + primitives + 4 family components) — 1,400 lines of framework-agnostic CSS
- A `render.js` harness simulating the real Eta pipeline
- 12 built HTML demos proving the design system works standalone
- Teacher/student projection safety verified via grep (ADR-022)

However, the CSS lives in `.scratch/`, not in the renderer package. The renderer currently has:

- `src/artifact-ui/` — **does not exist**
- `src/semantic-anchor-projections.ts` — inline CSS, manual HTML generation (the old way)
- `src/inverse-thinking-renderer.ts` — inline CSS, manual HTML generation (the old way)
- `src/theme/` — three-tier token system (`ThemeTokens` interface) used by `renderArtifact()`
- `templates/` — Eta templates with `base.html` shell and per-page CSS

The existing inline renderers produce correct but visually generic output. The Artifact UI CSS produces expressive, tactile, print-ready output matching the reference templates.

The goal is to:

1. Port the CSS into the renderer package
2. Create Eta templates that use Artifact UI classes
3. Wire typed contracts (`SemanticAnchorCluster`, lesson plans, exam keys, video routes, inverse-thinking) to the new templates
4. Replace the old inline renderers
5. Establish a pattern so adding a new artifact UI family requires minimal new code

## Decision

### 1. Folder structure — family-registry pattern

```
packages/renderer/src/artifact-ui/
├── tokens/
│   ├── contract.css              # Shared semantic token contract (ADR-023 §4)
│   ├── navy-ticket.css           # Navy ticket family primitives
│   ├── paper-dossier.css         # Paper dossier family primitives
│   ├── transit-route.css         # Transit route family primitives
│   └── investigation-folder.css  # Investigation folder family primitives
├── primitives.css                # Core family-agnostic components
├── families/
│   ├── navy-ticket.css           # Navy ticket family components
│   ├── paper-dossier.css         # Paper dossier family components
│   ├── transit-route.css         # Transit route family components
│   └── investigation-folder.css  # Investigation folder family components
├── registry.ts                   # Family registry (extensible)
├── loader.ts                     # CSS loading + inlining
└── index.ts                      # Public API

packages/renderer/templates/artifact/
├── navy-ticket/
│   ├── teaching.teacher.html     # Teacher projection
│   └── teaching.student.html     # Student projection
├── paper-dossier/
│   ├── lesson.html               # Lesson/path dossier
│   └── answer-key.html           # Exam answer key
├── transit-route/
│   └── video-route.html          # Video learning route
└── investigation-folder/
    └── inverse-thinking.html     # Inverse thinking investigation
```

**Why this structure:**

- CSS lives in `src/artifact-ui/` alongside the theme system — co-located with the code that consumes it
- Templates live in `templates/artifact/` alongside existing page templates — consistent with Eta's `views` config
- Each family is a directory, not a flat file — adding a new family means adding one directory with CSS + templates
- The registry is a TypeScript file, not config — type-safe, IDE-friendly, testable

### 2. Family registry — extensible by convention

```typescript
// registry.ts
export interface ArtifactFamily {
  /** Unique identifier matching data-artifact-theme attribute */
  readonly id: string;
  /** Human-readable name */
  readonly name: string;
  /** Path to family CSS file (relative to src/artifact-ui/) */
  readonly tokenFile: string;
  /** Path to family components CSS file */
  readonly familyFile: string;
  /** Eta template directory (relative to templates/artifact/) */
  readonly templateDir: string;
  /** Contract adapter function name */
  readonly adapterName: string;
  /** Supported artifact types for this family */
  readonly supportedTypes: readonly string[];
}

export const ARTIFACT_FAMILIES: readonly ArtifactFamily[] = [
  {
    id: 'navy-ticket',
    name: 'Navy Ticket',
    tokenFile: 'tokens/navy-ticket.css',
    familyFile: 'families/navy-ticket.css',
    templateDir: 'navy-ticket',
    adapterName: 'navyTicketAdapter',
    supportedTypes: ['teaching', 'practice'],
  },
  {
    id: 'paper-dossier',
    name: 'Paper Dossier',
    tokenFile: 'tokens/paper-dossier.css',
    familyFile: 'families/paper-dossier.css',
    templateDir: 'paper-dossier',
    adapterName: 'paperDossierAdapter',
    supportedTypes: ['lesson', 'answer-key', 'worksheet'],
  },
  {
    id: 'transit-route',
    name: 'Transit Route',
    tokenFile: 'tokens/transit-route.css',
    familyFile: 'families/transit-route.css',
    templateDir: 'transit-route',
    adapterName: 'transitRouteAdapter',
    supportedTypes: ['video-route'],
  },
  {
    id: 'investigation-folder',
    name: 'Investigation Folder',
    tokenFile: 'tokens/investigation-folder.css',
    familyFile: 'families/investigation-folder.css',
    templateDir: 'investigation-folder',
    adapterName: 'investigationFolderAdapter',
    supportedTypes: ['inverse-thinking'],
  },
] as const;
```

**Adding a new family = one registry entry + CSS files + templates + adapter.** No changes to the loader, renderer, or existing families.

### 3. CSS loading — standalone and offline

The loader concatenates CSS files in the correct order:

```
1. tokens/contract.css          # Shared semantic contract
2. tokens/{family}.css          # Family-specific token overrides
3. primitives.css               # Core family-agnostic components
4. families/{family}.css        # Family-specific components
```

All CSS is inlined into a single `<style>` block at render time — satisfying the standalone HTML invariant (AGENTS.md §8.4).

```typescript
// loader.ts
export function loadArtifactCSS(familyId: string): string {
  const family = getFamily(familyId);
  return [
    readCss('tokens/contract.css'),
    readCss(family.tokenFile),
    readCss('primitives.css'),
    readCss(family.familyFile),
  ].join('\n\n');
}
```

### 4. Render pipeline — contract → adapter → Eta → HTML

```
Typed Contract (e.g. SemanticAnchorCluster)
  │
  ▼
Family Adapter (navyTicketAdapter)
  │  Transforms contract → Eta template data shape
  │  Handles teacher/student projection safety (ADR-022)
  │
  ▼
Eta Template (templates/artifact/navy-ticket/teaching.teacher.html)
  │  Uses Artifact UI CSS classes (art-*)
  │  No inline styles, no CDN, no external assets
  │
  ▼
Standalone HTML
  │  All CSS inlined in <style> block
  │  data-artifact-theme="{family}" on root element
  │  oh-my-class brand string present
  │  Print-safe (@media print rules)
```

### 5. Public API — renderArtifactUi()

```typescript
// index.ts
export async function renderArtifactUi(
  request: ArtifactUiRenderRequest,
): Promise<string> {
  const family = getFamily(request.family);
  const adapter = getAdapter(family.adapterName);
  const templateData = adapter(request.contract, request.audience);
  const css = loadArtifactCSS(family.id);

  const html = await eta.renderAsync(
    `${family.templateDir}/${request.kind}.${request.audience}`,
    { ...templateData, artifactCSS: css, family: family.id },
  );

  return sanitize(html, request.artifactType);
}

export type ArtifactUiRenderRequest = {
  family: string;              // 'navy-ticket' | 'paper-dossier' | ...
  contract: unknown;           // Typed contract (SemanticAnchorCluster, etc.)
  audience: 'teacher' | 'student';
  kind: string;                // 'teaching' | 'practice' | 'lesson' | ...
  artifactType: string;        // For sanitizer config
};
```

### 6. Coexistence with existing theme system

The Artifact UI token system (`--art-*` prefix) is fully namespace-isolated from the existing renderer token system (`--color-*` prefix):

| System | Prefix | Consumer | Scope |
|--------|--------|----------|-------|
| Product/teaching-pack UI | `--color-*`, `--font-*` | Existing templates via `base.html` | Dashboard, teaching packs |
| Artifact UI | `--art-*` | New artifact templates via `renderArtifactUi()` | Standalone learning materials |

Both systems can coexist in the same renderer package. The `renderArtifact()` function (existing) and `renderArtifactUi()` function (new) are separate entry points with separate CSS injection paths.

### 7. Migration — replace inline renderers

| Old Renderer | Replacement | Family |
|--------------|-------------|--------|
| `semantic-anchor-projections.ts` | `renderArtifactUi()` with `navy-ticket` | navy-ticket |
| `inverse-thinking-renderer.ts` | `renderArtifactUi()` with `investigation-folder` | investigation-folder |
| Existing Eta templates (lesson, quiz, etc.) | `renderArtifactUi()` with `paper-dossier` | paper-dossier |

The old renderers are deleted after parity is verified. No gradual migration — clean replacement.

### 8. Scalability — adding a new family

To add a new artifact UI family (e.g., "science-lab"):

1. **Create CSS files:**
   - `src/artifact-ui/tokens/science-lab.css` — token overrides implementing `contract.css`
   - `src/artifact-ui/families/science-lab.css` — family-specific components

2. **Create templates:**
   - `templates/artifact/science-lab/{kind}.html` — Eta templates using `art-*` classes

3. **Create adapter:**
   - `src/artifact-ui/adapters/science-lab.ts` — transforms typed contract → template data

4. **Register:**
   - Add entry to `ARTIFACT_FAMILIES` in `registry.ts`

5. **Test:**
   - Add Vitest tests for standalone HTML invariants
   - Add Playwright visual QA at 375/768/1280

**No changes to:** loader.ts, index.ts, existing families, existing templates, or existing tests.

## Consequences

- Artifact UI CSS becomes a first-class part of the renderer package, versioned and tested alongside templates.
- The family-registry pattern makes adding new families mechanical — one entry + CSS + templates + adapter.
- The `--art-*` / `--color-*` namespace isolation prevents token collisions between product UI and artifact UI.
- Replacing inline renderers eliminates duplicate CSS and manual HTML generation.
- The standalone HTML invariant is preserved by construction (CSS inlining, no external assets).
- Teacher/student projection safety (ADR-022) is enforced by the adapter layer, not by CSS hiding.

## Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| Extend existing `ThemeTokens` with `--art-*` | Single token system | Couples artifact UI to product UI; token collision risk as families grow |
| Keep inline renderers, add Artifact UI as option | Zero migration risk | Duplicate CSS, technical debt, inconsistent visual language |
| Use a CSS-in-JS library | Runtime styling flexibility | Violates standalone HTML invariant; adds bundle weight |
| Put CSS in `common/branding/kits/` | Shared with Python agents | Artifact UI is renderer-only; Python agents don't consume CSS |
| Flat file structure (no family directories) | Simpler | Adding a new family scatters files across directories |

## References

- ADR-023: Artifact UI Layer from Template Corpus
- ADR-022: Semantic Anchor Domain Model and Projections
- ADR-021: Vocabulary Batch Pipeline Mode
- `.scratch/artifact-ui-integrations/resources/` — CSS implementation handoff
- `packages/renderer/src/theme/tokens.ts` — existing three-tier token model
- `packages/renderer/src/semantic-anchor-projections.ts` — current inline renderer (to be replaced)
- `packages/renderer/src/inverse-thinking-renderer.ts` — current inline renderer (to be replaced)
