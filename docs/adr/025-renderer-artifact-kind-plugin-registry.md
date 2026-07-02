# ADR-025: Renderer Artifact-Kind Plugin Registry Rewrite

## Status

**Decided** (2026-07-02) — `packages/renderer/` will be rewritten around a single Artifact-Kind Plugin Registry. This ADR supersedes the renderer-specific public API decisions in ADR-024 while preserving ADR-023's Artifact UI design-system goals and ADR-022's teacher/student projection safety requirements.

## Context

The renderer currently has three parallel ways to answer "what kind of artifact is this?":

1. `ArtifactType` in the TypeScript contracts.
2. Artifact UI `family + kind` pairs.
3. A hand-written `switch (artifact_type)` in `agent-renderer.ts`.

This split caused confirmed production risks:

- `flashcard_deck`, `reading_passage`, `exit_ticket`, `roadmap`, and `teaching_pack` are present in contracts/sanitizer config but are not explicitly dispatched by `renderAgentArtifact()`, so they can fall into `default -> lessonData()`.
- `sanitize()` and `sanitizeArtifactUi()` duplicate body extraction logic.
- `renderArtifactSync()` still exposes a weaker regex sanitizer path.
- `agent-renderer.ts` mixes validation, routing, and adapter logic.
- Artifact UI theming and regular artifact theming are separate, so accessibility themes do not consistently cover every render family.
- Public API boundaries are not enforceable because callers can deep-import internals.

We choose a production-ready rewrite rather than incremental patches.

Follow-up review of the real codebase showed that the external caller surface for render HTML is small: the main TypeScript caller outside `packages/renderer` is the vocabulary batch exporter, `apps/web` has no runtime renderer import, and Python uses the renderer through the subprocess protocol. Therefore the main risk of the rewrite is not caller migration; it is visual/template regression across the existing renderer surface. Golden baselines from the current renderer must be captured before any rewrite work starts.

## Decision

### 1. One Artifact-Kind Plugin Registry

Renderer identity is a registry `kind`, not `ArtifactType` plus a separate family/kind system.

Examples:

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

Each plugin owns its schema, adapter, template path, sanitizer policy, capabilities, and version.

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

### 2. Breaking Public API

The new public API is:

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
export async function renderBatch(request: RenderBatchRequest): Promise<readonly RenderResponse[]>;
```

The old public functions are removed from the public API: `renderArtifact`, `renderArtifactUi`, `renderArtifactUiSet`, `renderSemanticAnchorProjection*`, `renderInverseThinkingHtml`, and `renderArtifactSync`.

### 3. Full RenderContext

Every render call must include:

```ts
export interface RenderContext {
  readonly audience: "teacher" | "student";
  readonly locale: "vi" | "en";
  readonly theme: string;
  readonly renderMode: "preview" | "export" | "print";
  readonly requestId: string;
  readonly versions: RenderVersionContext;
  readonly assetPolicy: "inline-only";
}
```

This makes audience projection, i18n, accessibility theming, print/export/preview behavior, observability, version pinning, and standalone policy explicit.

### 4. Unified ThemeResolver

The separate regular theme and Artifact UI CSS loading paths are replaced by a shared `ThemeResolver` with a cache key of `(themeId, familyId?, renderMode, locale)`. Accessibility themes such as high-contrast/dyslexia must apply to regular artifacts and Artifact UI plugins.

### 5. Single Sanitizer Chokepoint

All rendered output passes through:

```ts
sanitizeRenderedHtml(html, plugin.sanitizerPolicy)
```

The function preserves `DOCTYPE`, sanitizes body content for full documents, sanitizes full fragments for fragments, and uses `sanitize-html` policies. Regex sanitizer and `renderArtifactSync()` are deleted.

### 6. Audience Safety

Plugins declare `AudiencePolicy`. Core rejects unsupported audiences before rendering. Student-capable plugins must pass leak-prevention invariant tests for fields such as `answer`, `correct_answer`, `explain`, `rationale`, `answer_key`, `teacher_rationale`, `coaching_notes`, `reveal_answer`, and `wrong_reasons`.

### 7. Standalone Asset Policy

The core renderer enforces `assetPolicy: "inline-only"` by rejecting external `src`, `href`, CSS `url(http...)`, CDN stylesheets, external fonts, and unmanaged external scripts. Allowed assets are `data:` URIs, sanitized inline SVG, and explicitly managed inline JS.

Managed inline JavaScript is not a boolean permission. A plugin that needs inline JS must declare every managed script with a stable id, source path, and SHA-256 hash:

```ts
export interface ManagedScriptDeclaration {
  readonly id: string;
  readonly sourcePath: string;
  readonly sha256: string;
}
```

The core renderer may inline a script only when the loaded source hash matches the plugin declaration. Any inline `<script>` not produced from a matching managed script declaration fails asset-policy validation. The plugin's sanitizer policy must separately allow only the `data-*`/`aria-*` attributes needed by that script.

### 8. Worker Protocol V2

Python-to-Node rendering keeps stdin/stdout transport but upgrades payloads.

Request:

```ts
{ requestId, kind, input, context }
```

Success response:

```ts
{ ok: true, html, manifest, diagnostics, metrics }
```

Failure response:

```ts
{ ok: false, error: { code, category, retryable, message, details }, diagnostics, metrics? }
```

### 9. Version Pinning

Every successful render returns a `RenderManifest` containing `rendererVersion`, `pluginVersion`, `templateVersion`, `themeVersion`, `sanitizerPolicyVersion`, `renderedAt`, and `contentHash`. Persisted artifacts store final HTML plus the manifest. Re-rendering is explicit and produces a new manifest.

### 10. I18n and Print

Renderer UI chrome uses a centralized `MessageCatalog` (`vi`, `en`). Templates must not hard-code labels such as "Answer" or "Teacher Edition". Print is a first-class `renderMode`; printable plugins declare `supportsPrint` and have print smoke coverage.

### 11. Package Boundary

`package.json` `exports` exposes only the public renderer API. Deep imports into internals such as theme loaders, sanitizer configs, or plugins are blocked.

### 12. Required Quality Gates

The rewrite cannot merge unless these gates pass:

1. Golden baselines from the current renderer captured before rewrite work starts.
2. Registry completeness for all 12 existing `ArtifactType` members plus Artifact UI kinds.
3. Golden snapshots for representative `(kind, audience, renderMode)` combinations compared against the captured baseline where applicable.
4. Leak-prevention invariant tests for student output.
5. Shared sanitizer XSS corpus across all sanitizer policies.
6. Worker protocol contract tests.
7. Visual/print Playwright smoke tests for representative plugins.

### 13. Delivery Model

The rewrite is a big-bang outcome, not a single mega-PR. Delivery is vertical-slice based:

1. Capture current-renderer baselines first.
2. Build the new core and fixture plugin in parallel with the old renderer.
3. Migrate plugins slice by slice with snapshots and invariant tests green.
4. Cut over callers once the registry is complete.
5. Decommission old paths only after all core and production-hardening gates pass.

Scope is tiered within the same epic:

- **Core blockers:** baseline capture, registry, runtime schemas, unified sanitizer, audience safety, asset policy, theme unification, and all currently supported artifact plugins.
- **Production hardening:** manifest persistence, worker metrics/diagnostics, i18n catalog, print mode, visual/print QA, and CI gates. These may land after the core kernel, but they must land before final legacy decommission.

## Consequences

### Positive

- Adding a new artifact kind becomes a plugin addition rather than editing routing, sanitizer maps, templates, and exporters separately.
- The confirmed missing-dispatch gap is structurally impossible once registry completeness tests are enforced.
- Accessibility themes and print behavior become consistent across every artifact family.
- Security audit surface is reduced to one sanitizer chokepoint and one asset policy validator.
- Worker observability improves via request IDs, metrics, diagnostics, typed errors, and manifests.

### Negative

- This is a breaking rewrite; all renderer callers must migrate in the same effort.
- The first implementation is larger than a patch because every existing artifact type must become a first-class plugin.
- Snapshot and visual fixtures will need careful review to avoid locking in bad output.

## Implementation Notes

Issues live under `.scratch/renderer-redesign/issues/` and are indexed in dependency order. The rewrite should implement a thin end-to-end fixture first, then migrate real plugins in vertical slices.
