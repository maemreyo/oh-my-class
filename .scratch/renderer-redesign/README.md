# Renderer Redesign Issue Index

Parent ADR: `docs/adr/025-renderer-artifact-kind-plugin-registry.md`

Source resolution: `.scratch/renderer-module/renderer-redesign-grilling-resolution.md`

## Issues

0. `issues/000-capture-current-renderer-golden-baselines.md` — Phase 0 baseline from current renderer
1. `issues/001-core-renderer-kernel.md` — core API, registry, fixture plugin
2. `issues/002-worker-protocol-v2.md` — Python↔Node worker protocol V2
3. `issues/003-theme-sanitizer-asset-policy.md` — ThemeResolver, sanitizer chokepoint, standalone policy
4. `issues/004-quiz-tracer-plugin.md` — first real plugin (`quiz`) end-to-end
5. `issues/005-practice-plugins.md` — `worksheet` + `drill`
6. `issues/006-summary-visual-plugins.md` — `recap` + `infographic`
7. `issues/007-lesson-answer-key-plugins.md` — `lesson` + `answer_key` with audience safety
8. `issues/008-missing-contract-plugins.md` — `flashcard_deck`, `reading_passage`, `exit_ticket`, `roadmap`
9. `issues/009-teaching-pack-bundle-plugin.md` — `teaching_pack` bundle renderer
10. `issues/010-navy-ticket-vocabulary-plugins.md` — semantic anchor vocabulary plugins
11. `issues/011-artifact-ui-specialty-plugins.md` — inverse-thinking, root-cause, video-route
12. `issues/012-i18n-print-and-visual-qa.md` — message catalog + print/visual smoke
13. `issues/013-manifest-persistence-and-export-wiring.md` — final HTML + manifest persistence/export integration
14. `issues/014-public-api-boundary-and-caller-migration.md` — package exports + caller migration + legacy removal
15. `issues/015-quality-gates-ci.md` — full quality gate suite
16. `issues/016-decommission-legacy-renderer.md` — delete old paths and verify no deep imports remain

## Delivery Tiers

**Phase 0:** issue 000. Capture current-renderer golden baselines before rewrite work starts.

**Core blockers:** issues 001-011 and 014. These establish the registry, migrate all current render paths, and cut callers over to the new API.

**Production hardening:** issues 012, 013, and 015. These add i18n, print/visual QA, manifest persistence, and quality gates. They may land after the core kernel but must land before decommission.

**Decommission:** issue 016. Runs only after every core and production-hardening gate passes.
