# Renderer Redesign — Grilling Resolution

> Source review: `.scratch/renderer-module/renderer-module-architecture-review.md`
> Outcome: resolve all proposed architectural issues into a production-ready redesign direction.

---

## 1. Final Direction

We will perform a **big-bang production-ready rewrite** of `packages/renderer/` around a single **Artifact-Kind Plugin Registry**.

This is not a patch of the current implementation. The target is a clean, enforceable renderer architecture that is:

- harnessed by runtime schemas and registry completeness tests
- smart and explicit about artifact kinds, audience, themes, render modes, and asset policy
- production-ready with typed errors, observability, version manifests, and worker protocol diagnostics
- flexible and scalable via self-contained plugins
- high-readability and modular by folder layout
- standalone by runtime asset-policy enforcement
- well-tested with global invariants, snapshots, XSS corpus, worker contract tests, and visual/print smoke tests
- UI/UX-centric via accessibility theme coverage, print mode, i18n catalog, and stable rendered outputs
- adapted to existing app features by replacing current callers with the new unified API

---

## 2. Decisions Chosen During Grilling

### D1 — Architecture target

**Decision:** Use **Artifact-Kind Plugin Registry** as the sole renderer architecture.

**Implementation mode:** Big-bang rewrite.

**Implication:** We are allowed to delete or replace old internals instead of preserving them as permanent compatibility wrappers.

---

### D2 — Public API compatibility

**Decision:** Public API may be breaking.

**Implication:** Existing public APIs such as `renderArtifact`, `renderArtifactUi`, `renderArtifactUiSet`, `renderSemanticAnchorProjectionSet`, and `renderInverseThinkingHtml` do not need to remain public.

Current callers must migrate to the new API.

---

### D3 — Single source of truth for artifact identity

**Decision:** Use registry `kind` as the only source of truth.

Recommended kind examples:

```text
quiz
worksheet
drill
recap
infographic
lesson
answer_key
flashcard_deck
reading_passage
exit_ticket
roadmap
teaching_pack
navy-ticket.teaching
navy-ticket.practice
paper-dossier.lesson
paper-dossier.answer-key
paper-dossier.root-cause-session
transit-route.video-route
investigation-folder.inverse-thinking
```

`artifact_type` from current agent output becomes a boundary-normalized legacy field, not the renderer's identity model.

---

### D4 — RenderContext

**Decision:** Every render call must include a full `RenderContext`.

```ts
export type Audience = "teacher" | "student";
export type Locale = "vi" | "en";
export type RenderMode = "preview" | "export" | "print";
export type AssetPolicy = "inline-only";

export interface RenderContext {
  readonly audience: Audience;
  readonly locale: Locale;
  readonly theme: string;
  readonly renderMode: RenderMode;
  readonly requestId: string;
  readonly versions: RenderVersionContext;
  readonly assetPolicy: AssetPolicy;
}

export interface RenderVersionContext {
  readonly rendererVersion: string;
  readonly templateVersion: string;
  readonly themeVersion?: string;
}
```

Purpose by field:

| Field | Why it exists |
|---|---|
| `audience` | Teacher/student projection and answer-leak protection |
| `locale` | Message catalog and HTML `lang` |
| `theme` | Brand/accessibility theme resolution |
| `renderMode` | Preview/export/print differences, especially print CSS |
| `requestId` | Correlation across Python worker pool and Node renderer |
| `versions` | Version pinning and RenderManifest generation |
| `assetPolicy` | Standalone output enforcement |

---

### D5 — Runtime schemas per plugin

**Decision:** Every plugin must declare a runtime schema.

```ts
export interface ArtifactKindPlugin<TInput, TTemplateData> {
  readonly kind: string;
  readonly version: string;
  readonly schema: z.ZodType<TInput>;
  readonly capabilities: ArtifactKindCapabilities;
  readonly sanitizerPolicy: SanitizerPolicy;

  adapt(input: TInput, ctx: RenderContext, services: RenderServices): Promise<TTemplateData> | TTemplateData;
  templatePath(ctx: RenderContext): string;
}
```

`agent-renderer.ts`-style fallback extraction (`asRecord`, `asString`, shape guessing) should not exist in the core bridge anymore.

Boundary behavior:

```text
unknown input
  → normalize request
  → lookup plugin by kind
  → plugin.schema.parse(input)
  → plugin.adapt()
  → eta.renderAsync()
  → sanitizeRenderedHtml()
  → validateStandaloneHtml()
```

---

### D6 — Unified theme pipeline

**Decision:** Replace separate `theme/loader.ts` and `artifact-ui/loader.ts` behavior with a shared `ThemeResolver`.

```ts
export interface ThemeResolver {
  resolveTheme(request: ThemeRequest): Promise<ResolvedTheme> | ResolvedTheme;
}

export interface ThemeRequest {
  readonly themeId: string;
  readonly familyId?: string;
  readonly renderMode: RenderMode;
  readonly locale: Locale;
}

export interface ResolvedTheme {
  readonly themeId: string;
  readonly version: string;
  readonly css: string;
}
```

Cache key:

```text
(themeId, familyId?, renderMode, locale)
```

Required behavior:

- Accessibility themes apply to both regular artifacts and Artifact UI families.
- Family-specific CSS layers can still exist, but are resolved through shared theme policy.
- Plugin can opt out only by declaring `themeable: false` with a clear reason.

---

### D7 — Single sanitizer chokepoint

**Decision:** Replace `sanitize()` + `sanitizeArtifactUi()` + legacy regex `sanitizer.ts` with one core function.

```ts
export function sanitizeRenderedHtml(html: string, policy: SanitizerPolicy): string;
```

Responsibilities:

- preserve `<!DOCTYPE>`
- sanitize body content only for full HTML documents
- sanitize full fragment for fragments
- use `sanitize-html` allowlist from plugin policy
- no plugin-owned ad-hoc sanitizer

Delete:

- `renderArtifactSync()`
- regex-based `sanitizer.ts`

SVG-specific sanitizer can remain separate, but must be audited through the same security test corpus.

---

### D8 — Audience safety

**Decision:** Combine core audience policy with plugin-owned projection.

```ts
export interface AudiencePolicy {
  readonly supportsTeacher: boolean;
  readonly supportsStudent: boolean;
  readonly studentLeakFields: readonly string[];
}
```

Core requirements:

- plugin must declare audience support
- core rejects unsupported audience before rendering
- student output must pass leak-prevention invariant tests
- plugin owns domain-specific projection logic

Default leak field list:

```text
answer
answers
answer_key
correct_answer
correctAnswer
correct_option
correctOption
solution
solutions
explain
explanation
rationale
teacher_rationale
coaching_notes
reveal_answer
wrong_reasons
```

---

### D9 — Package boundary

**Decision:** Enforce public boundary with `package.json exports`.

Public surface should be through `@oh-my-class/renderer` only.

Proposed public exports:

```ts
export { render, renderBatch } from "./core/render.js";
export type {
  RenderRequest,
  RenderResponse,
  RenderContext,
  RenderManifest,
  ArtifactKindPlugin,
} from "./core/types.js";
export {
  RendererError,
  RendererErrorCode,
} from "./core/errors.js";
```

No deep imports from:

```text
@oh-my-class/renderer/src/theme/loader
@oh-my-class/renderer/src/artifact-ui/loader
@oh-my-class/renderer/src/sanitizer/index
@oh-my-class/renderer/src/plugins/...
```

---

### D10 — Support all existing artifact types in V1

**Decision:** V1 registry must support all 12 current `ArtifactType` members.

Required plugins:

```text
lesson
quiz
worksheet
drill
recap
infographic
answer_key
flashcard_deck
reading_passage
exit_ticket
roadmap
teaching_pack
```

Artifact UI kinds also remain first-class plugins:

```text
navy-ticket.teaching
navy-ticket.practice
paper-dossier.lesson
paper-dossier.answer-key
paper-dossier.root-cause-session
transit-route.video-route
investigation-folder.inverse-thinking
```

Special case:

`teaching_pack` is a **bundle plugin**. It should render child artifacts through `renderBatch()` or internal recursive rendering, not pretend to be a lesson.

---

### D11 — Version pinning

**Decision:** Save final rendered HTML and a `RenderManifest`.

```ts
export interface RenderManifest {
  readonly requestId: string;
  readonly kind: string;
  readonly audience: Audience;
  readonly locale: Locale;
  readonly renderMode: RenderMode;
  readonly rendererVersion: string;
  readonly pluginVersion: string;
  readonly templateVersion: string;
  readonly themeVersion: string;
  readonly sanitizerPolicyVersion: string;
  readonly renderedAt: string;
  readonly contentHash: string;
}
```

Behavior:

- Stored artifacts do not visually drift when theme/template changes later.
- Re-render must be explicit and produce a new manifest/version.
- Export/audit should use stored `rendered_html` by default.

---

### D12 — Worker protocol

**Decision:** Upgrade Python↔Node worker protocol while keeping stdin/stdout transport.

Request:

```ts
export interface WorkerRenderRequest {
  readonly requestId: string;
  readonly kind: string;
  readonly input: unknown;
  readonly context: RenderContext;
}
```

Success response:

```ts
export interface WorkerRenderSuccess {
  readonly ok: true;
  readonly html: string;
  readonly manifest: RenderManifest;
  readonly diagnostics: RenderDiagnostic[];
  readonly metrics: RenderMetrics;
}
```

Failure response:

```ts
export interface WorkerRenderFailure {
  readonly ok: false;
  readonly error: SerializedRendererError;
  readonly diagnostics: RenderDiagnostic[];
  readonly metrics?: RenderMetrics;
}
```

This allows `renderer_pool.py` to distinguish:

- validation/input errors: do not retry
- unknown kind/template missing: do not retry, alert
- timeout/internal transient failures: retry if retryable

---

### D13 — Print support

**Decision:** Print is a core render mode.

`RenderContext.renderMode` includes:

```ts
"preview" | "export" | "print"
```

Each plugin declares:

```ts
supportsPrint: boolean;
```

If `supportsPrint: true`, tests must include print smoke/snapshot coverage.

Print CSS should use shared primitives plus plugin-specific additions.

---

### D14 — Required quality gates

**Decision:** Rewrite cannot merge unless all 6 gates pass.

1. Registry completeness
   - all 12 schema artifact types have plugins
   - all Artifact UI kinds have plugins
2. Golden snapshots
   - one baseline per representative `(kind, audience, renderMode)`
3. Leak-prevention invariant
   - every student output rejects answer/teacher-only leakage
4. Sanitizer XSS corpus
   - all sanitizer policies tested against shared payload corpus
5. Worker protocol contract tests
   - valid request, malformed JSON, unknown kind, schema error, timeout, retryable internal error
6. Visual/print Playwright smoke
   - representative regular artifacts + Artifact UI families

---

### D15 — I18n

**Decision:** Use centralized `MessageCatalog`.

```ts
export interface MessageCatalog {
  readonly locale: Locale;
  t(key: MessageKey, params?: Record<string, string | number>): string;
}
```

Files:

```text
src/i18n/messages.vi.ts
src/i18n/messages.en.ts
src/i18n/index.ts
```

Rules:

- templates do not hard-code chrome text such as `Answer`, `Teacher Edition`, `Generated by`
- user-generated content remains untouched
- missing translation keys fail tests

---

### D16 — Error taxonomy

**Decision:** Use typed `RendererError`.

```ts
export type RendererErrorCode =
  | "VALIDATION_ERROR"
  | "UNKNOWN_KIND"
  | "UNSUPPORTED_AUDIENCE"
  | "TEMPLATE_NOT_FOUND"
  | "SANITIZER_VIOLATION"
  | "ASSET_POLICY_VIOLATION"
  | "RENDER_TIMEOUT"
  | "INTERNAL_RENDER_ERROR";

export interface RendererErrorShape {
  readonly code: RendererErrorCode;
  readonly category: "input" | "configuration" | "security" | "timeout" | "internal";
  readonly retryable: boolean;
  readonly message: string;
  readonly details?: unknown;
}
```

Retry policy:

| Code | Retry? | Notes |
|---|---:|---|
| `VALIDATION_ERROR` | no | caller/input problem |
| `UNKNOWN_KIND` | no | caller/config problem |
| `UNSUPPORTED_AUDIENCE` | no | caller problem |
| `TEMPLATE_NOT_FOUND` | no | deploy/config bug, alert |
| `SANITIZER_VIOLATION` | no | security alert |
| `ASSET_POLICY_VIOLATION` | no | plugin/template bug |
| `RENDER_TIMEOUT` | yes | pool may retry with fresh worker |
| `INTERNAL_RENDER_ERROR` | depends | retry only if marked retryable |

---

### D17 — Standalone asset policy

**Decision:** Enforce standalone output in core runtime.

Default policy:

```ts
assetPolicy: "inline-only"
```

Core post-render validator fails on:

```text
src="http
href="http
@import url(http
url(http
<link rel="stylesheet"
external fonts/CDNs
unmanaged <script src="...">
```

Allowed:

```text
data: URIs
inline SVG after SVG sanitizer
inline JS only if plugin declares it and sanitizer policy allows required data/aria attributes
```

---

### D18 — Folder layout

**Decision:** Hybrid layout: core by layer, implementations by plugin.

Target structure:

```text
packages/renderer/src/
├── index.ts
├── core/
│   ├── render.ts
│   ├── registry.ts
│   ├── types.ts
│   ├── errors.ts
│   ├── manifest.ts
│   ├── diagnostics.ts
│   └── asset-policy.ts
├── worker/
│   ├── agent-worker.ts
│   ├── protocol.ts
│   └── versions.ts
├── theme/
│   ├── resolver.ts
│   ├── generator.ts
│   ├── tokens.ts
│   └── themes/
├── sanitize/
│   ├── sanitize-rendered-html.ts
│   ├── policies.ts
│   └── xss-corpus.ts
├── i18n/
│   ├── index.ts
│   ├── messages.vi.ts
│   └── messages.en.ts
├── plugins/
│   ├── quiz/
│   │   ├── plugin.ts
│   │   ├── schema.ts
│   │   ├── adapter.ts
│   │   ├── template.html
│   │   └── plugin.test.ts
│   ├── worksheet/
│   ├── lesson/
│   ├── teaching-pack/
│   ├── navy-ticket.teaching/
│   ├── navy-ticket.practice/
│   ├── paper-dossier.lesson/
│   ├── paper-dossier.answer-key/
│   └── ...
├── shared/
│   ├── eta-engine.ts
│   ├── component-projection.ts
│   ├── components/
│   └── css/
└── __tests__/
    ├── registry-completeness.test.ts
    ├── leak-prevention.test.ts
    ├── sanitizer-corpus.test.ts
    ├── worker-protocol.test.ts
    └── visual-print.spec.ts
```

---

### D19 — Legacy wrappers

**Decision:** Delete public legacy wrappers.

Remove from public API:

```text
renderSemanticAnchorProjection
renderSemanticAnchorProjectionSet
renderInverseThinkingHtml
renderArtifactUi
renderArtifactUiSet
renderArtifactSync
```

Replace callers with:

```ts
render({ kind: "navy-ticket.teaching", input, context })
render({ kind: "navy-ticket.practice", input, context })
render({ kind: "investigation-folder.inverse-thinking", input, context })
```

---

## 3. Proposed New Public API

```ts
export interface RenderRequest {
  readonly kind: string;
  readonly input: unknown;
  readonly context: RenderContext;
}

export interface RenderResponse {
  readonly html: string;
  readonly manifest: RenderManifest;
  readonly diagnostics: readonly RenderDiagnostic[];
  readonly metrics: RenderMetrics;
}

export async function render(request: RenderRequest): Promise<RenderResponse>;

export interface RenderBatchRequest {
  readonly items: readonly RenderRequest[];
  readonly concurrency?: number;
}

export async function renderBatch(request: RenderBatchRequest): Promise<readonly RenderResponse[]>;
```

Internal flow:

```text
render(request)
  → registry.get(request.kind)
  → plugin.schema.parse(request.input)
  → validateAudience(plugin.capabilities.audiencePolicy, ctx.audience)
  → services.themeResolver.resolveTheme({theme, familyId, renderMode, locale})
  → plugin.adapt(parsedInput, ctx, services)
  → eta.renderAsync(plugin.templatePath(ctx), templateData)
  → sanitizeRenderedHtml(rawHtml, plugin.sanitizerPolicy)
  → validateStandaloneHtml(sanitizedHtml, ctx.assetPolicy)
  → createRenderManifest(...)
  → return {html, manifest, diagnostics, metrics}
```

---

## 4. Issues To Create

### Issue 001 — Define core renderer API and types

Deliverables:

- `src/core/types.ts`
- `src/core/errors.ts`
- `src/core/render.ts`
- public `src/index.ts`
- no plugin migration yet

Acceptance:

- `render()` exists but may only support a test fixture plugin
- typed error taxonomy exists
- package exports map blocks deep imports

---

### Issue 002 — Implement plugin registry

Deliverables:

- `src/core/registry.ts`
- plugin registration API
- registry completeness test framework

Acceptance:

- duplicate kind registration rejected
- unknown kind throws `UNKNOWN_KIND`
- registry metadata inspectable for diagnostics

---

### Issue 003 — Implement unified theme resolver

Deliverables:

- `src/theme/resolver.ts`
- migrate existing `ThemeCSSGenerator`
- artifact-ui CSS layering through resolver
- cache by `(themeId, familyId?, renderMode, locale)`

Acceptance:

- high-contrast-dyslexia applies to Artifact UI plugin fixture
- cache isolated in injectable resolver instance

---

### Issue 004 — Implement unified sanitizer and asset policy

Deliverables:

- `src/sanitize/sanitize-rendered-html.ts`
- sanitizer policies migrated from existing configs
- `src/core/asset-policy.ts`
- delete regex sanitizer path

Acceptance:

- shared XSS corpus passes for every policy
- external URLs fail with `ASSET_POLICY_VIOLATION`

---

### Issue 005 — Implement worker protocol v2

Deliverables:

- `src/worker/protocol.ts`
- updated `agent-worker.ts`
- updated `services/gateway/renderer_pool.py` parsing

Acceptance:

- response includes html, manifest, diagnostics, metrics
- retryable flag controls pool retry behavior
- requestId propagated across logs/errors

---

### Issue 006 — Build plugin folder layout and migrate regular artifacts

Plugins:

```text
lesson
quiz
worksheet
drill
recap
infographic
answer_key
flashcard_deck
reading_passage
exit_ticket
roadmap
teaching_pack
```

Acceptance:

- all 12 current `ArtifactType` members have plugins
- no fallback default-to-lesson behavior remains
- `teaching_pack` renders as bundle, not lesson

---

### Issue 007 — Migrate Artifact UI families to plugins

Plugins:

```text
navy-ticket.teaching
navy-ticket.practice
paper-dossier.lesson
paper-dossier.answer-key
paper-dossier.root-cause-session
transit-route.video-route
investigation-folder.inverse-thinking
```

Acceptance:

- old Artifact UI public functions removed
- existing vocabulary batch/inverse-thinking callers migrated to `render()`
- interactivity.js is declared as managed inline script per plugin policy

---

### Issue 008 — Implement audience safety harness

Deliverables:

- `AudiencePolicy`
- shared projection helpers
- leak-prevention invariant tests across every student-capable plugin

Acceptance:

- default leak field list enforced
- every component variant tested
- student render cannot contain teacher-only fields

---

### Issue 009 — Add i18n message catalog

Deliverables:

- `src/i18n/messages.vi.ts`
- `src/i18n/messages.en.ts`
- catalog injection into plugin adapters/templates

Acceptance:

- no hard-coded renderer chrome labels in templates
- missing message key fails tests

---

### Issue 010 — Add manifest/version pinning

Deliverables:

- `RenderManifest`
- content hash
- renderer/template/theme/plugin/sanitizer versions
- gateway persistence integration

Acceptance:

- final HTML + manifest stored together
- re-render is explicit and produces new manifest

---

### Issue 011 — Add print mode support

Deliverables:

- `renderMode: "print"`
- shared print primitives
- plugin `supportsPrint`
- print visual smoke tests

Acceptance:

- representative quiz, lesson, answer-key, worksheet pass print smoke
- plugin without print support rejects print mode clearly

---

### Issue 012 — Quality gates and CI enforcement

Deliverables:

- registry completeness test
- golden snapshots
- leak-prevention invariant
- sanitizer XSS corpus
- worker protocol tests
- Playwright visual/print smoke

Acceptance:

- all 6 required gates run in CI
- no merge if any gate fails

---

## 5. Updated Risk Assessment

### Findings confirmed by code

- Missing dispatch for 5 `ArtifactType` members is real.
- `renderArtifactSync()` and regex sanitizer are still public/exported.
- `sanitize()` and `sanitizeArtifactUi()` duplicate body extraction logic.
- `agent-renderer.ts` currently mixes validation, routing, and adapters.
- TS `ContentComponent` has 22 variants; student projection strips explicit sensitive fields for 5 groups.

### Finding adjusted after code check

- Worker pool is not completely missing production controls: it already has timeout, retry, and worker replacement. Remaining work is typed error taxonomy, richer protocol, correlation, metrics, and retry policy.

---

## 6. Non-Negotiable Invariants For The Rewrite

1. No fallback routing to `lesson` for unknown artifact types.
2. No renderer path without runtime schema validation.
3. No student render may contain teacher-only answer fields.
4. No external assets in final HTML.
5. No regex sanitizer path for production HTML.
6. No deep imports outside public package exports.
7. Every plugin declares kind, version, schema, template path, sanitizer policy, capabilities, and tests.
8. Every render response includes manifest, diagnostics, and metrics.
9. Stored artifacts do not visually drift unless explicitly re-rendered.
10. Print mode is first-class for printable artifacts.
