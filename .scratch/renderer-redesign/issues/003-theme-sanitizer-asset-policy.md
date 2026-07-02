---
title: Unified theme resolver, sanitizer chokepoint, and standalone asset policy
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-07-02
---

## Parent

ADR-025: Renderer Artifact-Kind Plugin Registry Rewrite

## What to build

Replace separate theme and Artifact UI CSS loading paths with a shared ThemeResolver, replace duplicate sanitizer functions with one sanitizer chokepoint, and enforce standalone HTML through runtime asset policy validation.

Managed inline JavaScript must use plugin-declared hash allowlists: each script declaration includes `id`, `sourcePath`, and `sha256`; core may inline only matching sources. All other inline scripts fail asset-policy validation.

## Acceptance criteria

- [ ] `ThemeResolver` resolves CSS by `(themeId, familyId?, renderMode, locale)` and can be injected into render services.
- [ ] Existing theme generation and Artifact UI CSS layers are represented in the unified theme flow.
- [ ] `sanitizeRenderedHtml(html, policy)` handles full documents and fragments using one body-extraction implementation.
- [ ] Regex sanitizer and sync renderer paths are no longer used by production render flow.
- [ ] Asset policy rejects external `src`, `href`, CSS `url(http...)`, CDN stylesheet links, external fonts, and unmanaged external scripts.
- [ ] Managed inline JS is allowed only when a plugin declares `{ id, sourcePath, sha256 }` and the loaded source hash matches.
- [ ] Tests prove high-contrast/dyslexia theme can apply to both a regular fixture plugin and an Artifact UI fixture plugin.
- [ ] Shared XSS corpus passes for the fixture sanitizer policies.

## Blocked by

- 000-capture-current-renderer-golden-baselines.md
- 001-core-renderer-kernel.md
